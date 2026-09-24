# TASK R12 — Independent review of E09 host runner orchestration

## Frozen target and evidence

- E09 target: `d6ee96d923a91bf6db2e94eb109d970a238f8d68`.
- Required direct parent: E08 target `215d3c1acb6a3091a84f53cfdacb644d90116871`.
- Builder branch/worktree: `agent/E09-runner-orchestration-regressions` / `/home/zhiro/research/kv260-vlm-workers/E09-runner-orchestration-regressions`.
- Reviewer branch/worktree: `agent/R12-E09-review` / `/home/zhiro/research/kv260-vlm-workers/R12-E09-review`, created at exact E09 target.
- E09 brief: `/home/zhiro/research/kv260-vlm-orchestration/orchestration/task_briefs/TASK_E09.md`; E09 activation: `/home/zhiro/research/kv260-vlm-orchestration/orchestration/activations/E09.md`; source manifest: `/home/zhiro/research/kv260-vlm-orchestration/orchestration/evidence_snapshots/E09_runner_orchestration_regressions/SOURCE.sha256`.
- E09 runner SHA-256 `02d2c794c292bdb350803f9d028866e8b256e5846581e789b42928851f1a9cdf`; parser SHA-256 `0e28f81cc26ec47cfe2488c680623c74accd1bef92d9a4f3a31ae2fa73ba3b8d`; focused test SHA-256 `6e91308f475e09bf4e84dafb8250d2ae27b3c30d2bc32243639e988667c78974`; builder handoff SHA-256 `efb156ad765fabd83c4b0a6f911991fe6c949c45607aa1ad529c3c67335830db`.
- E01 P2-7 focused runner-review evidence SHA-256 `8cafc732a0a9af26ca8da9e4097f1192b5b324661632904d93c27961621a6e3e`; overall E01 review SHA-256 `569712d404eb4cc2d18aa10759d37a2928cd1b03df2fcf493fc9ab4e0330ef1f`.
- R12 frozen inputs: `orchestration/evidence_snapshots/R12_E09_review/SOURCE.sha256`.

## Review tasks and limits

1. Verify the clean reviewer tree starts at exact E09 target, its direct parent is E08, only the four scoped builder paths changed, all frozen source hashes pass, and builder handoff identities/output hashes/test result agree.
2. Run exactly once the independently authorized command `python3 -m unittest discover -s tests -p test_p2_runner_orchestration.py`. Run no other tests, syntax checks, dry plans, or source/runtime execution.
3. Statically verify production `main()` calls the same `run_host_orchestration` state machine exercised by tests, and that real SSH, staging, worker, status, copy/hash, parser, and record operations are injected callbacks rather than parallel test-only logic.
4. Confirm worker timeout never relaunches and permits at most one status query; copy is reachable only for the exact run ID with complete state, existing run directory, free runner lock, valid completion marker, and empty CLI/unreadable process lists.
5. Confirm the exact `REMOTE_LOCK_BUSY` plus `cli_started: false` response creates a parser-schema-valid `RUNNER_LOCK_BUSY` non-start for the current qid, creates later non-start records, and cannot score or become a CLI attempt.
6. Confirm transport/nonzero/malformed/incomplete status stays unresolved without copy/scoring, and incomplete copy (timeout, nonzero, manifest, or hash failure) prevents scoring and stops later qids while retaining partial local evidence.
7. Confirm a failed or unresolved prior qid prevents the requested and later qids from starting preflight, staging, worker, status, copy, or scoring; check existing scoring, attempt denominator, image parsing, E08 resource timestamp contract, and point-in-time claims are preserved.

Add only `reviews/E09_runner_orchestration_independent_review.md` and `orchestration/handoffs/R12_E09_review_handoff.md`. Report PASS/FAIL and P0/P1/P2 findings, exact hashes, clean-tree evidence, the single independent test result, and claim limits. Commit must directly parent exact E09 target.

No board/SSH, runtime/inference/benchmark, answer/annotation access, reboot, bitstream, GitHub activity, broader tests, syntax checks, dry plans, or code changes. Do not integrate E09 unless R12 returns exact-target PASS. P2-5 remains closed only at source-parser level; runtime parser success and external board gates remain unverified. P3 stays `NO_GO_NOW`.
