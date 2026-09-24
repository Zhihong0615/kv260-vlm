import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts/run_board_cpu_p2_textvqa.py"
CLI_NEEDLE = b"/home/ubuntu/kv260-vlm-p2-cpu/build-cpu/bin/llama-mtmd-cli"
RUN_ID = "e13-synthetic-run"


def production_worker_namespace():
    tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"), filename=str(RUNNER_PATH))
    assignment = next(
        node for node in tree.body
        if isinstance(node, ast.Assign) and
        any(isinstance(target, ast.Name) and target.id == "REMOTE_WORKER"
            for target in node.targets)
    )
    source = ast.literal_eval(assignment.value)
    namespace = {"__name__": "e13_test_remote_worker"}
    with patch("signal.signal"):
        exec(compile(source, str(RUNNER_PATH) + "::<REMOTE_WORKER>", "exec"), namespace)
    return namespace


def production_remote_status_factory():
    tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"), filename=str(RUNNER_PATH))
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == "remote_status_source")
    module = ast.Module(body=[function], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"Path": Path, "str": str}
    exec(compile(module, str(RUNNER_PATH) + "::<remote_status_source>", "exec"), namespace)
    return namespace["remote_status_source"]


WORKER = production_worker_namespace()
REMOTE_STATUS_SOURCE = production_remote_status_factory()


def add_process(proc_root, pid, cmdline=CLI_NEEDLE):
    process = proc_root / str(pid)
    process.mkdir(parents=True)
    if cmdline is not None:
        (process / "cmdline").write_bytes(cmdline)
    return process


def make_completed_run(base_dir):
    run_dir = base_dir / "runs" / RUN_ID
    run_dir.mkdir(parents=True)
    (base_dir / "runs" / ".cpu_p2_runner.lock").touch()
    payload = b"synthetic completed artifact\n"
    (run_dir / "payload.bin").write_bytes(payload)
    (run_dir / "result.json").write_text(json.dumps({
        "status": "REQUEST_FINISHED",
        "cli_started": True,
        "remote_process_cleanup_verified": True,
    }), encoding="utf-8")
    completion = {
        "schema": "kv260_cpu_p2_textvqa_board_completion_v1",
        "run_id": RUN_ID,
        "manifest": {
            "payload.bin": {
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
        },
    }
    (run_dir / "completion.json").write_text(json.dumps(completion), encoding="utf-8")
    return run_dir


def run_remote_status(proc_root, base_dir):
    source = REMOTE_STATUS_SOURCE(RUN_ID, proc_root=proc_root, base_dir=base_dir)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(compile(source, "<generated-remote-status>", "exec"),
             {"__name__": "e13_test_remote_status"})
    return json.loads(output.getvalue())


class RemoteProcessScanErrorTests(unittest.TestCase):
    def test_worker_helper_keeps_found_and_unreadable_processes_visible(self):
        with tempfile.TemporaryDirectory(prefix="e13-worker-proc-") as tempdir:
            proc_root = Path(tempdir)
            add_process(proc_root, 4101, CLI_NEEDLE)
            unreadable = add_process(proc_root, 4102, cmdline=None)
            (unreadable / "cmdline").mkdir()
            add_process(proc_root, 4103, b"python3\0not-the-board-cli")
            add_process(proc_root, 4104, cmdline=None)  # Process-exit/FileNotFoundError race.

            found, unreadable_pids = WORKER["owned_cli_processes"](proc_root)

            self.assertEqual(found, [4101])
            self.assertEqual(unreadable_pids, [4102])

    def test_remote_status_admits_empty_non_cli_and_disappeared_process_scans(self):
        with tempfile.TemporaryDirectory(prefix="e13-status-base-") as base_tempdir, \
                tempfile.TemporaryDirectory(prefix="e13-status-proc-") as proc_tempdir:
            base_dir = Path(base_tempdir)
            proc_root = Path(proc_tempdir)
            make_completed_run(base_dir)

            empty = run_remote_status(proc_root, base_dir)
            self.assertEqual(empty["state"], "COMPLETE")
            self.assertEqual(empty["board_cli_processes"], [])
            self.assertEqual(empty["unreadable_processes"], [])

            add_process(proc_root, 4201, b"python3\0idle-worker")
            add_process(proc_root, 4202, cmdline=None)  # FileNotFoundError is a process-exit race.
            non_cli = run_remote_status(proc_root, base_dir)
            self.assertEqual(non_cli["state"], "COMPLETE")
            self.assertEqual(non_cli["board_cli_processes"], [])
            self.assertEqual(non_cli["unreadable_processes"], [])

    def test_remote_status_does_not_complete_when_cmdline_scan_is_unreadable(self):
        with tempfile.TemporaryDirectory(prefix="e13-status-base-") as base_tempdir, \
                tempfile.TemporaryDirectory(prefix="e13-status-proc-") as proc_tempdir:
            base_dir = Path(base_tempdir)
            proc_root = Path(proc_tempdir)
            make_completed_run(base_dir)
            unreadable = add_process(proc_root, 4301, cmdline=None)
            (unreadable / "cmdline").mkdir()

            status = run_remote_status(proc_root, base_dir)

            self.assertEqual(status["state"], "REMOTE_STATE_UNKNOWN")
            self.assertEqual(status["unreadable_processes"], [4301])
            self.assertEqual(status["board_cli_processes"], [])

    def test_remote_status_exposes_a_found_cli_pid(self):
        with tempfile.TemporaryDirectory(prefix="e13-status-base-") as base_tempdir, \
                tempfile.TemporaryDirectory(prefix="e13-status-proc-") as proc_tempdir:
            base_dir = Path(base_tempdir)
            proc_root = Path(proc_tempdir)
            make_completed_run(base_dir)
            cli_needle = str(base_dir / "build-cpu/bin/llama-mtmd-cli").encode()
            add_process(proc_root, 4401, cli_needle)

            status = run_remote_status(proc_root, base_dir)

            self.assertEqual(status["state"], "REMOTE_STATE_UNKNOWN")
            self.assertEqual(status["board_cli_processes"], [4401])
            self.assertEqual(status["unreadable_processes"], [])

    def test_remote_status_top_level_procfs_failure_cannot_look_empty(self):
        with tempfile.TemporaryDirectory(prefix="e13-status-base-") as base_tempdir, \
                tempfile.TemporaryDirectory(prefix="e13-status-proc-file-") as proc_tempdir:
            base_dir = Path(base_tempdir)
            proc_file = Path(proc_tempdir) / "not-a-directory"
            proc_file.write_text("synthetic", encoding="utf-8")
            make_completed_run(base_dir)
            source = REMOTE_STATUS_SOURCE(RUN_ID, proc_root=proc_file, base_dir=base_dir)

            with self.assertRaises(NotADirectoryError):
                exec(compile(source, "<generated-remote-status>", "exec"),
                     {"__name__": "e13_test_remote_status"})


if __name__ == "__main__":
    unittest.main()
