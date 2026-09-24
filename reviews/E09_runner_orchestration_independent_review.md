# R12 — E09 host runner orchestration independent review

## Verdict

**FAIL — P0: 0, P1: 0, P2: 1.** E09 routes production `main()` through the same orchestration state machine exercised by the fake-operation tests. Timeout recovery, remote-status gating, incomplete-copy handling, lock-busy non-starts, and ordinary ordered-stop behavior are statically sound. One required ordered-stop case remains unhandled: if prior-run assessment raises because the previous raw directory is missing, execution stops before board-facing operations, but current and later qids receive no parser-valid non-start records. This leaves the E09/P2-7 acceptance incomplete.

## Frozen identity and review mode

- `review_mode`: `independent_static_source_review_with_one_authorized_focused_test`
- `reviewer_role`: `exact_target_independent_reviewer`
- E09 target: `d6ee96d923a91bf6db2e94eb109d970a238f8d68`
- Required direct parent: E08 `215d3c1acb6a3091a84f53cfdacb644d90116871` (verified)
- Reviewer branch/worktree: `agent/R12-E09-review` / `/home/zhiro/research/kv260-vlm-workers/R12-E09-review`
- Reviewer and builder worktrees were clean at review start; builder branch `agent/E09-runner-orchestration-regressions` is at the exact target and directly parents E08.
- R12 task brief SHA-256: `d8d550dea54a41c1b02864c1929cdcf47dae872dfa4f9379df9d25daa71368a2`
- R12 activation SHA-256: `af01a11caa806f9ca7dd746505287094b61f6252bc7b78fdeb0e3b04f175879d`
- R12 input manifest SHA-256: `b72c9597866b05afc70fd02281b739c4b7174f07389e236602732f4dc2fa8277`; all 11 entries passed verification from the reviewer worktree.
- E09 task brief SHA-256: `c0754682def64bf3ddad54df0d1acd660d7f5839e6adfdd22a627b69d028485c`
- E09 activation SHA-256: `e49addda9665e575b17409a8ac9810595c6f62dc17caf3019eba79fd26467e8d`
- E09 source manifest SHA-256: `eb17dec6cf5758a55e9fd6ddaec4e34748e4066175cc8864553ed07a4fb18488`
- E09 runner / parser / focused-test / builder-handoff SHA-256: `02d2c794c292bdb350803f9d028866e8b256e5846581e789b42928851f1a9cdf` / `0e28f81cc26ec47cfe2488c680623c74accd1bef92d9a4f3a31ae2fa73ba3b8d` / `6e91308f475e09bf4e84dafb8250d2ae27b3c30d2bc32243639e988667c78974` / `efb156ad765fabd83c4b0a6f911991fe6c949c45607aa1ad529c3c67335830db`
- E01 P2-7 runner-review / overall-review SHA-256: `8cafc732a0a9af26ca8da9e4097f1192b5b324661632904d93c27961621a6e3e` / `569712d404eb4cc2d18aa10759d37a2928cd1b03df2fcf493fc9ab4e0330ef1f`
- E09 target changed exactly four paths: `scripts/run_board_cpu_p2_textvqa.py`, `scripts/parse_board_textvqa_pilot.py`, `tests/test_p2_runner_orchestration.py`, and `orchestration/handoffs/E09_runner_orchestration_regressions_handoff.md`.

## Review results

### Production state machine and timeout/status/copy gates

`main()` constructs `HostOrchestrationOps` with its production callbacks and calls `run_host_orchestration()` (`scripts/run_board_cpu_p2_textvqa.py:1441-1458`). The tests import and invoke that same function with local fakes (`tests/test_p2_runner_orchestration.py:6-8, 110-131`); production SSH, rsync, worker, parser/scoring, and record callbacks are supplied at lines 1195-1451. The diff does not create a parallel test-only decision implementation.

The state machine launches the worker once and makes at most one status query; it contains no worker retry (`run_board_cpu_p2_textvqa.py:112-135`). Copy is reachable only after a zero-return status reply whose status is `COMPLETE`, run ID equals the current frozen run ID, run directory exists, lock is free, completion marker is valid, and CLI/unreadable-process lists are empty (`140-164`). The production status callback reads and preserves the bounded SSH reply; its remote probe validates the run ID, run directory, lock, process lists, completion/result records, marker schema/run ID, and file hashes (`948-991, 1343-1364`).

