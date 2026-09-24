# TASK E13 — Fail closed on remote CLI process-scan errors

## Frozen target and evidence

- Exact source base and required direct parent: recorded in `orchestration/activations/E13.md` after E12/R17 integration.
- R16 exact-target runner review: `reviews/audit/R16_runner_PASS_WITH_P2_FINDINGS_20260924.md`, SHA-256 `725afd51970d77fc9430584d374f2ccb28600400da1833e50baab5d11ac1ae64`.
- Scope is only R16 P2-1: `owned_cli_processes()` and the generated `remote_status_source()` scan can discard non-permission `OSError` while reading `/proc/*/cmdline`, allowing an incomplete cleanup/status scan to look like no owned CLI.
- Activation must pin the current runner SHA, focused-test SHA, R16 review and handoff hashes, parser context, taskbook hash, and source manifest.

## Objective and bounded scope

Fix only the two remote CLI presence scans so non-transient inspection errors remain visible and cannot support cleanup verification or `COMPLETE` remote status.

1. In the embedded worker's `owned_cli_processes()`, keep an injectable procfs-root defaulting to `/proc` for synthetic testing. Treat an entry that disappears with `FileNotFoundError` as a process-exit race; report every other `OSError` as unreadable/unknown so existing `cleanup_verified` logic stays false. Do not change the process CPU sampler, resource thresholds, timeout behavior, or result schema.
2. In `remote_status_source()`, add test-only input parameters for procfs root and base directory while keeping production defaults unchanged. Its generated source must also retain non-`FileNotFoundError` scan errors in the existing `unreadable_processes` field; an incomplete scan must not reach `state: COMPLETE`. A top-level procfs iteration failure may return a nonzero/unknown remote status, but must never be treated as an empty process list.
3. Add `tests/test_p2_remote_process_scan_errors.py`, executing the actual embedded worker helper and actual generated remote status source against synthetic temporary directories only. Construct a valid synthetic completion marker and lock state so a non-permission cmdline read error (for example `IsADirectoryError`) would yield false `COMPLETE` with the old code and must remain unknown with the fix. Verify normal empty/non-CLI scans remain admissible and found CLI PIDs remain visible. Do not access host `/proc`.
4. Preserve `FileNotFoundError` process-exit handling, output keys and types, parser contract, and all unrelated resource/owner-window/non-start behavior. Do not address R16 P2-2 or P2-3 in this task.
5. Change only `scripts/run_board_cpu_p2_textvqa.py`, the new focused test module, and `orchestration/handoffs/E13_process_scan_errors_handoff.md` in the worker commit.
6. Run only `python3 -m unittest discover -s tests -p test_p2_remote_process_scan_errors.py`, at most twice total and only once after the initial patch unless a correction is needed. No other tests, imports, parser/runner execution, dry plan, board, SSH, runtime, inference, benchmark, reboot, bitstream, network, user data, primary-checkout writes, or GitHub activity.
7. Commit directly on the frozen target with a clean worktree. Record every authorized invocation, exact output, changed paths, source/test/handoff hashes, and limitations. R19 independently reviews the exact E13 target and runs the same focused module once. Preserve the R16 audit report unchanged.

## Acceptance and limitations

Close only R16 P2-1 at source/synthetic-test level after exact-target R19 returns P0=0/P1=0. Do not claim live `/proc` visibility, board cleanup success, board readiness, or resolution of the two other R16 P2 findings. P3 remains `NO_GO_NOW`.
