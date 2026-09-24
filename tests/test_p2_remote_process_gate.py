import ast
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts/run_board_cpu_p2_textvqa.py"
TIMEOUT_IDENTITY = {
    "path": "/usr/bin/timeout",
    "resolved_path": "/usr/bin/timeout",
    "sha256": "0" * 64,
    "usable": True,
}
CONFIG = {
    "min_mem_available_kib": 2_750_000,
    "min_cma_free_kib": 700_000,
    "min_home_free_bytes": 1 << 30,
    "max_load1": 1.5,
    "max_busy_cores_per_process": 0.25,
    "timeout_executable": dict(TIMEOUT_IDENTITY),
}


def production_worker_namespace():
    """Execute the actual embedded worker source without entering its main()."""
    tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"), filename=str(RUNNER_PATH))
    assignment = next(
        node for node in tree.body
        if isinstance(node, ast.Assign) and
        any(isinstance(target, ast.Name) and target.id == "REMOTE_WORKER"
            for target in node.targets)
    )
    source = ast.literal_eval(assignment.value)
    namespace = {"__name__": "e11_test_remote_worker", "CONFIG": CONFIG}
    with patch("signal.signal"):
        exec(compile(source, str(RUNNER_PATH) + "::<REMOTE_WORKER>", "exec"), namespace)
    return namespace


WORKER = production_worker_namespace()


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        self.now += 0.001
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class ProcTree:
    def __init__(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="e11-proc-")
        self.root = Path(self.tempdir.name)

    def close(self):
        self.tempdir.cleanup()

    @staticmethod
    def stat_text(pid, comm, ticks, starttime):
        fields = ["S"] + ["0"] * 19
        fields[11] = str(ticks)
        fields[12] = "0"
        fields[19] = str(starttime)
        return f"{pid} ({comm}) " + " ".join(fields) + "\n"

    def add(self, pid, comm="python3", ticks=0, starttime=1, uid=1000):
        entry = self.root / str(pid)
        entry.mkdir(parents=True, exist_ok=True)
        (entry / "stat").write_text(self.stat_text(pid, comm, ticks, starttime), encoding="utf-8")
        (entry / "comm").write_text(comm + "\n", encoding="utf-8")
        (entry / "status").write_text(f"Name:\t{comm}\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n", encoding="utf-8")
        (entry / "cmdline").write_bytes(comm.encode("utf-8"))
        return entry

    def rewrite(self, pid, comm="python3", ticks=0, starttime=1, uid=1000):
        self.add(pid, comm, ticks, starttime, uid)


def passing_environment(selected_processes, process_count):
    return {
        "arch": "aarch64",
        "cpu_count": 4,
        "memory_kib": {
            "MemAvailable": 3_000_000,
            "CmaFree": 800_000,
            "SwapTotal": 0,
            "SwapFree": 0,
        },
        "home_free_bytes": 2 << 30,
        "loadavg": "0.10 0.20 0.30 1/10 900",
        "systemd_service_states": {
            "jupyter.service": {"active_state": "active", "returncode": 0, "timed_out": False},
            "apt-daily.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
            "apt-daily-upgrade.service": {"active_state": "inactive", "returncode": 3, "timed_out": False},
        },
        "packagekit_transaction_state": {"state": "SERVICE_INACTIVE", "timed_out": False},
        "timeout_executable": dict(TIMEOUT_IDENTITY),
        "selected_processes": selected_processes,
        "process_count": process_count,
    }


