# TASK E10 — Record ordered stops when prior evidence is missing or unreadable

## Frozen target and evidence

- Exact base and required direct parent: E09 target `d6ee96d923a91bf6db2e94eb109d970a238f8d68`.
- Builder branch/worktree: `agent/E10-prior-record-stop-remediation` / `/home/zhiro/research/kv260-vlm-workers/E10-prior-record-stop-remediation`.
- E09 failed exact-target review: R12 commit `b308c10f175954a8f323b42ff53960eb5cddcc25`, **FAIL P0=0/P1=0/P2=1**. Report SHA-256 `16b3fa1dacd80d9c1b34d532a9d951b9ea2bbd04ff8e1fab4839bf5063449904`; handoff SHA-256 `543b37cf5eca1477ebba89675d0807db4ca34a5a7adfda832e46d0cbf57a97e4`.
- E09 evidence and R12 report/handoff are frozen in `orchestration/evidence_snapshots/E10_prior_record_stop/SOURCE.sha256`.

## Objective

Fix only the R12 ordered-stop finding: if assessment of an earlier qid raises because its raw result is missing or unreadable, the requested qid and every later qid must receive parser-valid `cli_started: false` non-start records with an allowed prior-stop reason and the preceding run ID. No preflight, staging, worker, status query, copy, or score operation may run for the requested or later qids. Keep ordinary completed-but-failed previous-qid handling intact.

## Scope and acceptance

1. Verify exact E09 parent, clean worktree, and all frozen inputs before editing.
2. Make the smallest change in `scripts/run_board_cpu_p2_textvqa.py` and extend only `tests/test_p2_runner_orchestration.py`; add `orchestration/handoffs/E10_prior_record_stop_handoff.md`.
3. Use the same production-used `run_host_orchestration` seam. Convert prior assessment exceptions to a fail-closed unresolved stop and use the existing ordered non-start recording path. Keep the reason semantically accurate (`PRIOR_CASE_UNRESOLVED` is already in the parser enum); preserve the previous run ID. Ensure the command-line result reports the unresolved stop clearly.
4. Add a synthetic local fake case where `assess_previous` raises `ValueError` or `OSError`. Assert parser-valid current and later non-start records, correct prior run ID, no begin/preflight/stage/worker/status/copy/score calls, and a clear unresolved-stop decision. Keep the existing false-return prior-failure case.
5. Run exactly once and only once: `python3 -m unittest discover -s tests -p test_p2_runner_orchestration.py`. Do not run any other tests, syntax checks, dry plans, or source execution.
6. Change only the runner, focused orchestration test module, and this E10 handoff. Commit directly on exact E09 target with a clean worktree; record changed paths, one test result, output hashes, and limits.
7. R13 must independently review the exact E10 target and may independently run the same focused module once. Require exact-target R13 PASS before integrating E09/E10.

## Boundaries

Host-only local fakes and temporary directories. No board/SSH/network, runtime/inference/benchmark, reboot, bitstream, answer/annotation/user data, GitHub activity, resource-threshold/timeout changes, parser changes, image parsing, scoring changes, or E08 timestamp-contract changes. P2-7 remains open until R13 PASS. P2-5 remains closed only at source-parser level; runtime parser success and external board gates remain unverified. P3 stays `NO_GO_NOW`.
