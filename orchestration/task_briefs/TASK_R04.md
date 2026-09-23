# TASK R04 — Independent review of E02 runner remediation

## Frozen review target

- E02 worker commit: `aad962435278e470d36b3a0f247e9fb5624cf0f1`.
- Required direct parent: `7385c0b10033244b3e203a3b152ca63720207222`.
- Target branch/worktree: `agent/E02-runner-remediation` / `/home/zhiro/research/kv260-vlm-workers/E02-runner-remediation`.
- The exact review manifest and activation are in the coordinator worktree. The E02 activation SHA-256 is `61dcb508521b068e933b13a2cebf90e895619f1731b1391359052cecdab93aab`.

## Review tasks

1. Verify the exact E02 parent, clean target worktree, and that the target commit changes only the two runner/preflight source files plus the handoff.
2. Verify all nine frozen E01 snapshot entries against their manifest; verify every E02 output hash and that the runner pins the exact updated preflight hash.
3. Statically inspect whether: (a) the two-sample per-process CPU gate has a conservative per-PID interval, rejects malformed/racy/unobservable process state, checks load against the recorded threshold, and runs before image staging; (b) marker presence is captured inside the board worker immediately before removal and bound into its evidence; (c) worker timeout partial output is persisted and recovery uses at most one bounded read-only status check, then only the strict complete-manifest/copy/hash path, otherwise `REMOTE_STATE_UNKNOWN` without rerun; and (d) execution requires and records the exact non-empty owner-window reference.
4. Inspect handoff wording against code. Retain E01 P2-5/6/7 and external gates as unresolved. Do not infer readiness from source inspection.

## Boundaries and output

- No tests, syntax checks, dry plans, benchmarks, script/runtime execution, SSH, board access, inference, reboot, bitstream action, answer/annotation reads, or GitHub activity.
- Add only `reviews/E02_runner_remediation_independent_review.md` and `orchestration/handoffs/R04_E02_review_handoff.md` on the reviewer branch.
- Report PASS/FAIL with P0/P1/P2 findings, exact target and output hashes, and evidence limits. Reviewer commit must directly parent the exact E02 target and leave a clean worktree.
- A PASS supports coordinator integration of this source-only patch. It does not clear remaining P2 gates or change P3 `NO_GO_NOW`.
