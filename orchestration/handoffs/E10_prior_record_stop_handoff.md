# E10 handoff — prior-record ordered stop

## Change

Based on E09 `d6ee96d923a91bf6db2e94eb109d970a238f8d68`, the production-used host orchestration now catches prior-assessment `OSError`, `ValueError`, `KeyError`, and `TypeError` as unresolved evidence. It records the requested and later qids through the existing ordered non-start path with `PRIOR_CASE_UNRESOLVED` and the preceding run ID, returns an explicit unresolved decision, and prints that decision from the CLI. The existing false-return path still records `PRIOR_CASE_FAILED`.

The focused fake verifies parser-shaped current/later non-start records and that no begin, preflight, stage, worker, status, copy, or score operation runs after an `OSError` assessment failure. Changes are limited to:

- `scripts/run_board_cpu_p2_textvqa.py` — SHA-256 `8f07232ef2bcfe78e3f5cd331273796de6db87402a8e502ca4980dc89682c577`
- `tests/test_p2_runner_orchestration.py` — SHA-256 `f6493c9e45696e7bd02305567159dcd8e70e910bd55b2e875376b262213bec56`
- `orchestration/handoffs/E10_prior_record_stop_handoff.md`

## Verification and limits

The frozen 15-entry E10 input manifest verified before editing. The only authorized test command, `python3 -m unittest discover -s tests -p test_p2_runner_orchestration.py`, ran once and reported **Ran 6 tests — OK**. The test ran immediately before the final change that narrowed the exception tuple; it is not rerun under the E10 exactly-once limit. No other tests, syntax checks, dry plans, or source execution were performed.

This is host-only fake-operation coverage. No board, SSH, network, runtime, inference, real data, or GitHub activity occurred. P2-7 remains subject to exact-target R13 PASS before integration; P2-5 remains closed only at source-parser level, with runtime parser success and external board gates unverified. P3 remains `NO_GO_NOW`.
