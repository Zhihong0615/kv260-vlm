# R12 handoff — E09 host runner orchestration review

## Verdict

**FAIL — P0: 0, P1: 0, P2: 1.** Production `main()` uses the tested `run_host_orchestration()` state machine; worker timeout/status/copy/score ordering and exact lock-busy behavior pass static review and the focused tests. A missing prior raw directory makes the production prior-assessment callback raise before the ordered-stop state machine can write non-start records for the requested and later qids. The exact finding and bounded fix are in `reviews/E09_runner_orchestration_independent_review.md`.

## Exact identities

- Reviewed E09 target: `d6ee96d923a91bf6db2e94eb109d970a238f8d68`
- Required direct parent: E08 `215d3c1acb6a3091a84f53cfdacb644d90116871` (verified)
- Reviewer branch/worktree: `agent/R12-E09-review` / `/home/zhiro/research/kv260-vlm-workers/R12-E09-review`
- Builder branch/worktree: `agent/E09-runner-orchestration-regressions` / `/home/zhiro/research/kv260-vlm-workers/E09-runner-orchestration-regressions`, clean at exact target and directly parented by E08.
- R12 brief / activation / input manifest SHA-256: `d8d550dea54a41c1b02864c1929cdcf47dae872dfa4f9379df9d25daa71368a2` / `af01a11caa806f9ca7dd746505287094b61f6252bc7b78fdeb0e3b04f175879d` / `b72c9597866b05afc70fd02281b739c4b7174f07389e236602732f4dc2fa8277` (11/11 entries verified)
- E09 brief / activation / source manifest SHA-256: `c0754682def64bf3ddad54df0d1acd660d7f5839e6adfdd22a627b69d028485c` / `e49addda9665e575b17409a8ac9810595c6f62dc17caf3019eba79fd26467e8d` / `eb17dec6cf5758a55e9fd6ddaec4e34748e4066175cc8864553ed07a4fb18488`
- E09 runner / parser / focused test / builder handoff SHA-256: `02d2c794c292bdb350803f9d028866e8b256e5846581e789b42928851f1a9cdf` / `0e28f81cc26ec47cfe2488c680623c74accd1bef92d9a4f3a31ae2fa73ba3b8d` / `6e91308f475e09bf4e84dafb8250d2ae27b3c30d2bc32243639e988667c78974` / `efb156ad765fabd83c4b0a6f911991fe6c949c45607aa1ad529c3c67335830db`
- E09 changed paths are exactly the runner, parser, focused test, and builder handoff.

## Verification and limits

Ran exactly once: `python3 -m unittest discover -s tests -p test_p2_runner_orchestration.py`; result **5 tests, OK**. No other tests or execution were performed. The review commit directly parents the exact E09 target and adds only this handoff and the R12 report. Commit SHA, deliverable hashes, and final clean-tree status are returned with the completion report.

The review is limited to static source behavior and local fake-operation tests. It does not establish live board/parser behavior or external readiness. No board/SSH, runtime/inference, answer/annotation/user data, or GitHub activity was used. P2-5 remains closed only at source-parser level; runtime parser success and external gates remain unverified. P3 remains `NO_GO_NOW`. The FAIL disposition does not change global go/no-go.
