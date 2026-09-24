# E13 Handoff — Fail Closed on Remote CLI Process-Scan Errors

## Frozen target

- Branch: `agent/E13-process-scan-errors`
- Required direct parent: `dced7666bcb3c5f79efd2d983045bac35932d89b`
- Scope: close only R16 P2-1, which allowed non-permission `OSError` while reading `/proc/*/cmdline` to look like a completed empty process scan.
- R16 audit archive remains unchanged: `reviews/audit/R16_runner_PASS_WITH_P2_FINDINGS_20260924.md`, SHA-256 `725afd51970d77fc9430584d374f2ccb28600400da1833e50baab5d11ac1ae64`.

## Changes

- `scripts/run_board_cpu_p2_textvqa.py`: `owned_cli_processes()` now accepts an injectable procfs root defaulting to `/proc`; `FileNotFoundError` is treated as a process-exit race and every other per-entry `OSError` is recorded as unreadable. `remote_status_source()` accepts test-only procfs and base-directory inputs with the original production defaults; its generated scan follows the same error rule. Top-level procfs iteration errors propagate, so the generated command fails instead of reporting an empty successful scan.
- `tests/test_p2_remote_process_scan_errors.py`: executes the actual embedded worker helper and generated status source using only synthetic temporary directories. It covers empty and non-CLI scans, disappearing entries, unreadable cmdlines, visible CLI PIDs, and top-level iteration failure.

## Authorized test invocations

Only the authorized focused command was run, twice total. The first run exposed test-fixture mistakes (attempting to create a directory over an existing synthetic cmdline file and using a production path for a synthetic base); these were corrected in the test module before the second and final run.

Command, attempt 1:

```text
python3 -m unittest discover -s tests -p test_p2_remote_process_scan_errors.py
```

Exact combined output (exit code 1):

```text
.EF.E
======================================================================
ERROR: test_remote_status_does_not_complete_when_cmdline_scan_is_unreadable (test_p2_remote_process_scan_errors.RemoteProcessScanErrorTests.test_remote_status_does_not_complete_when_cmdline_scan_is_unreadable)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/zhiro/research/kv260-vlm-workers/E13-process-scan-errors/tests/test_p2_remote_process_scan_errors.py", line 130, in test_remote_status_does_not_complete_when_cmdline_scan_is_unreadable
    (unreadable / "cmdline").mkdir()
  File "/usr/lib/python3.12/pathlib.py", line 1313, in mkdir
    os.mkdir(self, mode)
FileExistsError: [Errno 17] File exists: '/tmp/e13-status-proc-duqn9892/4301/cmdline'

======================================================================
ERROR: test_worker_helper_keeps_found_and_unreadable_processes_visible (test_p2_remote_process_scan_errors.RemoteProcessScanErrorTests.test_worker_helper_keeps_found_and_unreadable_processes_visible)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/zhiro/research/kv260-vlm-workers/E13-process-scan-errors/tests/test_p2_remote_process_scan_errors.py", line 95, in test_worker_helper_keeps_found_and_unreadable_processes_visible
    (unreadable / "cmdline").mkdir()
  File "/usr/lib/python3.12/pathlib.py", line 1313, in mkdir
    os.mkdir(self, mode)
FileExistsError: [Errno 17] File exists: '/tmp/e13-worker-proc-zkysyibw/4102/cmdline'

======================================================================
FAIL: test_remote_status_exposes_a_found_cli_pid (test_p2_remote_process_scan_errors.RemoteProcessScanErrorTests.test_remote_status_exposes_a_found_cli_pid)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/zhiro/research/kv260-vlm-workers/E13-process-scan-errors/tests/test_p2_remote_process_scan_errors.py", line 148, in test_remote_status_exposes_a_found_cli_pid
    self.assertEqual(status["state"], "REMOTE_STATE_UNKNOWN")
AssertionError: 'COMPLETE' != 'REMOTE_STATE_UNKNOWN'
- COMPLETE
+ REMOTE_STATE_UNKNOWN

----------------------------------------------------------------------
Ran 5 tests in 0.005s

FAILED (failures=1)
```

Command, attempt 2:

```text
python3 -m unittest discover -s tests -p test_p2_remote_process_scan_errors.py
```

Exact output (exit code 0):

```text
.....
----------------------------------------------------------------------
Ran 5 tests in 0.005s

OK
```

## Hashes and limits

- Runner SHA-256: `418c72316a055d0260ba88ccf85e31dba98cc0e0256d499fefa96063aa82e694`
- Focused test SHA-256: `55b87f3afae7eab92f811209ecea5a5794699a615d048ed77238aa3f74a330c1`
- R16 handoff SHA-256 (unchanged): `7b3c621a6e46a8e075bec7786402950bfd9b6c9d5c1c518a49a9daa348eb76e0`
- No host `/proc`, board, SSH, network, runtime, inference, benchmark, reboot, bitstream, or user data was accessed. No parser or runner command was executed; only the authorized focused unittest command ran.
- This establishes source and synthetic-test behavior only. It does not establish live procfs visibility, board cleanup success, board readiness, or closure of R16 P2-2/P2-3. P3 remains `NO_GO_NOW`; R19 exact-target review is still required.
