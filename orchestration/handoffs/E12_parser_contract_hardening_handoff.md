# E12 Handoff — Parser Label and QID Contract Hardening

## Delivery

- Frozen target/direct parent: `ada49814f53f3c16b3e36383dcee65cb93473118`.
- The worker commit is directly on the frozen target; its full SHA is returned with this handoff.
- Changes are limited to the parser, one focused synthetic regression module, and this handoff.
- The original R14 report remains unchanged at `reviews/audit/R14_adapter_PASS_WITH_P2_FINDINGS_20260924.md`.

## Changes

- `scripts/parse_board_textvqa_pilot.py`: `answer_parse_ok` is exempt from label-key matching only when its value is a JSON boolean; nested label-key scanning remains recursive. Added `qid_matches`, which accepts only integer values excluding booleans, and used it at every JSON `question_id` comparison and when selecting manifest samples for pilot QIDs.
- `tests/test_p2_parser_label_qid_contract.py`: extracts and executes the production `has_label_keys` and `qid_matches` definitions; covers boolean and non-boolean metadata values, recursive nested label keys, integer/float/boolean QIDs, and an AST source-contract check for JSON `question_id` access.
- `orchestration/handoffs/E12_parser_contract_hardening_handoff.md`: this delivery record.

## Authorized test invocation

The one authorized invocation was:

```text
python3 -m unittest discover -s tests -p test_p2_parser_label_qid_contract.py
```

Exact output:

```text
......
----------------------------------------------------------------------
Ran 6 tests in 0.010s

OK
```

No correction or second test run was needed.

## File hashes

- Parser: `48c834d6b803eb6a06f4be39f287913c461701ec606956c66493fe7f10d7e209`
- Focused test: `a7ef837fc5a16129ce3fbe6d377ad5360b0a0d38423879c489ba275c014b9a23`
- This handoff's SHA-256 is returned after the file is finalized; it is kept outside this file to avoid a self-referential checksum.

## Evidence limits and next gate

This is source-level remediation with synthetic in-memory tests only. No manifest answer content, raw-run data, parser invocation, runner invocation, board, SSH, runtime, inference, or benchmark was accessed. The R14 findings should be considered closed only if exact-target R17 independently reports P0=0 and P1=0. No real artifact validation or board readiness is claimed; P3 remains `NO_GO_NOW`.
