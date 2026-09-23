# TASK E08 — Enforce complete CLI interval bracketing

## Frozen target

- E07 target: `6a658012e0ae8269c4c69efff884042be52058d4`.
- Required direct parent: exact E07 target above.
- Builder branch/worktree: `agent/E08-resource-timestamp-ordering` / `/home/zhiro/research/kv260-vlm-workers/E08-resource-timestamp-ordering`.
- R10 reviewer commit: `dd54d749992e54cbb1c092d9d1ba755f1fe3a492`, direct parent E07, verdict FAIL P0=0/P1=1/P2=0.
- R10 report SHA-256 `14bbe508dc1ce869fcf659dcd1c72222aecf17cc3a70a33e68455d2676d2736c`; handoff SHA-256 `9f1bbebb6df2680e6bf19c72c6dfdb52875a40981366b453d63039f57dca1e3a`.
- Frozen source manifest: `orchestration/evidence_snapshots/E08_resource_timestamp_ordering/SOURCE.sha256`.

## Objective and bounded scope

Fix only R10 P1: in pilot parsing, a reversed recorded CLI interval can pass because the code checks `pre_stamp <= started_at` and `post_stamp >= ended_at` without requiring `started_at <= ended_at`. The complete required ordering is `pre_stamp <= started_at <= ended_at <= post_stamp` before `resource_gates_verified` can be true.

1. Verify exact parent, clean worktree, frozen source manifest, and exact allowed paths before editing.
2. Add or factor a small deterministic timestamp-ordering predicate that the pilot parser actually calls before restoring `resource_gates_verified` to true. It must reject reversed intervals and a post snapshot that predates CLI start, even when it is later than the reversed CLI end.
3. Add focused unit cases for valid full ordering, `started_at > ended_at`, and post snapshot before start with otherwise passing resource evidence. Preserve malformed-time rejection and existing content gates.
4. Change only `scripts/parse_board_textvqa_pilot.py`, `tests/test_p2_resource_snapshot_contract.py`, and `orchestration/handoffs/E08_resource_timestamp_ordering_handoff.md`.
5. Run exactly once, and only once, this focused module command: `python3 -m unittest discover -s tests -p test_p2_resource_snapshot_contract.py`. Record the actual result; do not run a broader suite, syntax check, or dry plan.
6. Commit with direct parent E07 target and a clean worktree. Report commit, changed paths, and output SHA-256 values.
7. After E08 delivery, independent R11 may run the same exact focused module command once on the frozen E08 target as its only execution; all other review remains static.

## Boundaries

- Host-only source and focused test work. No SSH, board reads, reboot, inference, benchmark, runtime, bitstream, answer/annotation reads, or GitHub activity.
- Neither builder nor reviewer may run a broader suite, syntax check, or dry plan.
- Do not weaken or reclassify E07's snapshot schema/content checks, timeout identity, attempted denominator, failure scoring, host rehearsal scope, point-in-time-only claim, or unrelated parser gates. Do not add an in-run monitor.
- E07 remains unintegrated after R10 FAIL. Require exact-target independent R11 review of the E08 result before integration. P2-7 cross-phase runner orchestration coverage and external execution gates remain open; P3 stays `NO_GO_NOW`.
