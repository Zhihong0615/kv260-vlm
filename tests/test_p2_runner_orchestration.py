import json
from pathlib import Path
import tempfile
import unittest

from scripts.parse_board_textvqa_pilot import EXECUTION_KEYS, NON_START_REASONS, START_EVIDENCE_KEYS
from scripts.run_board_cpu_p2_textvqa import HostOrchestrationOps, ORDER, RUN_IDS, run_host_orchestration


def complete_status(qid):
    return {
        "state": "COMPLETE",
        "run_id": RUN_IDS[qid],
        "run_dir_exists": True,
        "runner_lock_free": True,
        "completion_marker_valid": True,
        "board_cli_processes": [],
        "unreadable_processes": [],
    }


class FakeOrchestrationOps:
    def __init__(self, root, qid, *, previous=None, worker=None, status=None, copy=None, score=None):
        self.root = Path(root)
        self.qid = qid
        self.previous = previous or {}
        self.worker_result = worker or {
            "timed_out": False,
            "remote_result": {"status": "REQUEST_FINISHED", "cli_started": True},
        }
        self.status_result = status or {"returncode": 0, "remote_status": complete_status(qid)}
        self.copy_result = copy or {"verified": True}
        self.score_result = score or {
            "answer_parse_ok": True,
            "image_processing_verified": True,
            "stop_after_this_request": False,
        }
        self.calls = []
        self.state_records = []
        self.nonstart_records = {}
        self.copy_partial_path = self.root / "partial-copy.bin"

    def assess_previous(self, qid):
        self.calls.append(("assess_previous", qid))
        return self.previous.get(qid, True)

    def begin(self):
        self.calls.append(("begin", self.qid))
        (self.root / "current-case").mkdir(exist_ok=True)

    def preflight(self):
        self.calls.append(("preflight", self.qid))
        return None

    def stage(self):
        self.calls.append(("stage", self.qid))
        return None

    def launch_worker(self):
        self.calls.append(("launch_worker", self.qid))
        (self.root / "current-case").mkdir(exist_ok=True)
        (self.root / "current-case" / "worker.stdout").write_bytes(b"partial synthetic worker output")
        return self.worker_result

    def query_status(self):
        self.calls.append(("query_status", self.qid))
        (self.root / "current-case").mkdir(exist_ok=True)
        (self.root / "current-case" / "remote_status.stdout").write_bytes(b"synthetic status evidence")
        if isinstance(self.status_result, BaseException):
            raise self.status_result
        return self.status_result

    def copy_and_verify(self):
        self.calls.append(("copy_and_verify", self.qid))
        self.copy_partial_path.write_bytes(b"partial synthetic copy")
        return self.copy_result

    def score(self):
        self.calls.append(("score", self.qid))
        return self.score_result

    def record_nonstart(self, qid, reason, prior_run_id):
        self.calls.append(("record_nonstart", qid, reason, prior_run_id))
        state = {
            "schema": "kv260_cpu_p2_textvqa_execution_v1",
            "question_id": qid,
            "cli_started": False,
            "non_start_reason": reason,
            "non_start_at_utc": "2026-09-24T00:00:00+00:00",
            "prior_run_id": prior_run_id,
            "timeout_executable_path": None,
            "timeout_executable_resolved_path": None,
            "timeout_executable_sha256": None,
            "timeout_executable_recheck_path": None,
            "timeout_executable_recheck_resolved_path": None,
            "timeout_executable_recheck_sha256": None,
            "timeout_executable_identity_verified": False,
            "timeout_executable_rechecked_at_utc": None,
        }
        self.nonstart_records[qid] = state
        record_path = self.root / f"nonstart-{qid}.json"
        record_path.write_text(json.dumps(state), encoding="utf-8")

    def record_state(self, phase, fields):
        self.calls.append(("record_state", phase))
        self.state_records.append((phase, dict(fields)))
        (self.root / f"state-{len(self.state_records)}.json").write_text(
            json.dumps({"phase": phase, **fields}), encoding="utf-8")

    def operations(self):
        return HostOrchestrationOps(
            assess_previous=self.assess_previous,
            begin=self.begin,
            preflight=self.preflight,
            stage=self.stage,
            launch_worker=self.launch_worker,
            query_status=self.query_status,
            copy_and_verify=self.copy_and_verify,
            score=self.score,
            record_nonstart=self.record_nonstart,
            record_state=self.record_state,
        )


