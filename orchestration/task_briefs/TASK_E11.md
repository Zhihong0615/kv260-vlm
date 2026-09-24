# TASK E11 — Fail closed on incomplete remote process samples before CLI launch

## Frozen target and evidence

- Exact source base and required direct parent: the R15 integration target recorded in `orchestration/activations/E11.md`.
- R15 exact-target review: `33d4a61be953380022e563b5bd495e3aeafe7a67`, direct parent `ad51e2784fbbc0697232ed265e49d2e804f18b9d`, verdict BLOCKED P0=0/P1=1/P2=3. Report SHA-256 `b9fb442cfa6dc16878aab813b77f8d9ce5ff46ec33b5a8c2a614d2040e6cd848`; handoff SHA-256 `004d8b947aa7d0d7ac8c10430c0b273ee4c42f2937d026eb525d820efedbb85a`.
- R14 adapter review remains integrated at the same source base: PASS_WITH_P2_FINDINGS P0=0/P1=0/P2=2; it is context only and is not an E11 change target.
- Frozen source manifest: `orchestration/evidence_snapshots/E11_remote_process_gate/SOURCE.sha256`.
- User taskbook: `/home/zhiro/Downloads/Codex_KV260_VLM_端到端研究任务书_v3.md`, SHA-256 `ad5e705e3a34510a28f1468ea619841e339b41a93a0c643821dbc80e53dc7b25`. Its execution contract authorizes bounded stage testing, review, repair, and archival; this brief narrows that authorization to the single focused command below.

## Objective and bounded scope

Fix only R15 P1: the final remote resource check after staging must not accept an incomplete process sample and proceed to the VLM CLI. The current pinned host preflight helper is a source reference for fail-closed process-sample semantics; do not modify it or its pinned hash.

1. Verify exact parent, clean worktree, and all frozen source hashes before editing.
2. In `scripts/run_board_cpu_p2_textvqa.py`, retain procfs read/parse failures as sample errors instead of silently discarding them. Detect before/after PID-set changes and process identity reuse (including start-time change); invalid/negative deltas and invalid tick/elapsed intervals must set `PROCESS_STATE_UNKNOWN`. The final post-staging `rich_snapshot()` and `gate()` must return a blocking reason before `Popen` for any unknown/incomplete sample. Keep the existing CPU, CMA, memory, load, timeout, service, and wait thresholds unchanged.
3. Add `tests/test_p2_remote_process_gate.py`. It must exercise the same production sampler/gate implementation used by the embedded remote worker, not a test-only duplicate. Use only synthetic temporary procfs trees/fakes and deterministic sampling; never read host `/proc`. Cover unreadable/malformed proc entries, appearing/disappearing PIDs, PID reuse/start-time changes, stable below-threshold samples, and a busy-process sample. Assert all incomplete/unknown cases produce a gate-blocking `PROCESS_STATE_UNKNOWN` and cannot be treated as a successful prelaunch decision.
4. Preserve R15 P2 findings as out of scope: non-permission cleanup/status read errors, enforcing one CLI across repeated owner-window references, and durable later non-start conflicts. Do not claim these were repaired.
5. Change only `scripts/run_board_cpu_p2_textvqa.py`, the new focused test module, and `orchestration/handoffs/E11_remote_process_gate_handoff.md`.
6. Run only `python3 -m unittest discover -s tests -p test_p2_remote_process_gate.py`, at most twice total: once after the initial implementation and, only if a correction is needed, once after that correction. If still failing after the second run, stop and preserve the failure. Do not run any other test, syntax check, import probe, dry plan, runner, remote worker, or hardware command.
7. Commit directly on the frozen target with a clean worktree. The handoff must record exact command/output, every run including failures, changed paths, source/test/handoff hashes, and evidence limitations. R16 independently reviews the exact E11 target; the R15 fail report must remain preserved at `reviews/audit/R15_current_runner_BLOCKED_20260924.md`.

## Boundaries

Host-only synthetic data. No SSH, board, runtime, inference, benchmark, reboot, bitstream, answers/annotations, primary-checkout writes, or GitHub activity. No resource threshold, timeout, remote application command, model input, parser, scoring, or P2 side-scope change. P3 remains `NO_GO_NOW`; this fix cannot itself authorize board execution.
