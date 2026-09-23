from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PARSER_PATH = ROOT / "scripts/parse_board_textvqa_pilot.py"
RUNNER_PATH = ROOT / "scripts/run_board_cpu_p2_textvqa.py"
SINGLE_RUNNER_PATH = ROOT / "scripts/run_board_cpu_p2_single.py"
PREFLIGHT_PATH = ROOT / "scripts/board_cpu_preflight_remote.py"
SPEC = importlib.util.spec_from_file_location("board_textvqa_parser_under_test", PARSER_PATH)
assert SPEC is not None and SPEC.loader is not None
parser_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = parser_module
SPEC.loader.exec_module(parser_module)
RUNNER_SPEC = importlib.util.spec_from_file_location("board_textvqa_runner_under_test", RUNNER_PATH)
assert RUNNER_SPEC is not None and RUNNER_SPEC.loader is not None
runner_module = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = runner_module
RUNNER_SPEC.loader.exec_module(runner_module)
SINGLE_RUNNER_SPEC = importlib.util.spec_from_file_location(
    "board_cpu_single_runner_under_test", SINGLE_RUNNER_PATH)
assert SINGLE_RUNNER_SPEC is not None and SINGLE_RUNNER_SPEC.loader is not None
single_runner_module = importlib.util.module_from_spec(SINGLE_RUNNER_SPEC)
sys.modules[SINGLE_RUNNER_SPEC.name] = single_runner_module
SINGLE_RUNNER_SPEC.loader.exec_module(single_runner_module)
PREFLIGHT_SPEC = importlib.util.spec_from_file_location("board_textvqa_preflight_under_test", PREFLIGHT_PATH)
assert PREFLIGHT_SPEC is not None and PREFLIGHT_SPEC.loader is not None
preflight_module = importlib.util.module_from_spec(PREFLIGHT_SPEC)
sys.modules[PREFLIGHT_SPEC.name] = preflight_module
PREFLIGHT_SPEC.loader.exec_module(preflight_module)