Transport exceptions, nonzero/malformed/incomplete status all take the `REMOTE_STATE_UNKNOWN` branch, with no copy or score and later qids recorded unresolved (`134-162`). Incomplete copy (timeout, nonzero, manifest error, or hash mismatch) returns unverified, records the failure phase, preserves whatever local files/transport output exist, skips scoring, and stops later qids (`164-175`; production copy callback `1366-1420`). The five focused test methods cover no retry and one status query, complete-current-run status gates, lock-busy behavior, eight status failure variants, four copy failures, and no-start ordered stop (`tests/test_p2_runner_orchestration.py:142-243`).

For the exact worker reply `{"status":"REMOTE_LOCK_BUSY","cli_started":false}`, the state machine records `RUNNER_LOCK_BUSY` for the current qid and unresolved non-starts for later qids without status, copy, or score (`run_board_cpu_p2_textvqa.py:117-123`). The embedded worker emits that exact JSON on lock acquisition failure at line 687. Production non-start callbacks write the parser's `kv260_cpu_p2_textvqa_execution_v1` result shape with `cli_started: false`, no prior run ID for `RUNNER_LOCK_BUSY`, and allowed timeout-identity fields (`1014-1048`); the parser enum accepts the reason and validates the non-start contract (`parse_board_textvqa_pilot.py:72-86, 109-121, 735-772`). The test verifies reason, qid, no start-evidence fields, no copy/status/score, and later records (`test_p2_runner_orchestration.py:159-174`). This path cannot set a CLI attempt or reach scoring.

### P2 finding: missing prior raw state bypasses ordered-stop records

**P2 — Prior assessment exceptions abort before writing current/later non-start records.** `run_host_orchestration()` invokes `ops.assess_previous(previous_qid)` without handling exceptions (`scripts/run_board_cpu_p2_textvqa.py:86-90`). The production callback directly calls `assess_previous()` (`1195-1198`), which raises `ValueError` when the previous raw directory is missing (`1005-1011`). There is no catch around the state-machine call in `main()` (`1453-1458`). Therefore, if a requested qid has a missing/unreadable prior raw record, the process exits before `begin`, preflight, staging, worker, status, copy, or scoring—which is fail-closed—but the ordered-stop path never writes the required parser-valid non-start records for the requested and later qids.

The test covers a previous assessment returning `False`, where the state machine records both non-starts and invokes no start-side callbacks (`tests/test_p2_runner_orchestration.py:227-243`); it does not cover the production callback raising for an absent prior raw directory.

**Consequence:** the request does not start, but its refusal and the remaining qid stop state are absent from the expected machine-readable records. The ordered-stop requirement in E09's task brief is not met for this unresolved-prior case.

**Bounded fix:** convert missing/unreadable prior evidence into a failed/unresolved assessment result caught by the production callback or state machine, then use the existing ordered-stop path to write current and later `PRIOR_CASE_FAILED` or `PRIOR_CASE_UNRESOLVED` non-start records. Add a focused test where `assess_previous` raises and assert those records are written while `begin`, preflight, stage, worker, status, copy, and score are not called.

### Preserved parser, scoring, and resource contracts

The parser change adds only `RUNNER_LOCK_BUSY` to the non-start reason enum; E08 resource timestamp ordering and strict non-start validation are otherwise unchanged (`parse_board_textvqa_pilot.py:109-121`; the E09 diff is limited to the enum addition). The runner keeps the existing failure scoring and denominator behavior because scoring remains behind verified copy and the existing adapter (`run_board_cpu_p2_textvqa.py:177-188, 1422-1439`; parser attempted/empty-score behavior at `parse_board_textvqa_pilot.py:784-810`). E08 point-in-time resource evidence, timeout identity, image parsing, argv/provenance, and other parser gates were not weakened in the reviewed diff.

### Independent test result

Ran exactly once, as authorized:

```text
python3 -m unittest discover -s tests -p test_p2_runner_orchestration.py
```

Result: **Ran 5 tests in 0.003s — OK.** This matches the E09 handoff's recorded 5-test result. No other tests, syntax checks, dry plans, or source/runtime execution were performed.

## Claim limits and disposition

This review covers static source behavior and one local fake-operation test module only. No board/SSH, runtime/inference/benchmark, answer/annotation/user data, reboot, bitstream, or GitHub activity was used. The tests establish orchestration decisions with injected fake operations, not live board or parser execution. P2-5 remains closed only at source-parser level; runtime parser success and external board gates remain unverified. P3 stays `NO_GO_NOW`.

**Disposition:** E09 does not receive exact-target R12 PASS until the missing-prior-record case is handled and reviewed. P2-7 host orchestration acceptance is not complete because a required ordered-stop non-start record path is missing.
