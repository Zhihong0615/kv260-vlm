# Task ID

C01 — Architecture Hypothesis Researcher

# Role

Highest-priority builder for P1/P2 architecture reasoning. This is a research task, not RTL design.

# Current project HEAD

Project baseline: `094edc130489dc59dd9333e4ae6b0aa4c8013149`  
Source evidence checkout: `/home/zhiro/research/kv260-vlm` (dirty overlay; read-only; verify `orchestration/source_snapshots/TASK_C01.sha256`).  
Task brief and hash manifest are frozen in `/home/zhiro/research/kv260-vlm-orchestration`.

# Branch / Worktree / Base commit

Branch: `agent/C01-architecture-candidates`  
Worktree: `/home/zhiro/research/kv260-vlm-workers/C01-architecture-candidates`  
Base commit and required initial HEAD: `094edc130489dc59dd9333e4ae6b0aa4c8013149`  
Required start state: clean worktree; verify `git status --short --branch`, `git branch --show-current`, and `git rev-parse HEAD`. Stop if any value differs.

# Stage

P1/P2 in progress; P3 is NO_GO_NOW. Start with current frozen evidence; do not wait for A/B. Incorporate their committed handoffs later, then make a separate update commit if warranted.

# Question

Does any concrete accelerator mechanism remain after direct prior-art comparison and the best static controls, given the actual KV260 resource limits and current MiniCPM-V evidence?

# Read first

Read these exact source-checkout files first; do not scan the full repository:

1. `/home/zhiro/research/kv260-vlm/status/PROJECT_STATUS.md`
2. `/home/zhiro/research/kv260-vlm/status/go_no_go.md`
3. `/home/zhiro/research/kv260-vlm/literature/kv260_vlm_falsifiable_hypotheses_20260923.md`
4. `/home/zhiro/research/kv260-vlm/literature/independent_novelty_review.md`
5. `/home/zhiro/research/kv260-vlm/literature/notes/recovlm.md`
6. `/home/zhiro/research/kv260-vlm/spec/p3_candidate_decision_fixed_bitstream_draft.md`
7. `/home/zhiro/research/kv260-vlm/spec/vision_vs_q4_pl_mvp_screen.md`
8. `/home/zhiro/research/kv260-vlm/spec/runtime_shape_visibility_audit_20260923.md`
9. `/home/zhiro/research/kv260-vlm/reviews/pl_mvp_interface_independent_review.md`

Verify their hashes using `orchestration/source_snapshots/TASK_C01.sha256` in the coordinator worktree. Check for A/B handoffs at the coordinator source path only after beginning your own analysis.

# Known facts

- Broad PhaseMap novelty did not pass; no method claim is selected.
- ReCoVLM directly covers several mechanisms previously floated as candidates, including fixed-shape visual-token normalization, stage placement, KV transfer/residency, CPU LM-head work, and MoE bank-group placement.
- Static phase/shape dispatch is a strong baseline because graph dimensions are visible before backend allocation in the pinned runtime.
- H1's host arithmetic-only N=8 tile screen already weakens a width-64 tail story; no board timing supports a tail-cost claim.
- There are host shape, selected timing, and allocator observations, but no measured KV260 VLM execution, PL traffic, PS–PL transfer, physical local-memory occupancy, or board stall trace.
- P3 remains NO_GO_NOW.

# Important uncertainties

- Whether any of H1–H5 is a real failure interval on K26 rather than a conventional static tuning opportunity.
- Whether current request metadata is available at the necessary selector point.
- Whether the mechanism's benefit survives transition, staging, PS–PL, full-request quality, energy and area costs.
- Whether a simpler static per-shape, fixed-bucket, batch, CPU-fallback, or command-list control removes the opportunity.

# Forbidden assumptions

- Do not rename phase scheduling, tensor-lifetime reuse, bank allocation, Q4_K acceleration, command batching, or fixed-shape bucketing as a new contribution.
- Do not treat a candidate as novel because the exact platform/model pairing is less common.
- Host evidence is not board evidence; virtual allocation is not physical traffic or BRAM/URAM residency.
- Do not convert candidate arithmetic into an expected speedup.
- Do not edit `status/go_no_go.md`, `status/PROJECT_STATUS.md`, or the global novelty verdict.
- Do not let an architecture sketch bypass the independent Reviewer.

# Scope

- Independently screen existing H1–H5 and at most two additional mechanism candidates.
- Keep no more than three candidates total; explicitly conclude **NONE OF THEM IS STRONG ENOUGH** if evidence or prior-art separation is inadequate.
- For each candidate provide: problem, observed evidence and its class, mechanism and hardware structure, changed decision variable, closest prior-art competitor, strongest static control, expected source of benefit, resource/area/runtime cost, required real trace, numeric success threshold proposal, direct falsification result, and minimum viable experiment.
- Create a comparison table and recommend only the next measurement—not RTL.
- Begin now from current evidence. Once A/B handoffs are committed, compare them and update only if they materially change the candidate ranking; cite exact commit SHAs.

# Out of scope

- No RTL/HLS, bitstream, board inference, reboot, board configuration, or first-load preparation.
- No paper conclusion, novelty claim, P3 gate change, or edits to global status.
- No new host/board experiment unless the Scheduler first issues a separate task brief.
- No GitHub Issue, push, PR, remote setup, or publication.

# Deliverables

- `orchestration/handoffs/C_architecture_candidates.md`
- Any compact supporting candidate matrix under `spec/` on this branch.
- Commit the initial reasoning separately from any later A/B incorporation. Do not commit raw traces, model weights, or private material.

# Acceptance criteria

- At most three concrete candidates; “none” is an acceptable and valuable answer.
- Every candidate names a finite observed failure interval, a decision variable not already handled by static controls, and a measurement that could disprove it.
- Baselines include the strongest static controls and closest paper mechanism, with all transition and full-request costs included.
- Claims distinguish measured facts, estimates, and proposals; each source is traceable.
- Handoff includes the verdict per candidate, changed files, exact commits, checks, and unresolved dependencies.

# Stop conditions

Stop and report if a candidate requires an unsupported novelty claim, no actual selector signal exists at decision time, the strongest static baseline is not reproducible, or the next step requires board access, RTL/bitstream, or a changed P3 gate. Do not modify the source checkout.
