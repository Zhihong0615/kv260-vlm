# TASK R09 — Independent review of E06 point-in-time resource evidence

## Frozen review target

- E06 worker commit: `4403b5ffdc7c4a8f40fc0b4451aba451f87077c0`.
- Required direct parent: `25a156a3d1bfe3292a5f7078225753b8455532b0`.
- Builder branch/worktree: `agent/E06-point-in-time-resource-contract` / `/home/zhiro/research/kv260-vlm-workers/E06-point-in-time-resource-contract`.
- Reviewer branch/worktree: `agent/R09-E06-review` / `/home/zhiro/research/kv260-vlm-workers/R09-E06-review`, checked out at the exact E06 target.
- E06 brief SHA-256: `edb1dd03e6539f044704ae4e3431e40dbe6c2c82a32670661a974d3c294126c2`.
- E06 activation SHA-256: `cec916913840dc92bd91d33ac878cfaf18e46e24824cb927c6a7e10015fdfb26`.
- E06 four-entry input manifest SHA-256: `7858293b39e69f2cb0e3a9a5449646ef0f4c6502fee8dedec131ba613e1656c6`.
- E06 parser SHA-256: `92e7bf4edc797ca360aa9647fe54b5a21c224236ac123d2a9aa7ad3377f2641e`.
- E06 focused-test SHA-256: `ef7ae9b926385b3cb58c0202c09189f402ef80cf930981621272c5dde9ba05b9`.
- E06 handoff SHA-256: `018f7a3c408162ac7ed8d754c80bc421323ecca62a9073060ccbcc5596596bcc`.
- Review input manifest: `orchestration/evidence_snapshots/R09_E06_review/SOURCE.sha256`.

## Review tasks

1. Verify the exact E06 parent, clean worktree, three changed paths, output hashes, and frozen E06 input hashes. Confirm the one focused test command/result from the handoff without rerunning it.
2. Review `classify_resource_snapshot_evidence()` and all parser call paths. Confirm the output separates prelaunch and post-run statuses, exposes point-in-time-only scope, never implies an in-run monitor, and fails closed for unavailable or malformed required evidence.
3. Scrutinize the meaning of “well-formed”: compare the helper’s accepted snapshot structures with the fields later consumed by the parser. In particular, determine whether `resource_gates_verified` can be true when detailed resource fields are missing, malformed, or inconsistent with an empty `gate_reasons` list. Check the focused test fixtures against the claimed contract.
4. Confirm any post-run gate reason prevents `image_processing_verified`, while attempted-request denominator and the existing failed-attempt scoring rule (empty prediction, zero score) remain intact. Check the host rehearsal output says board resources were not sampled and does not claim board gate verification.
5. Check that unrelated command, image-integrity, timeout-identity, privacy, and completion validation paths were not weakened. Report any discrepancy between implementation and handoff claims.

## Boundaries and outputs

- Static review only. Do not run tests, syntax checks, dry plans, benchmarks, inference, answer/annotation reads, code, board/SSH actions, reboot, bitstream work, or GitHub activity.
- Add only `reviews/E06_point_in_time_resource_independent_review.md` and `orchestration/handoffs/R09_E06_review_handoff.md` on the reviewer branch.
- Report PASS/FAIL with P0/P1/P2 findings, exact target/output hashes, clean-tree evidence, and claim limits. Reviewer commit must directly parent the exact E06 target.
- Do not integrate before exact-target PASS. The review does not establish live board resources, runtime parser success, in-run safety, or board readiness. P2-7 and all other external gates remain open; P3 stays `NO_GO_NOW`.
