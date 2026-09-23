import unittest

from scripts.parse_board_textvqa_pilot import classify_resource_snapshot_evidence


TIMEOUT_IDENTITY = {
    "path": "/usr/bin/timeout",
    "resolved_path": "/usr/bin/timeout",
    "sha256": "0" * 64,
    "usable": True,
}


def runner_snapshot(gate_reasons=None):
    """Shape emitted by the embedded remote worker's rich_snapshot()."""
    return {
        "schema": "kv260_cpu_p2_textvqa_runtime_preflight_v3",
        "captured_at_utc": "2026-09-24T00:00:00Z",
        "scope": "read-only bounded CPU-only TextVQA preflight",
        "arch": "aarch64",
        "cpu_count": 4,
        "memory_kib": {
            "MemTotal": 6_000_000,
            "MemAvailable": 3_000_000,
            "CmaFree": 800_000,
            "SwapTotal": 0,
            "SwapFree": 0,
        },
        "vmstat_global": {"oom_kill": 0, "pgmajfault": 0, "pswpin": 0, "pswpout": 0},
        "home_free_bytes": 2 << 30,
        "loadavg": "0.10 0.20 0.30 1/10 900",
        "systemd_service_states": {
            "jupyter.service": {"active_state": "active", "returncode": 0, "timed_out": False},
            "apt-daily.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
            "apt-daily-upgrade.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
            "packagekit.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
        },
        "jupyter_active": "active",
        "jupyter_returncode": 0,
        "packagekit_transaction_state": {
            "state": "SERVICE_INACTIVE",
            "transaction_ids": [],
            "returncode": None,
            "timed_out": False,
        },
        "timeout_executable": dict(TIMEOUT_IDENTITY),
        "selected_processes": [],
        "process_count": 400,
        "cpu_frequency_khz": {"cpu0": 1_200_000},
        "thermal_c": {"cpu0": 45.0},
        "gate_reasons": [] if gate_reasons is None else gate_reasons,
    }


def classify(pre=None, post=None):
    return classify_resource_snapshot_evidence(
        runner_snapshot() if pre is None else pre,
        runner_snapshot() if post is None else post,
        "pilot",
        TIMEOUT_IDENTITY,
    )


class ResourceSnapshotContractTests(unittest.TestCase):
    def test_both_runner_snapshots_pass(self):
        result = classify()
        self.assertEqual(result["prelaunch_resource_gate_status"], "PASS")
        self.assertEqual(result["post_run_resource_gate_status"], "PASS")
        self.assertTrue(result["resource_gates_verified"])
        self.assertFalse(result["in_run_resource_monitoring_performed"])
        self.assertIn("point_in_time", result["resource_evidence_scope"])

    def test_prelaunch_gate_reasons_fail_combined_gate(self):
        result = classify(pre=runner_snapshot(["LOAD"]))
        self.assertEqual(result["prelaunch_resource_gate_status"], "FAIL")
        self.assertEqual(result["post_run_resource_gate_status"], "PASS")
        self.assertFalse(result["resource_gates_verified"])

    def test_post_run_gate_reasons_fail_combined_gate(self):
        result = classify(post=runner_snapshot(["MEMAVAILABLE"]))
        self.assertEqual(result["prelaunch_resource_gate_status"], "PASS")
        self.assertEqual(result["post_run_resource_gate_status"], "FAIL")
        self.assertFalse(result["resource_gates_verified"])
        self.assertEqual(result["postflight_gate_reasons"], ["MEMAVAILABLE"])

    def test_malformed_containers_fail_closed(self):
        for missing_field in ("systemd_service_states", "packagekit_transaction_state", "gate_reasons"):
            with self.subTest(missing_field=missing_field):
                malformed_post = runner_snapshot()
                malformed_post.pop(missing_field)
                result = classify(post=malformed_post)
                self.assertEqual(result["post_run_resource_gate_status"], "MALFORMED")
                self.assertFalse(result["resource_gates_verified"])

    def test_prelaunch_nonfinite_and_negative_load_fail_closed(self):
        for value in (
            "nan 0.20 0.30 1/10 900",
            "inf 0.20 0.30 1/10 900",
            "-inf 0.20 0.30 1/10 900",
            "-0.1 0.20 0.30 1/10 900",
            "0.10 nan 0.30 1/10 900",
            "0.10 0.20 -inf 1/10 900",
        ):
            with self.subTest(load1=value):
                malformed_pre = runner_snapshot()
                malformed_pre["loadavg"] = value
                result = classify(pre=malformed_pre)
                self.assertNotEqual(result["prelaunch_resource_gate_status"], "PASS")
                self.assertFalse(result["resource_gates_verified"])

    def test_missing_post_run_measurements_fail_closed(self):
        for missing_field in (
            "memory_kib", "vmstat_global", "home_free_bytes", "loadavg", "selected_processes",
            "process_count",
        ):
            with self.subTest(missing_field=missing_field):
                malformed_post = runner_snapshot()
                malformed_post.pop(missing_field)
                result = classify(post=malformed_post)
                self.assertEqual(result["post_run_resource_gate_status"], "MALFORMED")
                self.assertFalse(result["resource_gates_verified"])

    def test_malformed_process_rows_fail_closed(self):
        malformed_pre = runner_snapshot()
        malformed_pre["selected_processes"] = [{"pid": 123, "comm": "apt", "role": "process"}]
        result = classify(pre=malformed_pre)
        self.assertEqual(result["prelaunch_resource_gate_status"], "MALFORMED")
        self.assertFalse(result["resource_gates_verified"])

    def test_forbidden_process_cannot_pass_with_empty_gate_reasons(self):
        inconsistent_pre = runner_snapshot()
        inconsistent_pre["selected_processes"] = [
            {"pid": 123, "uid": 0, "comm": "apt", "role": "process"}
        ]
        result = classify(pre=inconsistent_pre)
        self.assertEqual(result["prelaunch_resource_gate_status"], "INCONSISTENT")
        self.assertIn("forbidden_process_gate", result["prelaunch_resource_consistency_issues"])
        self.assertFalse(result["resource_gates_verified"])

    def test_post_run_active_service_cannot_match_empty_gate_reasons(self):
        inconsistent_post = runner_snapshot()
        inconsistent_post["systemd_service_states"]["apt-daily.service"] = {
            "active_state": "active", "returncode": 0, "timed_out": False,
        }
        result = classify(post=inconsistent_post)
        self.assertEqual(result["post_run_resource_gate_status"], "INCONSISTENT")
        self.assertIn("package_upgrade_service_gate", result["post_run_resource_consistency_issues"])
        self.assertFalse(result["resource_gates_verified"])

    def test_post_run_memory_gate_cannot_pass_with_empty_reasons(self):
        inconsistent_post = runner_snapshot()
        inconsistent_post["memory_kib"]["MemAvailable"] = 100
        result = classify(post=inconsistent_post)
        self.assertEqual(result["post_run_resource_gate_status"], "INCONSISTENT")
        self.assertIn("memory_or_cma_gate", result["post_run_resource_consistency_issues"])
        self.assertFalse(result["resource_gates_verified"])

    def test_host_rehearsal_reports_separate_scope(self):
        result = classify_resource_snapshot_evidence(
            runner_snapshot(), runner_snapshot(), "rehearsal"
        )
        self.assertIsNone(result["resource_gates_verified"])
        self.assertEqual(result["prelaunch_resource_gate_status"], "NOT_APPLICABLE")
        self.assertIn("board resources not sampled", result["resource_evidence_scope"])


if __name__ == "__main__":
    unittest.main()
