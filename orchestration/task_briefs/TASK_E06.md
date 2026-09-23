# TASK E06 — Make the CPU pilot's point-in-time resource evidence explicit

## Frozen source and decision

- Exact source base: `25a156a3d1bfe3292a5f7078225753b8455532b0` (E05/R08 integrated coordinator source).
- Builder branch/worktree: `agent/E06-point-in-time-resource-contract` / `/home/zhiro/research/kv260-vlm-workers/E06-point-in-time-resource-contract`.
- Four-entry input manifest: `orchestration/evidence_snapshots/E06_point_in_time_resource_contract/SOURCE.sha256`.
- The user-authorized taskbook requests automated tests and independent review (frozen taskbook SHA-256 `ad5e705e3a34510a28f1468ea619841e339b41a93a0c643821dbc80e53dc7b25`). The frozen pilot protocol already states it takes prelaunch and post-run snapshots, has no in-run monitor or automatic stop threshold, cannot promise resources stay safe throughout a request, and uses post-run deterioration to stop later requests. This task implements that point-in-time contract; it must not add or imply an in-run lease.

## Objective and acceptance

Resolve E01 P2-5 for the bounded CPU pilot by making its resource evidence scope explicit and fail-closed in derived results:

- The parser distinguishes the prelaunch gate result from the post-run gate result and declares that only point-in-time snapshots were observed; no in-run resource monitoring occurred.
- `resource_gates_verified` is true only when both required snapshots are well-formed and have empty gate-reason lists. A post-run gate reason makes this field false and therefore prevents `image_processing_verified` from being true, while preserving the attempted-request denominator and answer scoring semantics.
- Missing or malformed gate-reason containers fail closed. The host rehearsal path must state its own resource-evidence scope without claiming board resources were sampled.
- Add a focused unit test for the pure snapshot-evidence classification helper and run only that test. The test must cover both snapshots passing, postflight failure, preflight failure, and malformed evidence.
- Keep the protocol's explicit limit: passing pre/post snapshots do not prove that conditions remained within thresholds during the request. If an in-run abort is ever required, it needs a separate versioned monitor design and review.

## Scope and deliverables

- Modify only `scripts/parse_board_textvqa_pilot.py` and add `tests/test_p2_resource_snapshot_contract.py` plus `orchestration/handoffs/E06_point_in_time_resource_contract_handoff.md`.
- The handoff records exact base/target, direct-parent and clean-tree evidence, changed paths, input/output hashes, the point-in-time decision, test command/result, and remaining gates.
- Do not run dry plans, benchmarks, inference, answer/annotation reads, broader suites, code against the board, SSH/board actions, reboot, bitstream work, or GitHub activity. Do not modify the primary checkout or frozen snapshots.

## Independent review gate

Queue exact-target independent R09 after the builder commit. Integrate only after PASS. This change classifies evidence; it does not prevent a transient workload from starting and ending between snapshots, establish runtime parser success, or establish board readiness. P2-7 and all other external gates remain open; P3 stays `NO_GO_NOW`.
