# TASK R05 — Independent review of B05 ordered media-group trace audit

## Frozen review target

- B05 worker commit: `dbaf1372342b7535b33200a49a3711269d28fa07`.
- Required direct parent: `f7ad31d98ba96846c2a7522f114f6e310f63b19b`.
- Target branch/worktree: `agent/B05-ordered-group-trace-audit` / `/home/zhiro/research/kv260-vlm-workers/B05-ordered-group-trace-audit`.
- The exact review manifest and activation are in the coordinator worktree. The B05 activation SHA-256 is `0f2abb9ffd942065f7e4041c79328afd66562d0b34b3bb1c5eb6ebd80db2879a`.

## Review tasks

1. Verify the exact B05 parent, clean target worktree, and only the declared analyzer/JSON/report/handoff outputs.
2. Verify all eleven B05 frozen source hashes and all four worker output hashes from the review manifest.
3. Independently recompute from the four compressed traces the 24 media-group boundaries, vision-node counts, B04 full-key sets, multiplicity-preserving multisets, ordered sequences, and adjacent-transition profiles. Confirm group classes, all B04 set fingerprints, and both reported empty pair sets (same-set/different-sequence; same-multiset/different-sequence).
4. Check the analyzer’s canonical key against B04; assess that the report does not infer backend selection, runtime selector visibility, crop identity, cost, allocation/liveness, traffic, resource pressure, novelty, or performance.
5. Assess the recommendation to stop pursuing a group-aware selector from these four traces and preserve the requirement for a separately gated measurement against the static key plus ordered-sequence/replay null if timing becomes a question.

## Boundaries and output

- Offline trace reading and independent recomputation only. No tests, syntax checks, benchmarks, answer/annotation reads, host inference, board access, SSH, reboot, bitstream work, or GitHub activity. Do not run the submitted analyzer because it writes the reviewed output artifacts.
- Add only `reviews/B05_ordered_group_trace_independent_review.md` and `orchestration/handoffs/R05_B05_review_handoff.md` on the reviewer branch.
- Report PASS/FAIL with P0/P1/P2 findings, exact target/output hashes, and claim limits. Reviewer commit must directly parent the exact B05 target and leave a clean worktree.
- This is a static workload-information audit only; it cannot change P3 `NO_GO_NOW` or establish a method claim.