class RemoteProcessGateTests(unittest.TestCase):
    def setUp(self):
        self.proc = ProcTree()
        self.addCleanup(self.proc.close)
        self.proc.add(41, "python3", ticks=10)

    def rich_snapshot(self, mutate=None, tick_rate=100, advance_sleep=True):
        clock = FakeClock()

        def sleeper(seconds):
            if advance_sleep:
                clock.sleep(seconds)
            if mutate is not None:
                mutate()

        return WORKER["rich_snapshot"](
            proc_root=self.proc.root,
            sleep_fn=sleeper,
            clock=clock,
            sysconf=lambda _name: tick_rate,
            snapshot_fn=passing_environment,
            preflight_pid=41,
        )

    def assert_incomplete_blocks_prelaunch(self, snapshot):
        self.assertEqual(snapshot["process_cpu_sample_state"], "PROCESS_STATE_UNKNOWN")
        self.assertIn("PROCESS_STATE_UNKNOWN", snapshot["gate_reasons"])
        self.assertTrue(snapshot["gate_reasons"], "an incomplete process sample must block prelaunch")

    def test_unreadable_and_malformed_proc_entries_block(self):
        unreadable = self.proc.root / "52"
        unreadable.mkdir()
        (unreadable / "stat").mkdir()
        malformed = self.proc.root / "53"
        malformed.mkdir()
        (malformed / "stat").write_text("malformed stat record\n", encoding="utf-8")

        snapshot = self.rich_snapshot()

        self.assert_incomplete_blocks_prelaunch(snapshot)
        self.assertTrue(any(error.startswith("pid:52:") for error in snapshot["process_cpu_sample_errors"]))
        self.assertTrue(any(error.startswith("pid:53:") for error in snapshot["process_cpu_sample_errors"]))

    def test_appearing_and_disappearing_pids_block(self):
        self.proc.add(52, "idle", ticks=4)
        with self.subTest(change="appearing"):
            snapshot = self.rich_snapshot(mutate=lambda: self.proc.add(53, "idle", ticks=0))
            self.assert_incomplete_blocks_prelaunch(snapshot)
            self.assertIn("sample_pid_set_changed", snapshot["process_cpu_sample_errors"])

        self.proc.add(53, "idle", ticks=0)
        with self.subTest(change="disappearing"):
            snapshot = self.rich_snapshot(mutate=lambda: shutil.rmtree(self.proc.root / "53"))
            self.assert_incomplete_blocks_prelaunch(snapshot)
            self.assertIn("sample_pid_set_changed", snapshot["process_cpu_sample_errors"])

    def test_pid_reuse_starttime_change_blocks(self):
        self.proc.add(52, "idle", ticks=4, starttime=7)

        snapshot = self.rich_snapshot(
            mutate=lambda: self.proc.rewrite(52, "idle", ticks=5, starttime=8)
        )

        self.assert_incomplete_blocks_prelaunch(snapshot)
        self.assertIn("pid:52:identity_changed", snapshot["process_cpu_sample_errors"])

    def test_invalid_delta_tick_rate_and_elapsed_interval_block(self):
        self.proc.add(52, "idle", ticks=20)
        with self.subTest(invalid="negative delta"):
            snapshot = self.rich_snapshot(mutate=lambda: self.proc.rewrite(52, "idle", ticks=10))
            self.assert_incomplete_blocks_prelaunch(snapshot)
            self.assertIn("pid:52:invalid_cpu_delta", snapshot["process_cpu_sample_errors"])

        with self.subTest(invalid="tick rate"):
            snapshot = self.rich_snapshot(tick_rate=0)
            self.assert_incomplete_blocks_prelaunch(snapshot)
            self.assertTrue(any(error.startswith("clock_tick_rate:")
                                for error in snapshot["process_cpu_sample_errors"]))

        with self.subTest(invalid="elapsed interval"):
            snapshot = self.rich_snapshot(advance_sleep=False)
            self.assert_incomplete_blocks_prelaunch(snapshot)
            self.assertIn("sample_interval_invalid", snapshot["process_cpu_sample_errors"])

    def test_stable_below_threshold_sample_passes(self):
        self.proc.add(52, "idle", ticks=10)

        snapshot = self.rich_snapshot()

        self.assertEqual(snapshot["process_cpu_sample_state"], "OK")
        self.assertEqual(snapshot["gate_reasons"], [])

    def test_busy_process_sample_blocks(self):
        self.proc.add(52, "idle", ticks=0)

        snapshot = self.rich_snapshot(mutate=lambda: self.proc.rewrite(52, "idle", ticks=100))

        self.assertEqual(snapshot["process_cpu_sample_state"], "OK")
        self.assertIn("BUSY_CPU", snapshot["gate_reasons"])
        self.assertTrue(snapshot["gate_reasons"], "busy process CPU use must block prelaunch")


if __name__ == "__main__":
    unittest.main()
