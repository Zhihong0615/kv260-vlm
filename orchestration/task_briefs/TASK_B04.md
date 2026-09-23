# TASK B04 — Static per-op key coverage of selected VLM traces

## Objective

Quantify how much of the observed shape variation in the four selected B03 traces is represented by the strongest static per-op signature `(op, input/output dtype, ne, nb)`. Compare that control with deliberately coarser GEMM-only and shape-only keys, and determine whether media-group identity adds any information about the *observed operator signatures*.

This is an offline trace analysis only. It does not measure backend eligibility, placement, latency, bandwidth, resource pressure, or a K26 advantage. Do not promote a hypothesis or novelty claim from key coverage.

## Frozen inputs and activation gate

- Source commit: B03 worker commit `4d7ce5e5fa5e750833cb5a05b8b3a15364861134`.
- B03 input manifests and trace limitations are recorded in `orchestration/handoffs/B03_selected_qid_optrace_handoff.md` at that commit.
- This task's source hashes are listed in `orchestration/evidence_snapshots/B04_static_key_coverage/SOURCE.sha256`.
- **Do not activate B04 until R02 independently passes B03's exact-SHA integrity and interpretation review.** If R02 fails, revise the B03 source first and regenerate this task's exact source manifest from the reviewed replacement commit.

## Procedure

1. Create a dedicated clean worker branch/worktree based exactly on the frozen B03 commit after the activation gate passes. Keep the primary checkout read-only.
2. Verify every entry in the B04 `SOURCE.sha256` before analysis and again before commit. Stop on any mismatch.
3. Parse only the four compressed graph traces and existing B03 metadata summaries. Do not run inference or open prompt, answer, annotation, image, model, or board files.
4. For each vision node, construct a canonical full static key from op, each input's dtype/dimensions/strides, and output dtype/dimensions/strides. Exclude pointer IDs, names, request IDs, media-group ordinals, and storage addresses from the key. Also calculate clearly labeled coarse-key inventories (op plus GEMM M/N/K where applicable; op plus output shape) to show which information those keys discard.
5. Report raw node-record coverage, unique keys per group, cross-group key-set equivalence classes, cross-request reuse, and where the coarse keys merge full-key-distinct observations. Any collision is only a metadata collision statement, not an accelerator cost or placement failure.
6. State explicitly that the graph callback runs after backend splitting; this analysis cannot validate `supports_op` eligibility or final K26 placement. State that group ordinals are encoded media-batch ordinals, not crop identities.

## Stop conditions and boundaries

- No source/runtime edits, inference, answer/annotation inspection, tests, board SSH, board inference, reboot, bitstream build/load, or remote GitHub actions.
- Do not alter `status/go_no_go.md`, the global novelty verdict, or P3 `NO_GO_NOW`.
- Keep outputs compact; do not duplicate the raw traces.

## Deliverables

- `scripts/analyze_static_key_coverage_B04.py`
- `experiments/derived/static_key_coverage_B04.json`
- `experiments/derived/static_key_coverage_B04.md`
- `orchestration/handoffs/B04_static_key_coverage_handoff.md` with exact source, tool and output hashes; deterministic counts; interpretation limits; and a recommendation to retain, weaken, or reject the associated measurement question.
- One commit on `agent/B04-static-key-coverage`, whose parent is the exact frozen B03 commit, with a clean worktree.

