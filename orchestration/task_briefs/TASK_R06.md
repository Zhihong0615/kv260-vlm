# TASK R06 — Independent review of E03 preflight validation hardening

## Frozen review target

- E03 worker commit: `9c048ce95400a8156c919dd0d0bb4279cace47cc`.
- Required direct parent: `c550d3fe7e5272e6fee42d259d7f861b55ea4b2a`.
- Target branch/worktree: `agent/E03-runner-validation-hardening` / `/home/zhiro/research/kv260-vlm-workers/E03-runner-validation-hardening`.
- Reviewer branch/worktree: `agent/R06-E03-review` / `/home/zhiro/research/kv260-vlm-workers/R06-E03-review`, checked out at the exact E03 target.
- E03 brief SHA-256: `aef22eb90cf13f0e73c612000d70dc319df2169c9e9c7a15945e99b0d189eca8`.
- E03 activation SHA-256: `815c7b2eddd196e42b7220a6688c12086a67cb4a21a27742fbd4d3bd258cb570`.
- Five-entry review manifest: `orchestration/evidence_snapshots/R06_E03_review/SOURCE.sha256`; SHA-256 `8fc8b41e33da2f1fcbe99aa10b7cabcadcf9d99dca03f44e5c1aa465510f1ca9`.

## Review tasks

1. Verify the exact E03 parent, clean target worktree, and only the named source/handoff changes.
2. Verify every entry in the five-entry R06 manifest from the E03 target repository root; verify the E03 brief and activation hashes from the coordinator root.
3. Independently inspect both host and embedded board load gates. Confirm malformed/missing values and `nan`, `inf`, `-inf`, or negative finite values add a blocking reason; finite nonnegative values retain the configured threshold. Trace the host block path to before image staging, and the worker gate to before CLI launch.
4. Independently inspect malformed `process_cpu_rows` cases (wrong container, non-dict rows, missing/wrong-typed required fields) and confirm threshold evaluation cannot index malformed data or escape the structured blocked/nonstart-record path. Confirm valid row, uniqueness, preflight PID, and busy-core threshold semantics remain intact.
5. Assess the exact scope and E03 handoff claims. Preserve E01 P2-5/6/7 and all external gates as open; do not imply board readiness or change P3.

## Boundaries and outputs

- Static review only. Do not run tests, syntax checks, dry plans, benchmarks, inference, answer/annotation reads, board/SSH, reboot, bitstream work, or GitHub activity. Do not run the target code.
- Add only `reviews/E03_preflight_validation_independent_review.md` and `orchestration/handoffs/R06_E03_review_handoff.md` on the reviewer branch.
- Report PASS/FAIL with P0/P1/P2 findings, exact target/output hashes, claim limits, and clean-tree evidence. Reviewer commit must directly parent the exact E03 target.
- No coordinator integration before PASS. This does not establish board readiness; P3 remains `NO_GO_NOW`.
