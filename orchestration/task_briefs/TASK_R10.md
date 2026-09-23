# TASK R10 — Independent review of strict snapshot validation

## Frozen review target

- E07 worker commit: `6a658012e0ae8269c4c69efff884042be52058d4`.
- Required direct parent: E06 target `4403b5ffdc7c4a8f40fc0b4451aba451f87077c0`.
- Builder branch/worktree: `agent/E07-strict-resource-snapshot-validation` / `/home/zhiro/research/kv260-vlm-workers/E07-strict-resource-snapshot-validation`.
- Reviewer branch/worktree: `agent/R10-E07-review` / `/home/zhiro/research/kv260-vlm-workers/R10-E07-review`, checked out at exact E07 target.
- E07 task brief SHA-256: `2f3b08a1c3c262bdeaae6417c9f23188fc009dc66f13a21ff277e49135c0c377`.
- E07 activation SHA-256: `e16dcf2664961b50a41d8f98c819dfb3be11f9c4354879ecc77266796c3f6dbf`.
- E07 fourteen-entry input manifest SHA-256: `d05f56e523e80598279ed3119ca0b1c6db1d4c0f28e4975cdfa88e20eb611fff`.
- E07 parser SHA-256: `325fee0fc07c6a9cbe03909e438b8761b81459ac057e93164b4dbf553acae87c`.
- E07 focused-test SHA-256: `dfd6c808c0fe1b7eaee66ad69e4e197aaf4300d3d1d86e1792e7a85078b2ed2b`.
- E07 handoff SHA-256: `a126ea655900b735608a3e92a3dfe0b6576a0ee60418032e6f72e8c585d2bf89`.
- R10 input manifest: `orchestration/evidence_snapshots/R10_E07_review/SOURCE.sha256`.

## Review tasks

1. Verify exact parent, clean worktree, three changed paths, E07 output hashes, and all frozen E07 inputs. Confirm the sole focused test command/result from the handoff without rerunning it.
2. Compare the classifier's accepted prelaunch/post-run structures with the frozen runner's embedded `rich_snapshot()` and the exact records written to `preflight_before.json` / `preflight_after.json`. Ensure it does not require fields present only in the separate host initial-preflight schema, and the test fixtures match the embedded worker output.
3. Recheck every R09 false-pass: NaN/Inf/negative load, missing post-run memory/vmstat/disk/load/process fields, malformed process rows, active package-upgrade service with empty gate reasons, and resource values inconsistent with empty reasons. Inspect status handling for missing/malformed containers and nonempty reasons.
4. Confirm command/pre/post timeout identities are cross-bound; pre/post timestamps bracket the recorded CLI interval before `resource_gates_verified` may be true; both snapshots must pass before combined image-processing verification can pass.
5. Confirm the attempted denominator, failed-attempt empty-prediction/zero-score rule, answer scoring, host-rehearsal scope, point-in-time-only claim, no-in-run-monitor statement, and unrelated parser gates remain intact. Report any gap between code, tests, and handoff.

## Boundaries and outputs

- Static source review only. Do not run tests, syntax checks, dry plans, benchmarks, inference, answer/annotation reads, code, SSH/board actions, reboot, bitstream work, or GitHub activity.
- Add only `reviews/E07_strict_resource_snapshot_independent_review.md` and `orchestration/handoffs/R10_E07_review_handoff.md` on the reviewer branch.
- Report PASS/FAIL with P0/P1/P2 findings, exact target/output hashes, clean-tree evidence, and claim limits. Reviewer commit must directly parent the exact E07 target.
- Do not integrate before exact-target PASS. The review does not establish live board resources, runtime parser success, request-long safety, or board readiness. P2-7 and all other external gates remain open; P3 stays `NO_GO_NOW`.
