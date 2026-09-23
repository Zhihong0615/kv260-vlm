# Task ID

A01 — Prior-Art / Novelty Researcher

# Role

Builder for P1 literature analysis. Work independently from the Scheduler and from B/C. The attached research-orchestration instructions are the governing scope.

# Current project HEAD

Project baseline: `094edc130489dc59dd9333e4ae6b0aa4c8013149`  
Source evidence checkout: `/home/zhiro/research/kv260-vlm` (dirty overlay; read-only; verify `orchestration/source_snapshots/TASK_A01.sha256`).  
This task brief is frozen in the coordinator worktree at `/home/zhiro/research/kv260-vlm-orchestration`.

# Branch / Worktree / Base commit

Branch: `agent/A01-prior-art`  
Worktree: `/home/zhiro/research/kv260-vlm-workers/A01-prior-art`  
Base commit and required initial HEAD: `094edc130489dc59dd9333e4ae6b0aa4c8013149`  
Required start state: clean worktree; verify `git status --short --branch`, `git branch --show-current`, and `git rev-parse HEAD`. Stop if any value differs.

# Stage

P1 in progress; P3 is NO_GO_NOW.

# Question

Which constraint-specific failure regimes in the closest FPGA/LLM/VLM papers generated their research ideas, and which—if any—remain uncovered for real MiniCPM-V 4.6 workloads on KV260 after the strongest static controls?

# Read first

Read these exact source-checkout files first; do not scan the full repository:

1. `/home/zhiro/research/kv260-vlm/status/PROJECT_STATUS.md`
2. `/home/zhiro/research/kv260-vlm/status/go_no_go.md`
3. `/home/zhiro/research/kv260-vlm/literature/idea_derivation_chains_20260923.md`
4. `/home/zhiro/research/kv260-vlm/literature/notes/recovlm.md`
5. `/home/zhiro/research/kv260-vlm/literature/notes/streamtensor.md`
6. `/home/zhiro/research/kv260-vlm/literature/notes/trine.md`
7. `/home/zhiro/research/kv260-vlm/literature/notes/persistent_state.md`
8. `/home/zhiro/research/kv260-vlm/literature/prior_art_matrix_correction_20260923.md`
9. `/home/zhiro/research/kv260-vlm/literature/source_access.md`
10. `/home/zhiro/research/kv260-vlm/literature/kv260_vlm_falsifiable_hypotheses_20260923.md`

Verify their hashes using `orchestration/source_snapshots/TASK_A01.sha256` in the coordinator worktree. Read source PDFs or official artifacts as needed for primary evidence.

# Known facts

- Broad PhaseMap novelty was rejected; no method claim is selected.
- Direct prior art already covers FPGA VLM phase assignment, fixed-shape visual-token normalization, KV movement/residency, streaming/fusion, memory-centric matrix dispatch, persistent state, and bank/port-aware placement.
- Host traces show 3/5/7 ordered image groups and variable graph widths, but do not establish board cost or physical traffic.
- Static shape/tile/bucket controls are strong. The existing N=8 padding screen is arithmetic-only and weakens H1.
- ReCoVLM was read from a user-supplied full paper; its platform is Orin Nano + VU9P, not KV260.
- These facts are provisional inputs. Your work must independently verify evidence level and exact source scope.

# Important uncertainties

- Whether any MiniCPM-V shape/group transition causes a measured K26 discontinuity beyond static tuning.
- Whether current traces expose selector signals before the decision point.
- Whether a proposed gap survives the closest paper's mechanism and baseline.
- Which cited results are board-measured versus analytical, simulated, or transferred from another platform.

# Forbidden assumptions

- Similarity of names is not novelty.
- Host graph shape, virtual allocator extent, logical bytes, or callback time is not board traffic, physical lifetime, or isolated kernel time.
- Do not treat candidate hypotheses as global conclusions.
- Do not claim the absence of a paper without a documented search scope.
- Do not treat ReCoVLM's platform or baseline asymmetry as a KV260 result.

# Scope

- Reconstruct idea-derivation chains for ReCoVLM, StreamTensor, TRINE, Persistent-State Dataflow, Hummingbird, MEADOW, TeLLMe, and the closest additional FPGA/FCCM/FPL/DAC/ICCAD/DATE/AICAS/ASP-DAC work.
- For each selected paper, state: observation, root cause, why prior methods fail, key decision variable, mechanism, strongest baseline, evidence, and failure regime.
- Produce 3–5 falsifiable KV260 + complete MiniCPM-V hypotheses. Each must name the actual trace needed, closest prior work, strongest static control, a numeric success criterion to propose, and a result that rejects it.
- Clearly separate a research question from a contribution claim. Record “none survive” if appropriate.
- Update literature files only on this branch; do not modify the global novelty verdict or status.

# Out of scope

- No RTL/HLS, bitstream, board inference, reboot, board configuration, or long benchmark.
- No edits to `status/go_no_go.md` or the global novelty conclusion.
- No broad literature dump or unbounded paper search.
- No GitHub Issue, push, PR, remote setup, or publication; this repository has no configured remote.

# Deliverables

- `orchestration/handoffs/A_novelty_handoff.md`
- Targeted literature updates under `literature/` on this branch only.
- Commit the brief and handoff/update milestones locally. Never stage large raw traces, weights, private files, or the whole `experiments/raw/` tree.

# Acceptance criteria

- Handoff gives a direct answer in at most 10 lines, followed by evidence, sources, caveats, and rejected alternatives.
- Paper summaries use the required eight-link chain and qualify each result by platform and measurement boundary.
- Hypotheses are falsifiable and compare against a genuinely strong static/prior-art baseline; at least one may be explicitly rejected.
- Every changed research statement links to a primary source or a local evidence file and is distinguished from inference.
- Handoff identifies changed files, commit SHA, checks performed, and remaining blockers.
- Independent review is still required before Scheduler changes any global research decision.

# Stop conditions

Stop and report in the handoff if hashes do not match, source access is unavailable, the cited paper cannot be verified, or completing the task would require board activity, a new accelerator, an unbounded data collection, or an unsupported novelty assertion. Do not repair the source checkout.
