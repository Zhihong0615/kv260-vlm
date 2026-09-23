# E06 point-in-time resource evidence handoff

## Build identity

- Base: `25a156a3d1bfe3292a5f7078225753b8455532b0`; the E06 target commit directly parents this base.
- Branch/worktree: `agent/E06-point-in-time-resource-contract` / `/home/zhiro/research/kv260-vlm-workers/E06-point-in-time-resource-contract`.
- Input manifest SHA-256: `7858293b39e69f2cb0e3a9a5449646ef0f4c6502fee8dedec131ba613e1656c6`; all four entries passed verification.
- Changed paths: `scripts/parse_board_textvqa_pilot.py`, `tests/test_p2_resource_snapshot_contract.py`, and this handoff only.

| Frozen input | SHA-256 |
|---|---|
| Parser before E06 | `c98da380900582c22cebba90134170c1dd0f81c0f853c8dc67e5c82c98981281` |
| Frozen pilot protocol | `4629db39f822dc8f0fd6f0ec619b1f36c1632406f035aca5860643c86567fce3` |
| Current P2 gate review | `569712d404eb4cc2d18aa10759d37a2928cd1b03df2fcf493fc9ab4e0330ef1f` |
| Authorized taskbook | `ad5e705e3a34510a28f1468ea619841e339b41a93a0c643821dbc80e53dc7b25` |

## Evidence contract

- The parser reports prelaunch and post-run snapshot status and reasons separately. Missing or malformed required fields, invalid UTC timestamps, or malformed containers classify as unavailable/malformed and fail closed. `resource_gates_verified` becomes true only after both point-in-time snapshots pass with empty reason lists and the existing detailed resource checks pass.
- Pilot output explicitly states `board_prelaunch_and_post_run_point_in_time_snapshots_only` and `in_run_resource_monitoring_performed: false`. A post-run gate reason makes `resource_gates_verified` and `image_processing_verified` false. The CLI start remains in the attempted denominator and the existing failed-attempt score rule remains unchanged (empty prediction, zero score).
- Host rehearsal has its own `host_rehearsal_direct_local_file_hashes_only; board resources not sampled` scope, marks board resource gates not applicable, and does not imply that board resources were measured.
- Passing the two snapshots does not establish conditions throughout the request; there is no in-run monitor or automatic abort threshold in this change. Any required continuous monitoring needs its own versioned design and review.

## Verification and output hashes

- Focused command: `python3 -m unittest discover -s tests -p test_p2_resource_snapshot_contract.py`
- Result: `Ran 5 tests ... OK` (both snapshots pass, prelaunch failure, post-run failure, malformed evidence, and separate host rehearsal scope).
- Parser SHA-256: `92e7bf4edc797ca360aa9647fe54b5a21c224236ac123d2a9aa7ad3377f2641e`.
- Focused test SHA-256: `ef7ae9b926385b3cb58c0202c09189f402ef80cf930981621272c5dde9ba05b9`.
- Exact target commit SHA and this handoff's SHA-256 are returned in the builder completion message because each cannot include its own hash in tracked content.

## Limits and remaining gates

This was parser/test work only. No board or SSH access, runtime inference, benchmark, broader suite, syntax check, dry plan, network action, or answer/annotation read was performed. The unit test classifies synthetic snapshot structures; it is not evidence of live board resources or runtime parser success. Independent exact-target R09 review is required before integration. P2-7 and other execution gates remain open; this change makes no board-readiness claim. P3 remains `NO_GO_NOW`.
