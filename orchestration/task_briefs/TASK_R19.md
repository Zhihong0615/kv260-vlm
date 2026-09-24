# TASK R19 — Independent review of E13 remote process-scan hardening

## Frozen target

- Exact E13 runner/test target and required direct parent: recorded in `orchestration/activations/R19.md` after E13 delivery.
- Review both production remote process scans, the focused synthetic test, E13 handoff, and the preserved R16 audit report.
- Required fixed runner output: `reviews/board_cpu_p2_textvqa_runner_independent_review.md`.
- Preserve `reviews/audit/R16_runner_PASS_WITH_P2_FINDINGS_20260924.md` unchanged.

## Objective and acceptance

1. Verify exact E13 parent, clean worktree, manifest and source/test hashes before review.
2. Independently confirm that permission and non-permission `OSError` values cannot be treated as absence, `FileNotFoundError` disappearance is handled as specified, cleanup verification remains false under unknown visibility, remote status cannot report `COMPLETE` on incomplete scans, and ordinary empty/found-process behavior is preserved. Confirm production defaults remain `/proc` and the board base path.
3. Review source and run only `python3 -m unittest discover -s tests -p test_p2_remote_process_scan_errors.py` once. No other tests, imports, parser/runner execution, dry plan, board/SSH/network/runtime/inference/benchmark/reboot/bitstream, or user-data inspection.
4. Write a fresh report at the fixed runner review path binding exact E13 runner SHA and exact parser context SHA. Include independent-static metadata, explicit P0/P1/P2 counts, test command/output, findings and limitations. Add exact-SHA handoff; commit only the fixed report and handoff, leaving a clean tree.

## Boundaries

Do not address owner-window reuse or durable later non-start conflicts. Preserve the R16 audit record. No live board cleanup, resource, owner-window, runtime, or readiness claim.