class BoardTextVQAContractTests(unittest.TestCase):
    def test_valid_nonstart_is_excluded_from_attempts(self) -> None:
        state = {
            "schema": "kv260_cpu_p2_textvqa_execution_v1",
            "question_id": 38299,
            "cli_started": False,
            "non_start_reason": "PREFLIGHT_BLOCKED",
            "non_start_at_utc": "2026-09-23T12:00:00+00:00",
            "prior_run_id": None,
        }
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            (raw / "result.json").write_text(json.dumps(state), encoding="utf-8")
            result = parser_module.inspect_case(
                38299, raw, {"image_id": "test"}, {"images": {}}, "0" * 64,
                ROOT / "unused-manifest.json", None, "pilot")
        self.assertIs(result["attempted"], False)
        self.assertEqual(result["status"], "NOT_ATTEMPTED")

    def test_nonstart_with_execution_field_remains_unknown(self) -> None:
        state = {
            "schema": "kv260_cpu_p2_textvqa_execution_v1",
            "question_id": 38299,
            "cli_started": False,
            "non_start_reason": "PREFLIGHT_BLOCKED",
            "non_start_at_utc": "2026-09-23T12:00:00+00:00",
            "prior_run_id": None,
            "remote_run_dir": "/home/ubuntu/kv260-vlm-p2-cpu/runs/qid38299",
        }
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            (raw / "result.json").write_text(json.dumps(state), encoding="utf-8")
            result = parser_module.inspect_case(
                38299, raw, {"image_id": "test"}, {"images": {}}, "0" * 64,
                ROOT / "unused-manifest.json", None, "pilot")
        self.assertIsNone(result["attempted"])
        self.assertTrue(any(error.startswith("ATTEMPT_STATE_INVALID") for error in result["errors"]))

    def test_valid_image_event_order_passes_and_overlap_fails(self) -> None:
        valid = "\n".join((
            "0.00.001.000 I encoding mtmd batch, n_chunks = 1 (done = 0, total = 1)",
            "0.00.001.001 I mtmd batch encoding done in 4 ms",
            "0.00.001.002 I decoding image batch 1/1, n_tokens_batch = 8",
            "0.00.001.003 I image decoded (batch 1/1) in 3 ms",
        ))
        overlap = "\n".join((
            "0.00.001.000 I encoding mtmd batch, n_chunks = 1 (done = 0, total = 1)",
            "0.00.001.001 I mtmd batch encoding done in 4 ms",
            "0.00.001.002 I encoding mtmd batch, n_chunks = 1 (done = 1, total = 1)",
            "0.00.001.003 I decoding image batch 1/1, n_tokens_batch = 8",
            "0.00.001.004 I image decoded (batch 1/1) in 3 ms",
            "0.00.001.005 I mtmd batch encoding done in 4 ms",
        ))
        self.assertTrue(parser_module.inspect_events(valid)["event_predicate_pass"])
        self.assertFalse(parser_module.inspect_events(overlap)["event_predicate_pass"])

    def test_raw_label_keys_and_symlinks_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            (raw / "nested").mkdir()
            (raw / "nested/labels.json").write_text(
                json.dumps({"meta": [{"ground_truth_answers": ["private"]}]}), encoding="utf-8")
            errors = parser_module.inspect_raw_json_labels(raw)
            self.assertTrue(any(error.startswith("RAW_REFERENCE_LABEL_KEY") for error in errors))

            external = raw.parent / (raw.name + "_external.json")
            external.write_text("{}", encoding="utf-8")
            try:
                (raw / "linked.json").symlink_to(external)
                symlink_errors = parser_module.inspect_raw_json_labels(raw)
                self.assertTrue(any(error.startswith("RAW_SYMLINK_REJECTED") for error in symlink_errors))
            finally:
                external.unlink(missing_ok=True)

    def test_runner_metadata_answer_parse_flag_is_not_a_reference_label(self) -> None:
        self.assertFalse(parser_module.has_label_keys({"answer_parse_ok": True}))
        self.assertTrue(parser_module.has_label_keys({"ground_truth_answers": ["secret"]}))
        self.assertTrue(parser_module.has_label_keys({"answer_parse_ok": {"reference": "secret"}}))

    def _write_board_completion_fixture(self, raw: Path) -> str:
        manifest = {}
        for name in sorted(parser_module.PILOT_BOARD_FILE_NAMES):
            payload = json.dumps({"stdout_log_sha256": "0" * 64}).encode() if name == "result.json" else name.encode()
            (raw / name).write_bytes(payload)
            manifest[name] = {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        completion = {
            "schema": "kv260_cpu_p2_textvqa_board_completion_v1",
            "run_id": "kv260_cpu_p2_tvqa_q38299_r01",
            "manifest": manifest,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "worker_pid": 123,
        }
        completion_path = raw / "completion.json"
        completion_path.write_text(json.dumps(completion), encoding="utf-8")
        digest = hashlib.sha256(completion_path.read_bytes()).hexdigest()
        receipt = {
            "schema": "kv260_cpu_p2_textvqa_host_copy_verification_v1",
            "question_id": 38299,
            "run_id": "kv260_cpu_p2_tvqa_q38299_r01",
            "completion_json_sha256": digest,
            "board_files_verified": True,
            "verified_file_names": sorted(parser_module.PILOT_BOARD_FILE_NAMES | {"completion.json"}),
            "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        (raw / parser_module.HOST_COPY_RECEIPT_NAME).write_text(json.dumps(receipt), encoding="utf-8")
        return digest

    def test_board_completion_and_host_copy_receipt_bind_board_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            completion_sha = self._write_board_completion_fixture(raw)
            self.assertEqual(parser_module.verify_board_completion_manifest(raw, 38299), completion_sha)
            parser_module.verify_host_copy_receipt(raw, 38299, completion_sha)

    def test_board_completion_rejects_result_and_stdout_mutated_together(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            self._write_board_completion_fixture(raw)
            stdout_path = raw / "stdout.log"
            stdout_path.write_text("replacement prediction\n", encoding="utf-8")
            result_path = raw / "result.json"
            result_path.write_text(json.dumps({"stdout_log_sha256": hashlib.sha256(stdout_path.read_bytes()).hexdigest()}),
                                   encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "completion hash/size mismatch"):
                parser_module.verify_board_completion_manifest(raw, 38299)

    def test_preflight_systemd_unknown_and_active_upgrade_fail_closed(self) -> None:
        timeout = mock.Mock(side_effect=subprocess.TimeoutExpired("systemctl", 5))
        unknown = preflight_module.systemd_state("apt-daily.service", timeout)
        self.assertEqual(unknown["active_state"], "UNKNOWN")
        self.assertTrue(unknown["timed_out"])
        good = {
            "jupyter.service": {"active_state": "active", "returncode": 0, "timed_out": False},
            "apt-daily.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
            "apt-daily-upgrade.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
        }
        self.assertEqual(runner_module.systemd_gate_reasons(good), [])
        active_upgrade = {**good, "apt-daily-upgrade.service":
                          {"active_state": "activating", "returncode": 0, "timed_out": False}}
        self.assertIn("PACKAGE_UPGRADE_SERVICE", runner_module.systemd_gate_reasons(active_upgrade))
        timed_out = {**good, "apt-daily.service": unknown}
        self.assertIn("PACKAGE_UPGRADE_SERVICE", runner_module.systemd_gate_reasons(timed_out))

    def test_packagekit_query_distinguishes_idle_active_and_unknown(self) -> None:
        active = {"packagekit.service":
                  {"active_state": "active", "returncode": 0, "timed_out": False}}
        idle = preflight_module.packagekit_transaction_state(
            {"packagekit.service":
             {"active_state": "inactive", "returncode": 3, "timed_out": False}},
            run=mock.Mock())
        self.assertEqual(idle["state"], "SERVICE_INACTIVE")

        no_transactions = preflight_module.packagekit_transaction_state(
            active, run=mock.Mock(return_value=mock.Mock(
                returncode=0, stdout="ao 0\n", stderr="")))
        self.assertEqual(no_transactions["state"], "NO_ACTIVE_TRANSACTIONS")

        one_transaction = preflight_module.packagekit_transaction_state(
            active, run=mock.Mock(return_value=mock.Mock(
                returncode=0, stdout="ao 1 /org/freedesktop/PackageKit/transactions/12\n", stderr="")))
        self.assertEqual(one_transaction["state"], "ACTIVE_TRANSACTIONS")
        self.assertEqual(len(one_transaction["transaction_ids"]), 1)

        unknown = preflight_module.packagekit_transaction_state(
            active, run=mock.Mock(side_effect=subprocess.TimeoutExpired("busctl", 10)))
        self.assertEqual(unknown["state"], "UNKNOWN")
        self.assertTrue(unknown["timed_out"])

    def test_shutdown_waiter_requires_exact_command_and_runner_allows_only_idle_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            cmdline = proc / "cmdline"
            cmdline.write_bytes(
                b"/usr/bin/python3\0/usr/share/unattended-upgrades/"
                b"unattended-upgrade-shutdown\0--wait-for-signal\0")
            self.assertEqual(preflight_module.process_role(proc, "unattended-upgr"), "shutdown_waiter")
            cmdline.write_bytes(
                b"/usr/bin/python3\0/usr/share/unattended-upgrades/"
                b"unattended-upgrade\0--debug\0")
            self.assertEqual(preflight_module.process_role(proc, "unattended-upgr"), "unattended_upgrade")

        snapshot = {
            "arch": "aarch64", "cpu_count": 4,
            "memory_kib": {"MemAvailable": 3_000_000, "CmaFree": 800_000,
                            "SwapTotal": 0, "SwapFree": 0},
            "home_free_bytes": 2 << 30, "jupyter_active": "active",
            "loadavg": "0.2 0.2 0.2 1/100 123",
            "systemd_service_states": {
                "jupyter.service": {"active_state": "active", "returncode": 0, "timed_out": False},
                "apt-daily.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
                "apt-daily-upgrade.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
            },
            "tools_present": {"timeout": True, "/usr/bin/time": True},
            "selected_processes": [
                {"pid": 1218, "comm": "unattended-upgr", "role": "shutdown_waiter"},
                {"pid": 123008, "comm": "packagekitd", "role": "process"},
            ],
            "packagekit_transaction_state": {
                "state": "NO_ACTIVE_TRANSACTIONS", "transaction_ids": [], "timed_out": False,
            },
        }
        single_runner_module.preflight_gate(snapshot)
        self.assertEqual(runner_module.preflight_resource_gate_reasons(snapshot), [])

        worker_config = {
            "min_mem_available_kib": 2_750_000, "min_cma_free_kib": 700_000,
            "min_home_free_bytes": 1 << 30, "max_load1": 1.5,
            "max_busy_cores_per_process": 0.25,
        }
        worker_globals = {"__name__": "board_worker_contract", "CONFIG": worker_config}
        exec(runner_module.REMOTE_WORKER, worker_globals)
        worker_snapshot = {
            "arch": "aarch64", "cpu_count": 4,
            "memory_kib": snapshot["memory_kib"], "home_free_bytes": snapshot["home_free_bytes"],
            "jupyter_active": "active", "jupyter_returncode": 0,
            "loadavg": snapshot["loadavg"],
            "systemd_service_states": {
                "jupyter.service": {"active_state": "active", "returncode": 0, "timed_out": False},
                "apt-daily.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
                "apt-daily-upgrade.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
            },
            "selected_processes": snapshot["selected_processes"],
            "packagekit_transaction_state": snapshot["packagekit_transaction_state"],
        }
        self.assertEqual(worker_globals["gate"](worker_snapshot, True), [])

        snapshot["packagekit_transaction_state"] = {
            "state": "ACTIVE_TRANSACTIONS", "transaction_ids": ["/transaction/1"],
            "timed_out": False,
        }
        self.assertIn("PACKAGEKIT_STATE", runner_module.preflight_resource_gate_reasons(snapshot))
        worker_snapshot["packagekit_transaction_state"] = snapshot["packagekit_transaction_state"]
        self.assertIn("PACKAGEKIT_STATE", worker_globals["gate"](worker_snapshot, True))
        snapshot["packagekit_transaction_state"] = {
            "state": "ACTIVE_TRANSACTIONS", "transaction_ids": ["/transaction/1"],
            "timed_out": False,
        }
        with self.assertRaisesRegex(ValueError, "PackageKit transaction"):
            single_runner_module.preflight_gate(snapshot)

    def test_transport_timeout_preserves_partial_output_for_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            exc = subprocess.TimeoutExpired("ssh", 45, output=b"partial-out", stderr=b"partial-err")
            details = runner_module.persist_transport_failure(raw, "remote_status", exc)
            self.assertTrue(details["remote_status_timed_out"])
            self.assertEqual((raw / "remote_status.stdout").read_bytes(), b"partial-out")
            self.assertEqual((raw / "remote_status.stderr").read_bytes(), b"partial-err")

    def test_embedded_remote_programs_compile_and_preflight_is_pinned(self) -> None:
        compile("CONFIG={}\n" + runner_module.REMOTE_WORKER, "remote_worker.py", "exec")
        compile(runner_module.remote_status_source(runner_module.RUN_IDS[38299]),
                "remote_status.py", "exec")
        self.assertEqual(parser_module.sha256(runner_module.PREFLIGHT_SOURCE),
                         runner_module.PREFLIGHT_SOURCE_SHA256)


if __name__ == "__main__":
    unittest.main()
