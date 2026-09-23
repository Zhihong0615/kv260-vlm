# TASK B05 — Ordered VLM media-group trace null audit

## Research question

B04 found that the full per-op signature key represents the observed signature sets in all 24 media groups, so group ordinal adds no new *set membership* information in these four selected requests. It did not test whether the ordered operator-signature sequence contains group-specific context beyond those sets. Audit that narrower question before spending effort on a group-aware selector or sequence-sensitive measurement plan.

## Frozen inputs

- Exact SHA-256 inputs are listed in `orchestration/evidence_snapshots/B05_ordered_group_trace_audit/SOURCE.sha256`.
- Inputs are limited to the four B03 compressed traces, B03 derived metadata summaries, and B04 analyzer/results/handoffs.
- Read only `vision_encoder` node records and `media_batch` boundaries in the traces. Do not inspect prompts, images, model files, answer text, annotations, or run-manifest case contents.
- Verify every manifest hash before and after analysis. Treat all trace files as immutable.

## Required analysis

1. Reconstruct B04's full per-node key exactly: op plus ordered input/output dtype, `ne`, and `nb`; exclude names, ids, addresses, group/request identity, and storage metadata.
2. Preserve trace order inside each request and media group. Compare each group's ordered full-key sequence, key multiset/set, and adjacent-key transition counts. Report which distinctions are already visible from node keys or B04's group-set result.
3. Identify any pair of groups with the same full-key set but different ordered sequences, and any sequence distinctions that disappear after canonicalization. State the finite four-request scope and avoid treating media-batch ordinals as crop identities.
4. Compare against the strongest static null supported by these traces: per-op full-key dispatch plus a static ordered-sequence/replay table. Explain whether any observed sequence feature would force a dynamic selector, or whether it only motivates timing tests against that static plan.

## Deliverables

- A compact deterministic analyzer under `scripts/` and report under `experiments/derived/`.
- `orchestration/handoffs/B05_ordered_group_trace_audit_handoff.md` with source and output hashes, exact worker start/target SHAs, results, limits, and an explicit recommendation (stop, or define a separately gated timing experiment).
- One clean commit on `agent/B05-ordered-group-trace-audit`, direct parent equal to the exact frozen base in `orchestration/activations/B05.md`.

## Boundaries

- Offline analysis only. No host inference, board access, SSH, tests, syntax checks, benchmarks, source/runtime changes, or GitHub actions.
- Do not claim a K26 cost, allocation/liveness effect, resource-pressure interval, backend placement, bandwidth, novelty, or performance result.
- Preserve the B04 conclusion and P3 `NO_GO_NOW`. This task can reject an unnecessary sequence hypothesis or prioritize a future measurement; it cannot select a method.
