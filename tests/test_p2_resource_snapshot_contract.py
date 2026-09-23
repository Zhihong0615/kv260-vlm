import unittest

from scripts.parse_board_textvqa_pilot import classify_resource_snapshot_evidence


def snapshot(gate_reasons=None):
    value = {
        "schema": "kv260_cpu_p2_textvqa_runtime_preflight_v3",
        "captured_at_utc": "2026-09-24T00:00:00Z",
        "gate_reasons": [] if gate_reasons is None else gate_reasons,
        "systemd_service_states": {
            "jupyter.service": {"active_state": "active", "returncode": 0, "timed_out": False},
            "apt-daily.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
            "apt-daily-upgrade.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
        },
        "packagekit_transaction_state": {"state": "SERVICE_INACTIVE", "timed_out": False},
        "timeout_executable": {
            "path": "/usr/bin/timeout",
            "resolved_path": "/usr/bin/timeout",
            "sha256": "0" * 64,
            "usable": True,
        },
    }
    value.update({
        "memory_kib": {
            "MemAvailable": 3_000_000,
            "CmaFree": 800_000,
            "SwapTotal": 0,
            "SwapFree": 0,
        },
        "jupyter_active": "active",
        "home_free_bytes": 2 << 30,
        "loadavg": "0.10 0.20 0.30",
        "selected_processes": [],
    })
    return value


class ResourceSnapshotContractTests(unittest.TestCase):
    def test_both_point_in_time_snapshots_pass(self):
        result = classify_resource_snapshot_evidence(snapshot(), snapshot(), "pilot")
        self.assertEqual(result["prelaunch_resource_gate_status"], "PASS")
        self.assertEqual(result["post_run_resource_gate_status"], "PASS")
        self.assertTrue(result["resource_gates_verified"])
        self.assertFalse(result["in_run_resource_monitoring_performed"])
        self.assertIn("point_in_time", result["resource_evidence_scope"])

    def test_post_run_gate_reason_fails_combined_gate(self):
        result = classify_resource_snapshot_evidence(
            snapshot(), snapshot(["MEMORY_GATE_DETERIORATED"]), "pilot"
        )
        self.assertEqual(result["prelaunch_resource_gate_status"], "PASS")
        self.assertEqual(result["post_run_resource_gate_status"], "FAIL")
        self.assertFalse(result["resource_gates_verified"])
        self.assertEqual(result["postflight_gate_reasons"], ["MEMORY_GATE_DETERIORATED"])

    def test_prelaunch_gate_reason_fails_combined_gate(self):
        result = classify_resource_snapshot_evidence(
            snapshot(["LOAD_GATE"]), snapshot(), "pilot"
        )
        self.assertEqual(result["prelaunch_resource_gate_status"], "FAIL")
        self.assertEqual(result["post_run_resource_gate_status"], "PASS")
        self.assertFalse(result["resource_gates_verified"])

    def test_malformed_snapshot_fails_closed(self):
        for missing_field in ("systemd_service_states", "packagekit_transaction_state", "gate_reasons"):
            with self.subTest(missing_field=missing_field):
                malformed_post = snapshot()
                malformed_post.pop(missing_field)
                result = classify_resource_snapshot_evidence(snapshot(), malformed_post, "pilot")
                self.assertEqual(result["post_run_resource_gate_status"], "MALFORMED")
                self.assertFalse(result["resource_gates_verified"])

    def test_host_rehearsal_reports_separate_scope(self):
        result = classify_resource_snapshot_evidence(snapshot(), snapshot(), "rehearsal")
        self.assertEqual(result["resource_gates_verified"], None)
        self.assertEqual(result["prelaunch_resource_gate_status"], "NOT_APPLICABLE")
        self.assertIn("board resources not sampled", result["resource_evidence_scope"])


if __name__ == "__main__":
    unittest.main()
