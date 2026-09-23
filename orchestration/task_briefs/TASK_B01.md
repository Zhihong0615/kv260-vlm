# Task ID

B01 — Profiling / Workload Researcher

# Role

Builder for P2 hardware-relevant workload evidence. Analyze only measurements and traces that can change a hardware/runtime decision.

# Current project HEAD

Project baseline: `094edc130489dc59dd9333e4ae6b0aa4c8013149`  
Source evidence checkout: `/home/zhiro/research/kv260-vlm` (dirty overlay; read-only; verify `orchestration/source_snapshots/TASK_B01.sha256`).  
Task brief and hash manifest are frozen in `/home/zhiro/research/kv260-vlm-orchestration`.

# Branch / Worktree / Base commit

Branch: `agent/B01-workload-profile`  
Worktree: `/home/zhiro/research/kv260-vlm-workers/B01-workload-profile`  
Base commit and required initial HEAD: `094edc130489dc59dd9333e4ae6b0aa4c8013149`  
Required start state: clean worktree; verify `git status --short --branch`, `git branch --show-current`, and `git rev-parse HEAD`. Stop if any value differs.

# Stage

P2 in progress. No board VLM inference or PS–PL implementation exists.

# Question

Which existing MiniCPM-V workload records are strong enough to set accelerator shape, tile, buffering, DMA, and PS–PL-boundary priorities, and which highest-impact evidence gaps prevent those decisions?

# Read first

Read these exact source-checkout files first; do not scan the full repository:

1. `/home/zhiro/research/kv260-vlm/status/PROJECT_STATUS.md`
2. `/home/zhiro/research/kv260-vlm/status/go_no_go.md`
3. `/home/zhiro/research/kv260-vlm/literature/kv260_vlm_falsifiable_hypotheses_20260923.md`
4. `/home/zhiro/research/kv260-vlm/experiments/derived/textvqa_dev50_visual_workload_inventory_ANALYSIS_NOTE.md`
5. `/home/zhiro/research/kv260-vlm/experiments/derived/textvqa_matmul_shapes_four_request_host_audited1_ANALYSIS_NOTE.md`
6. `/home/zhiro/research/kv260-vlm/experiments/derived/textvqa_allocator_metadata_four_request_comparison_audited4_ANALYSIS_NOTE.md`
7. `/home/zhiro/research/kv260-vlm/experiments/derived/textvqa_phase_timeline_three_request_comparison_and_raw_audit.md`
8. `/home/zhiro/research/kv260-vlm/experiments/derived/host_phase_timeline_boundary_spec.md`
9. `/home/zhiro/research/kv260-vlm/experiments/derived/minicpmv_image_prefill_ffnup_n_tile_padding_screen_round01.md`

Verify their hashes using `orchestration/source_snapshots/TASK_B01.sha256` in the coordinator worktree. Follow cited raw trace paths only when necessary, and record exact input hashes/paths.

# Known facts

- Host dev50 contains seven ordered logged image-token patterns with 3/5/7 groups; log availability before dispatch is not established.
- Four audited host requests expose variable selected matrix widths and allocator metadata. These are graph and virtual-buffer observations, not executed PL kernels, physical lifetimes, or DDR traffic.
- Three selected host timelines contain 3/5/7 image-encoder calls; they are not a representative population estimate.
- The host image-prefill N=8 arithmetic screen reports 97.3% useful-column occupancy for selected shapes; it is not a timing or tile-selection result.
- Host CPU TextVQA dev50 median fresh-process wall is 8.558 s, P95 12.548 s, and MMF soft accuracy is 0.644; this is not a KV260 result.
- ReCoVLM and other existing papers already cover several generic mechanisms; a profile alone does not establish novelty.

# Important uncertainties

- Which operation/shape buckets dominate weighted end-to-end time on the real KV260 path.
- True crop/batch semantics, actual executed kernels, per-request repeated-weight traffic, reuse distance, and physical tensor lifetime.
- Real DMA/AXI bytes, command and synchronization overhead, PS–PL idle gaps, stalls, board memory pressure and local-memory occupancy.
- Which observations are representative of held-out requests rather than selected examples.

# Forbidden assumptions

- Do not multiply graph-node count by nominal FLOPs and call it measured time.
- Do not label logical bytes as DDR traffic or allocator metadata as physical allocation/liveness.
- Do not infer a K26 PE/tile/BRAM/URAM/port design from host-only quantities.
- Do not run more traces just to increase sample count; every new measurement needs a stated decision it can change.
- Do not modify global go/no-go or claim novelty.

# Scope

- Reconcile existing dev50 visual patterns, shape inventory, timing boundaries, dtype/quantization mix and allocator traces.
- Report per-request/per-phase call counts and weighted work only where the measurement supports it.
- Distinguish measured timings from graph counts, arithmetic proxies, virtual allocation, and derived estimates.
- Rank the most hardware-relevant workloads and the remaining unknowns by their expected impact on a design decision.
- Propose the smallest next measurement that would resolve each top-ranked unknown. Analyze host traces only; do not access or load the board.
- A new host trace is in scope only if you first state the decision it resolves, the minimum trace fields, and why existing evidence cannot answer it. Do not collect it if that case is already represented by a current review or can be answered from an existing raw file.

# Out of scope

- No new FPGA/RTL/bitstream, board command, board inference, reboot, or system reconfiguration.
- No broad benchmark campaign, trace-every-node effort, or unbounded parsing.
- No claims about true reuse/lifetime/traffic without direct evidence.
- No GitHub Issue, push, PR, remote setup, or publication.

# Deliverables

- `orchestration/handoffs/B_workload_handoff.md`
- A concise, reproducible hardware-relevant profile under `experiments/derived/` on this branch.
- The handoff must end with **Top hardware-relevant workloads** and **Remaining unknowns ranked by importance**.
- Record exact input hashes. Keep raw inputs read-only; never commit large raw traces or source archives.

# Acceptance criteria

- Each reported number is labeled by evidence class, population, shape/phase, and measurement boundary.
- Workload ranking is linked to concrete hardware decisions (PE shape, tile, DMA, local memory, boundary, or fallback).
- Unknowns are ranked and each has a minimal resolving experiment and explicit stop condition.
- No unsupported physical, board, or novelty claim appears.
- Handoff includes changed files, commit SHA, reproducibility steps, checks performed, and blockers.

# Stop conditions

Stop and report if a required raw input is missing or hash-mismatched, if the result depends on board-only fields unavailable in current evidence, if analysis would require broad new data collection, or if a derived script would need changes to shared APIs. Keep the source checkout read-only.
