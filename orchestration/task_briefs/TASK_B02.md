# Task ID

B02 — Selected Host Visual-Pattern Evidence Audit

## Role

Workload evidence analyst. Reconcile the four frozen development-request records and state exactly which runtime/shape facts they establish.

## Frozen input target

Snapshot commit: `548d6229d9fbff67db5103933d9c837259d6b4f4` — selected host records, derived workload inventory, and existing shape/selector notes.

Evidence directory: `orchestration/evidence_snapshots/B02_workload_pattern_audit/`. At activation, verify branch/base/clean state and run `sha256sum -c SOURCE.sha256` from this directory. Stop if any check fails.

Selected development requests:

- qid 35950 — logged pattern `[60,60,60,60,60]`
- qid 34609 — logged pattern `[63,63,63,63,63]`
- qid 35419 — logged pattern `[63,63,63,63,63,63,63]`; it also has a selected host phase timeline
- qid 35005 — logged pattern `[64,70,70,70,70,70,70]`

## Questions

1. Do the exact request commands and logs agree with the inventory for qid, image identity/hash/dimensions, runtime arguments, return status, and ordered `n_tokens_batch` sequence?
2. What do the logs actually show about repeated MTMD encode/decode groups (`n_chunks`, `done/total`, event order, per-event host durations)? What do they not show about crop identity, independent hardware jobs, physical memory traffic, or PL scheduling?
3. Which of these qids have an existing graph/op-shape trace, allocator trace, or only an outer phase timeline? Reconcile against the frozen shape notes and name the evidence boundary.
4. At what point is each observed field available? Distinguish post-processor log fields from graph dimensions visible at backend eligibility. Evaluate the strongest static control available from the frozen evidence.
5. Give the smallest next measurement that could falsify a future shape/group-dependent hypothesis, including fields needed to prove request identity, dispatch-time availability, full-request cost, and static-control parity. This is a proposal only; do not collect new data.

## Requirements and limits

- Use only the frozen snapshot. Do not read the primary checkout, raw files outside this snapshot, chat histories, or network sources.
- Keep host measured, host runtime-source, and analytical evidence distinct. Do not infer KV260 latency, crop traffic, physical occupancy, PS–PL overhead, or performance from these logs.
- Do not promote or rename a research contribution. R01's FAIL remains in force; this task only clarifies the available workload evidence.
- Do not run tests, inference, scripts, benchmarks, syntax checks, SSH, or board commands. Do not inspect or disclose answer labels. Do not modify source evidence or global status.
- A task-local markdown report and compact handoff are the only deliverables.

## Deliverables

1. `experiments/derived/selected_host_pattern_audit_B02.md` — one concise table across the four qids, source hashes, trace coverage, measured facts, and missing evidence.
2. `orchestration/handoffs/B02_workload_pattern_audit_handoff.md` — exact input/worker SHAs, conclusion, boundary, and smallest next measurement.

Commit both on the activated worker branch. Leave the worktree clean and report the final HEAD. This audit is not an independent review or a hardware gate.