class RunnerOrchestrationTests(unittest.TestCase):
    def run_fake(self, qid=ORDER[0], **kwargs):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        fake = FakeOrchestrationOps(temporary.name, qid, **kwargs)
        decision = run_host_orchestration(qid, ORDER, RUN_IDS, fake.operations())
        return fake, decision

    def assert_parser_valid_nonstart(self, record, qid, reason, prior_run_id):
        self.assertTrue(set(record).issubset(EXECUTION_KEYS))
        self.assertFalse(record["cli_started"])
        self.assertEqual(record["question_id"], qid)
        self.assertEqual(record["non_start_reason"], reason)
        self.assertIn(reason, NON_START_REASONS)
        self.assertEqual(record["prior_run_id"], prior_run_id)
        self.assertFalse(set(record) & START_EVIDENCE_KEYS)

    def test_worker_timeout_queries_once_then_copies_only_exact_complete_run(self):
        fake, decision = self.run_fake(worker={"timed_out": True, "remote_result": None})
        self.assertEqual(decision["status"], "COMPLETE")
        self.assertEqual([name for name, *_ in fake.calls].count("launch_worker"), 1)
        self.assertEqual([name for name, *_ in fake.calls].count("query_status"), 1)
        self.assertEqual(
            (fake.root / "current-case" / "worker.stdout").read_bytes(),
            b"partial synthetic worker output",
        )
        self.assertTrue((fake.root / "current-case" / "remote_status.stdout").is_file())
        names = [name for name, *_ in fake.calls]
        self.assertLess(names.index("query_status"), names.index("copy_and_verify"))
        self.assertLess(names.index("copy_and_verify"), names.index("score"))
        self.assertEqual([row[1] for row in fake.state_records if row[0] == "final"], [
            {"stop_after_this_request": False},
        ])

    def test_exact_remote_lock_busy_is_current_qid_nonstart_and_stops_later_qids(self):
        fake, decision = self.run_fake(worker={
            "timed_out": False,
            "remote_result": {"status": "REMOTE_LOCK_BUSY", "cli_started": False},
        })
        self.assertEqual(decision["status"], "REMOTE_LOCK_BUSY")
        self.assertNotIn("query_status", [name for name, *_ in fake.calls])
        self.assertNotIn("copy_and_verify", [name for name, *_ in fake.calls])
        self.assertNotIn("score", [name for name, *_ in fake.calls])
        self.assert_parser_valid_nonstart(fake.nonstart_records[ORDER[0]], ORDER[0],
                                          "RUNNER_LOCK_BUSY", None)
        for later in ORDER[1:]:
            self.assert_parser_valid_nonstart(fake.nonstart_records[later], later,
                                              "PRIOR_CASE_UNRESOLVED", RUN_IDS[ORDER[0]])
        self.assertEqual(fake.state_records[-1][0], "remote_runner_lock_busy")
        self.assertFalse(fake.state_records[-1][1]["board_inference_attempted"])

    def test_status_transport_malformed_and_incomplete_results_remain_unresolved(self):
        cases = ("transport", "nonzero", "malformed", "wrong_run_id", "lock_busy",
                 "completion_invalid", "cli_present", "unreadable_process")
        for case in cases:
            with self.subTest(case=case):
                if case == "transport":
                    status = OSError("synthetic SSH status transport failure")
                elif case == "nonzero":
                    status = {"returncode": 255, "remote_status": None}
                elif case == "malformed":
                    status = {"returncode": 0, "remote_status": None}
                else:
                    remote_status = complete_status(ORDER[1])
                    if case == "wrong_run_id":
                        remote_status["run_id"] = "another-run"
                    elif case == "lock_busy":
                        remote_status["runner_lock_free"] = False
                    elif case == "completion_invalid":
                        remote_status["completion_marker_valid"] = False
                    elif case == "cli_present":
                        remote_status["board_cli_processes"] = [123]
                    elif case == "unreadable_process":
                        remote_status["unreadable_processes"] = [456]
                    status = {"returncode": 0, "remote_status": remote_status}
                fake, decision = self.run_fake(qid=ORDER[1], status=status)
                self.assertEqual(decision["status"], "REMOTE_STATE_UNKNOWN")
                self.assertEqual([name for name, *_ in fake.calls].count("query_status"), 1)
                self.assertNotIn("copy_and_verify", [name for name, *_ in fake.calls])
                self.assertNotIn("score", [name for name, *_ in fake.calls])
                self.assertTrue((fake.root / "current-case" / "remote_status.stdout").is_file())
                self.assertEqual(fake.state_records[-1][0], "remote_state_unknown")
                self.assertEqual(fake.state_records[-1][1]["status"], "REMOTE_STATE_UNKNOWN")
                self.assert_parser_valid_nonstart(fake.nonstart_records[ORDER[2]], ORDER[2],
                                                  "PRIOR_CASE_UNRESOLVED", RUN_IDS[ORDER[1]])

    def test_incomplete_copy_never_scores_and_preserves_partial_output(self):
        copy_failures = (
            {"verified": False, "phase": "copy_incomplete", "failure_at": "raw_copy_timeout"},
            {"verified": False, "phase": "copy_incomplete", "failure_at": "raw_copy_returncode"},
            {"verified": False, "phase": "copy_manifest_invalid", "failure_at": "completion_manifest"},
            {"verified": False, "phase": "copy_mismatch", "failure_at": "copy_hash_mismatch"},
        )
        for copy_result in copy_failures:
            with self.subTest(copy_result=copy_result):
                fake, decision = self.run_fake(qid=ORDER[1], copy=copy_result)
                self.assertEqual(decision["status"], "EVIDENCE_COPY_INCOMPLETE")
                self.assertTrue(fake.copy_partial_path.is_file())
                self.assertNotIn("score", [name for name, *_ in fake.calls])
                self.assert_parser_valid_nonstart(fake.nonstart_records[ORDER[2]], ORDER[2],
                                                  "PRIOR_CASE_UNRESOLVED", RUN_IDS[ORDER[1]])

    def test_ordered_stop_records_requested_and_later_qids_without_starting_them(self):
        fake, decision = self.run_fake(qid=ORDER[1], previous={ORDER[0]: False})
        self.assertEqual(decision["status"], "PRIOR_CASE_FAILED")
        self.assertEqual(fake.calls, [
            ("assess_previous", ORDER[0]),
            ("record_nonstart", ORDER[1], "PRIOR_CASE_FAILED", RUN_IDS[ORDER[0]]),
            ("record_nonstart", ORDER[2], "PRIOR_CASE_FAILED", RUN_IDS[ORDER[0]]),
        ])
        self.assertNotIn("begin", [name for name, *_ in fake.calls])
        self.assertNotIn("preflight", [name for name, *_ in fake.calls])
        self.assertNotIn("stage", [name for name, *_ in fake.calls])
        self.assertNotIn("launch_worker", [name for name, *_ in fake.calls])
        self.assertNotIn("query_status", [name for name, *_ in fake.calls])
        self.assertNotIn("copy_and_verify", [name for name, *_ in fake.calls])
        for qid in ORDER[1:]:
            self.assert_parser_valid_nonstart(fake.nonstart_records[qid], qid,
                                              "PRIOR_CASE_FAILED", RUN_IDS[ORDER[0]])


if __name__ == "__main__":
    unittest.main()
