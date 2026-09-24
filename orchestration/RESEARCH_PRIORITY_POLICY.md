# Research-first scheduling policy

Effective: 2026-09-24, by user direction.

## Objective

Find a defensible FPGA–VLM contribution grounded in MiniCPM-V behavior and KV260 constraints. Treat the current runner/parser infrastructure as sufficient for research unless a defect can damage the board, prevent an experiment, produce an incorrect result, or distort evidence.

## Task admission question

Before starting work, ask: **Will this result change the paper idea, hardware architecture, experimental conclusion, or P3 go/no-go?**

- If yes, prioritize it and state the decision it can change.
- If no, defer it or minimize it.
- Immediately address only issues that can damage the board, block an experiment, make results incorrect, or invalidate evidence.

## Time and review allocation

- At least 70% of active agent effort goes to primary-paper analysis, MiniCPM-V workload/bottleneck investigation, falsifiable architecture hypotheses, strong baselines, and decision-relevant profiling.
- Independent reviews are batched at research milestones. Do not create Builder→Reviewer→repair→Reviewer chains for small P2/P3 changes.
- Any future engineering review is proportional to risk and is triggered immediately only by the four critical conditions above.

## Engineering backlog (deferred)

These items remain visible but are not the next tasks. Reassess each only when it is on the critical path of a concrete, authorized experiment or when it meets an immediate-fix condition.

| Item | Current classification | Revisit trigger |
|---|---|---|
| R16 P2-2: owner-window reuse across runner invocations | Defer; do not patch now. This may become an execution-critical owner-window control. | Before any actual board run, determine whether the named owner's reservation/lock protocol already enforces exclusivity. If not, implement the smallest control required to prevent a second launch in the same window. |
| R16 P2-3: durable recording of later non-start conflicts | Defer. No current experiment evidence is known to be lost or misattributed. | Revisit only if the planned run's evidence chain can omit or misattribute a non-start outcome. |
| R17 AST test-guard precision | Defer. Current parser use sites were statically traced through strict QID matching; the finding concerns test guard strength. | Revisit if parser behavior is shown to be wrong or the next experiment depends on a contract that the current checks cannot establish. |
| Coordinator model-manifest mirror is stale | Historical host runs remain valid: their run manifest pins the primary checkout manifest hash and corrected `no-nextn` GGUF hash. The coordinator mirror points to the earlier regular Q4_K_M artifact. | Before any new run rooted in the coordinator checkout, stage the verified current model manifest and artifacts by an approved, hash-preserving path; never infer the historical run's model identity from the stale mirror. |
| Rare malformed-input, schema, NaN, and log-format edges | Backlog unless they cross one of the immediate-fix conditions. | Revisit on a concrete experiment path, observed failure, evidence mismatch, or a direct safety hazard. |

## Board work boundary

Offline literature and trace analysis may proceed. Board/SSH/inference/bitstream actions still require the recorded safety gates and fresh explicit authorization for the exact bounded operation. A measurement plan is useful only if it states which architecture or go/no-go decision its result changes.
