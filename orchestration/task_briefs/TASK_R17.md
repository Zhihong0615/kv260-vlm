# TASK R17 — Independent review of E12 parser contract remediation

## Frozen target

- Exact E12 parser/test target and required direct parent: recorded in `orchestration/activations/R17.md` after E12 delivery.
- Review the changed parser, focused synthetic test, E12 handoff, original R14 report/archive, and unchanged runner context.
- Required fixed parser review output: `reviews/kv260_cpu_p2_textvqa_output_contract_v2_independent_review.md`.
- Preserve `reviews/audit/R14_adapter_PASS_WITH_P2_FINDINGS_20260924.md` unchanged.

## Objective and acceptance

1. Verify the exact E12 parent, clean worktree, task manifest, and source/test hashes before review.
2. Independently assess that non-boolean values under `answer_parse_ok` are rejected by raw JSON scanning; true JSON integer QIDs are accepted while floats and booleans are rejected at every parser QID comparison and manifest selection; and the regression test exercises the actual production helpers without answer/annotation data.
3. Source review plus one independent run of only `python3 -m unittest discover -s tests -p test_p2_parser_label_qid_contract.py`. This is the sole execution permitted in the Reviewer worktree. No parser/runner execution, imports, other tests, dry plan, board, SSH, runtime, inference, benchmark, reboot, bitstream, network, or answer/annotation inspection.
4. Write a fresh report to the fixed parser review path binding the exact E12 parser SHA. Include `review_mode: independent_static`, `reviewer_role: independent_reviewer`, exact runner context SHA, explicit P0/P1/P2 counts, test command/output, findings, and limitations. A P0/P1-free verdict is required for the parser review gate. Add an exact-SHA handoff and commit only the report and handoff, leaving the worktree clean.

## Boundaries

Do not alter the runner review path or its report. Preserve R14's previous P2 report unchanged in the audit archive. No board readiness, runtime parser, output authenticity, or owner-window claim.
