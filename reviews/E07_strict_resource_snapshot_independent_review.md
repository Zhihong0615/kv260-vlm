# R10 — E07 strict resource snapshot independent review

## Verdict

**FAIL — P0: 0, P1: 1, P2: 0.** E07 closes the R09 resource-content false-pass paths, but its CLI-interval timestamp check still permits an inverted interval and can accept a post-run snapshot taken before CLI start. Therefore the R10 requirement that pre/post snapshots bracket the recorded CLI interval is not fully satisfied. The finding below is the only issue identified in scope.

## Frozen identity and review mode

- `review_mode`: `independent_static_source_review`
- `reviewer_role`: `exact_target_independent_reviewer`
- E07 target: `6a658012e0ae8269c4c69efff884042be52058d4`
- Required direct parent: E06 `4403b5ffdc7c4a8f40fc0b4451aba451f87077c0` (verified)
- Reviewer branch/worktree: `agent/R10-E07-review` / `/home/zhiro/research/kv260-vlm-workers/R10-E07-review`
- At review start: exact target HEAD and clean worktree verified.
- R10 task brief SHA-256: `277d836b70b8dd4ff138fa87010dbf2b8be0aa412009cc91ab0e0af10c36819a`
- R10 activation SHA-256: `518cf686811e6d2bb3d9d83615dd8ab82f0cb1be1ace0b71700467ba10d23670`
- R10 input manifest SHA-256: `e02e5038288d405e3eeb3b5e12581f86785a7ad4c5cfd0f8f15a28624acf960b`; all 21 entries passed verification from the target worktree.
- E07 brief SHA-256: `2f3b08a1c3c262bdeaae6417c9f23188fc009dc66f13a21ff277e49135c0c377`
- E07 activation SHA-256: `e16dcf2664961b50a41d8f98c819dfb3be11f9c4354879ecc77266796c3f6dbf`
- E07 input manifest SHA-256: `d05f56e523e80598279ed3119ca0b1c6db1d4c0f28e4975cdfa88e20eb611fff`
- E07 target parser SHA-256: `325fee0fc07c6a9cbe03909e438b8761b81459ac057e93164b4dbf553acae87c`
- E07 target focused-test SHA-256: `dfd6c808c0fe1b7eaee66ad69e4e197aaf4300d3d1d86e1792e7a85078b2ed2b`
- E07 target handoff SHA-256: `a126ea655900b735608a3e92a3dfe0b6576a0ee60418032e6f72e8c585d2bf89`
- Frozen embedded runner SHA-256: `cf0577bac5bc39eb42e43289eead86febeb30e6012adf0254860f3e24437d1fc`
- E07 target changed paths are exactly the parser, focused test, and E07 handoff listed above.

## Review results

The classifier at `scripts/parse_board_textvqa_pilot.py:204-393` validates the embedded worker's `rich_snapshot()` shape and semantic gate values. The required fields and exact scope at lines 219-228 match the frozen embedded worker at `scripts/run_board_cpu_p2_textvqa.py:450-478`; `rich_snapshot()` adds `gate_reasons` at lines 518-522, and the runner writes these objects as `preflight_before.json` and `preflight_after.json` at lines 634 and 665. This is distinct from host preflight evidence. The fixture in `tests/test_p2_resource_snapshot_contract.py:14-52` matches the embedded-worker schema and scope.

The reviewed classifier rejects non-finite and negative load values, missing measurement fields, malformed selected-process rows, and malformed nested service or PackageKit records. It independently derives semantic issues even when `gate_reasons` is empty, returning `INCONSISTENT`; nonempty gate reasons return `FAIL` (`parse_board_textvqa_pilot.py:248-288, 313-393`). This addresses the R09 false-pass cases for empty-but-contradictory process, service, and memory data. Focused tests cover those categories at `tests/test_p2_resource_snapshot_contract.py:86-156`.

Timeout identity is validated against the command and each snapshot, and the two snapshots are compared (`parse_board_textvqa_pilot.py:290-297, 395-424`; command/result provenance is checked at lines 824-828 and 903-910). The pilot path initializes the combined resource flag false, requires valid snapshot statuses and a passing prelaunch status, and only restores the flag from the helper result after subsequent checks (`913-923, 987`). `image_processing_verified` requires that flag to be exactly true in pilot mode (`1028-1035`). Rehearsal remains explicitly host-only and reports board resource gates as not applicable (`176-191`).

Attempt state remains tied to `cli_started` (`689-720`); once a CLI start is recorded, failures receive an empty prediction and zero score (`764-772, 1050-1053`). Parseable answers use the pinned evaluator, and the aggregate attempted denominator is retained (`1042-1049, 1118-1142`). The reviewed diff does not alter the unrelated argv, artifact/input identity, raw-hash, completion, marker, privacy, or image-event checks.

The E07 handoff reports the focused command `python3 -m unittest discover -s tests -p test_p2_resource_snapshot_contract.py` with 11 passing tests. This review confirmed that claim from the frozen handoff only; **the command was not rerun**.

## P1 finding

**P1 — Inverted CLI timestamps can pass the snapshot-bracketing gate.** At `scripts/parse_board_textvqa_pilot.py:925-935`, the parser parses `started_at` and `ended_at` but only rejects `pre_stamp > started_at` or `post_stamp < ended_at`. It never requires `started_at <= ended_at`. For example, if the recorded start is 10:00, end is 09:59, pre snapshot is 09:59:30, and post snapshot is 09:59:30, both current comparisons pass even though the post snapshot predates CLI start. With otherwise passing snapshots, the code later sets `resource_gates_verified` from the classifier at line 987, so the temporal evidence can be reported as verified without a post-run observation after the CLI interval.

**Consequence:** malformed or wall-clock-discontinuous execution timestamps can make the point-in-time resource gate appear to bracket the CLI when it does not. This violates the explicit R10 timestamp requirement and weakens the evidence tied to pilot image processing.

**Bounded fix:** require `started_at <= ended_at` and validate the complete ordering `pre_stamp <= started_at <= ended_at <= post_stamp` before setting `resource_gates_verified` true. Add focused cases for an inverted interval and a post snapshot before start; do not weaken the existing snapshot-content checks.

## Claim limits and disposition

This is a static review of the frozen source and documentation only. No code, tests, syntax checks, dry plans, board/SSH action, inference, answer/annotation data, or GitHub activity was used. The focused test result above is only the builder's recorded claim. No live board state, runtime parser success, request-long resource safety, or board readiness is established. Point-in-time snapshots still do not provide in-run monitoring; P2-7 and other external gates remain open, and P3 remains `NO_GO_NOW`.

**Disposition:** E07 does not receive exact-target PASS until the timestamp ordering gap is fixed and independently reviewed.
