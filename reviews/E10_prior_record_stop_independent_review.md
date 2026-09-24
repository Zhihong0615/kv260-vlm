# R13 — E10 unresolved-prior ordered-stop independent review

## Verdict

**PASS — P0: 0, P1: 0, P2: 0.** E10 handles missing/unreadable prior evidence as an unresolved assessment, records the requested and later qids as parser-valid non-starts bound to the preceding run, avoids all start-side callbacks, and reports the unresolved decision. The ordinary previous-assessment false path remains `PRIOR_CASE_FAILED`. The final E10 target's authorized focused test passed.

## Frozen identity and review mode

- `review_mode`: `independent_static_source_review_with_one_authorized_focused_test`
- `reviewer_role`: `exact_target_independent_reviewer`
- E10 target: `feac56916af589725e55e4f524ec4049fc565348`
- Required direct parent: E09 `d6ee96d923a91bf6db2e94eb109d970a238f8d68` (verified)
- Reviewer branch/worktree: `agent/R13-E10-review` / `/home/zhiro/research/kv260-vlm-workers/R13-E10-review`
- At review start: exact target HEAD and clean worktree verified. Builder branch/worktree `agent/E10-prior-record-stop-remediation` / `/home/zhiro/research/kv260-vlm-workers/E10-prior-record-stop-remediation` is clean at the exact target and directly parents E09.
- R13 task brief SHA-256: `2ca43946c839c2f597e60979948a34ab656ae82e1cedb9b29a47e5c11bd016d6`
- R13 activation SHA-256: `0a8af3f5a47d9ef453c66ba57c44b8c47a12148053bd745bd1f32d0638a0596e`
- R13 input manifest SHA-256: `838d376d266d87b8f6b1ee50f6aca10e089610fd7316730895b7ae58c5d26b2c`; all 17 entries passed verification from the reviewer worktree.
- E10 task brief SHA-256: `21eb5bfee5b3b9f9fca911df4f558f18bda4c1d33d0c9579f793dd450c104c3a`
- E10 activation SHA-256: `0e04d0d7b8cbb4e2268a8b8b6cd9f052ab3c37601defe5fefbb348dd8424d330`
- E10 input manifest SHA-256: `328d4393322aee1386adc78814ca7668a9a2cd0a06abde1298ef13b884504814`
- E10 runner / focused-test / builder-handoff SHA-256: `8f07232ef2bcfe78e3f5cd331273796de6db87402a8e502ca4980dc89682c577` / `f6493c9e45696e7bd02305567159dcd8e70e910bd55b2e875376b262213bec56` / `782a2d3313e8e2a48f93af50999bcadde1474583e62bb74ce113612536f70af9`
- E10 changed exactly three paths: `scripts/run_board_cpu_p2_textvqa.py`, `tests/test_p2_runner_orchestration.py`, and `orchestration/handoffs/E10_prior_record_stop_handoff.md`.
- R12 finding commit: `b308c10f175954a8f323b42ff53960eb5cddcc25` (FAIL, P0=0/P1=0/P2=1); its report and handoff were among the frozen R13 inputs.

## Review results

### Exception-to-unresolved production path

`run_host_orchestration()` wraps `ops.assess_previous(previous_qid)` in a catch for `OSError`, `ValueError`, `KeyError`, and `TypeError` (`scripts/run_board_cpu_p2_textvqa.py:86-93`). This covers the prior failure: production `assess_previous()` raises `ValueError` when the prior raw directory is missing (`1012-1018`); unreadable records may raise `OSError`, and malformed/missing data may raise the other caught types. The catch writes `PRIOR_CASE_UNRESOLVED` non-starts for `order[index:]`, using `run_ids[previous_qid]` as their prior run ID, then returns an explicit unresolved decision with exit code 1.

Because the catch returns before `ops.begin()`, none of `begin`, preflight, stage, worker, status, copy, or score can run. The fake exception case asserts the exact call list, both non-start records, the preceding run ID, unresolved qid, requested qid, and error text (`tests/test_p2_runner_orchestration.py:248-267`). The fixture's `non_start_at_utc` is an aware UTC timestamp (`2026-09-24T00:00:00+00:00`); the production writer uses `datetime.now(timezone.utc).isoformat()` (`run_board_cpu_p2_textvqa.py:1021-1038`).

The generated result has `schema: kv260_cpu_p2_textvqa_execution_v1`, the proper qid, `cli_started: false`, reason, UTC non-start timestamp, preceding `prior_run_id`, and the allowed timeout-identity metadata (`1021-1038`). `PRIOR_CASE_UNRESOLVED` is in the parser's allowed reason set, the parser requires an aware UTC timestamp, requires the referenced prior run to precede the non-start qid, and rejects execution/start evidence on a non-start (`parse_board_textvqa_pilot.py:109-121, 735-758`). Thus the current and later records satisfy the parser's non-start contract and remain outside the CLI attempted denominator.

`main()` prints the decision JSON for both `PRIOR_CASE_FAILED` and `PRIOR_CASE_UNRESOLVED`, then returns the decision's nonzero code (`run_board_cpu_p2_textvqa.py:1460-1465`). The ordinary `assess_previous()` return-false path still records current/later `PRIOR_CASE_FAILED` non-starts and avoids all start-side callbacks (`run_host_orchestration()` lines 94-97; test lines 230-246).

### Preserved E09/E08 behavior

E10 changes only the prior-assessment exception path and its test. E09 timeout/no-retry and one-status-query behavior, exact lock-busy handling, strict remote-status predicate, verified-copy-before-score order, partial-copy retention, and failed-case ordered stop remain unchanged in the target diff. The parser is unchanged from E09, preserving its `RUNNER_LOCK_BUSY`/unresolved non-start schema, attempted denominator and zero-score failure behavior, and E08 resource timestamp ordering. Point-in-time resource evidence remains distinct from in-run monitoring. No board-readiness or request-long safety claim follows.

### Independent test result

The E10 handoff notes its builder test ran before the final catch-clause narrowing. On the exact final E10 target, the only independently run command authorized by TASK_R13 was:

```text
python3 -m unittest discover -s tests -p test_p2_runner_orchestration.py
```

Result: **Ran 6 tests in 0.003s — OK.** No other tests, syntax checks, dry plans, or source/runtime execution were performed.

## Claim limits and disposition

This is static host-runner review plus one local fake-operation test module. No board/SSH/network/runtime/inference/benchmark, answer/annotation/user data, reboot, bitstream, or GitHub activity was used. The tests do not establish live board behavior or parser runtime success. P2-7 receives this source-level ordered-stop PASS; P2-5 remains closed only at source-parser level, external board gates remain unverified, and P3 stays `NO_GO_NOW`.

**Disposition:** E10 receives exact-target R13 PASS for the unresolved-prior ordered-stop remediation. This review does not authorize a board run or change global go/no-go.
