# E08 resource timestamp ordering handoff

## Build identity

- Base and required direct parent: E07 target `6a658012e0ae8269c4c69efff884042be52058d4`.
- Branch/worktree: `agent/E08-resource-timestamp-ordering` / `/home/zhiro/research/kv260-vlm-workers/E08-resource-timestamp-ordering`.
- E08 source manifest SHA-256: `4432b4293de9e74b6fc965e05cd1eb1302c9597a921f2befcc19f4e185b53d9e`; all 18 frozen inputs passed before edits.
- R10 review commit: `dd54d749992e54cbb1c092d9d1ba755f1fe3a492` (FAIL, P0=0/P1=1/P2=0); report SHA-256 `14bbe508dc1ce869fcf659dcd1c72222aecf17cc3a70a33e68455d2676d2736c`; handoff SHA-256 `9f1bbebb6df2680e6bf19c72c6dfdb52875a40981366b453d63039f57dca1e3a`.
- Changed paths: `scripts/parse_board_textvqa_pilot.py`, `tests/test_p2_resource_snapshot_contract.py`, and this handoff only.
- The target commit directly parents the exact base above. The final commit ID and handoff's own SHA-256 are reported in the builder completion message because they cannot be embedded in their own tracked content.

## Interval contract

- Added a deterministic ordering predicate for `pre_stamp <= started_at <= ended_at <= post_stamp`. Pilot parsing calls it before restoring `resource_gates_verified`; invalid order raises the existing parser failure path and the final gate helper also returns false.
- Added regressions with otherwise passing pre/post resource evidence for valid ordering, `started_at > ended_at`, and the reversed case where the post snapshot is after the recorded end but before the recorded start. Existing malformed-time handling and E07 snapshot-content checks remain unchanged.
- Snapshot evidence remains point-in-time only. No in-run monitor, content-gate change, timeout-identity change, scoring change, or rehearsal-scope change was made.

## Verification and output hashes

- Focused command, run once: `python3 -m unittest discover -s tests -p test_p2_resource_snapshot_contract.py`
- Result: `Ran 14 tests ... OK`.
- Parser SHA-256: `d31ef5a1df63ec1f0cd5a3c19c2a5f5ec34ea76b1d64ecb7be3aa8c0c5d4de45`.
- Focused test SHA-256: `f4d55864f704fe1ffb39b097b1adb87209b94c6895f2acf34dcbe874b92fd751`.
- Handoff SHA-256: reported in the builder completion message.

## Limits and remaining gates

This is host-only parser and focused-test work. No other test, syntax check, dry plan, runtime, SSH, board read, inference, benchmark, answer/annotation read, reboot, bitstream, or GitHub action was performed. Independent exact-target R11 review is required before integration. P2-7 and external execution gates remain open; P3 stays `NO_GO_NOW`.
