# TASK E09 — P2-7 host runner recovery regression coverage

## Frozen target and evidence

- Exact source base and required direct parent: E08 target `215d3c1acb6a3091a84f53cfdacb644d90116871`.
- Builder branch/worktree: `agent/E09-runner-orchestration-regressions` / `/home/zhiro/research/kv260-vlm-workers/E09-runner-orchestration-regressions`.
- E01 P2-7 source: frozen runner-review report SHA-256 `8cafc732a0a9af26ca8da9e4097f1192b5b324661632904d93c27961621a6e3e`; overall E01 review SHA-256 `569712d404eb4cc2d18aa10759d37a2928cd1b03df2fcf493fc9ab4e0330ef1f`.
- E08 runner SHA-256 `cf0577bac5bc39eb42e43289eead86febeb30e6012adf0254860f3e24437d1fc`; parser SHA-256 `d31ef5a1df63ec1f0cd5a3c19c2a5f5ec34ea76b1d64ecb7be3aa8c0c5d4de45`.
- E08/R11 source and review are integrated at coordinator; exact review target was E08 `215d3c1acb6a3091a84f53cfdacb644d90116871`, R11 PASS P0=0/P1=0/P2=0.
- Frozen input manifest: `orchestration/evidence_snapshots/E09_runner_orchestration_regressions/SOURCE.sha256`.

## Objective and bounded scope

Close only E01 P2-7. E01 found helper tests but no test drove the host runner through remote-worker timeout recovery, board runner-lock contention, remote-status failure, incomplete evidence copy, or ordered stop behavior. Extract the smallest host orchestration decision seam needed so the production runner uses the same tested code with injectable subprocess/SSH/copy boundaries.

1. Verify exact parent, clean worktree, and all frozen manifest entries before editing.
2. Keep the current production defaults and frozen command/provenance contracts. Tests must use fake subprocess/SSH/copy dependencies and temporary local directories; they must never contact a board or network.
3. Add cases to one new focused module, `tests/test_p2_runner_orchestration.py`, covering these outcomes through the same host orchestration function the production runner calls:
   - **Worker timeout recovery:** do not relaunch the worker; make at most one status query; only proceed to raw copy after the exact current run ID is reported complete, the lock is free, completion marker is valid, and CLI/unreadable process lists are empty.
   - **Remote runner-lock contention:** the exact worker response `REMOTE_LOCK_BUSY` with `cli_started: false` is recorded as a parser-valid non-start for the current qid; stop and record later qids; never score or claim a CLI attempt. If needed, add only the `RUNNER_LOCK_BUSY` non-start enum to the parser and preserve the existing strict non-start schema.
   - **Status failure/unknown:** transport exception, nonzero return, malformed JSON, or incomplete status must remain unresolved; do not copy or score; stop later qids and preserve the current evidence state.
   - **Incomplete raw copy:** timeout, nonzero return, or manifest/hash failure must not reach scoring/image verification; preserve available partial output and stop later qids.
   - **Ordered stop:** when a prior qid failed or remains unresolved, the requested and later qids receive valid non-start records and no preflight, staging, worker, status, or copy operation is invoked for them.
4. The tests must assert call order/counts, status and non-start records, no retry, no scoring on incomplete evidence, and stop behavior. Use synthetic records and temporary paths only; do not read answers, annotations, or real request images.
5. Change only `scripts/run_board_cpu_p2_textvqa.py`, optionally `scripts/parse_board_textvqa_pilot.py` for the single new non-start enum described above, `tests/test_p2_runner_orchestration.py`, and `orchestration/handoffs/E09_runner_orchestration_regressions_handoff.md`.
6. Run exactly once, and only once, `python3 -m unittest discover -s tests -p test_p2_runner_orchestration.py`. Do not run the snapshot test module, full suite, syntax checks, dry plans, or any other execution.
7. Commit with direct parent E08 target and clean worktree. Record exact paths, test result, output SHA-256 values, and limitations in the handoff.
8. After delivery, R12 may independently run that same exact focused module once on the frozen E09 target; all other review is static.

## Boundaries

- Host-only; no SSH, board access, reboot, inference, benchmark, runtime execution, bitstream work, answer/annotation reads, or GitHub activity.
- Do not change resource thresholds, worker timeout values, board lock behavior except recording an exact lock-busy response as non-start, completion/receipt hashing, score rules, image parsing, or the E08 point-in-time timestamp contract. Do not claim request-long resource safety.
- Require exact-target independent R12 review before integration. P2-5 is closed only at source-parser level; runtime parser success and all external board gates remain unverified. P3 stays `NO_GO_NOW`.
