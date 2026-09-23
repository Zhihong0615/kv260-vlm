# Scheduler State — KV260 + MiniCPM-V 4.6

Updated: 2026-09-24  
Coordinator branch: `orchestration/dispatch-20260924`  
Coordinator worktree: `/home/zhiro/research/kv260-vlm-orchestration`  
Worker baseline: `094edc130489dc59dd9333e4ae6b0aa4c8013149` on local `master`  
Git remote: none configured

## Stage and decision

- P0: post-reboot access and the immediate CPU-runner CMA gate pass.
- P1: literature and novelty analysis remain in progress; broad PhaseMap novelty is rejected and no method claim is selected.
- P2: host baseline, workload traces, numeric feasibility and board CPU build evidence are in progress.
- P3: **NO_GO_NOW**. Do not start accelerator RTL, load a research bitstream, or write a contribution claim.
- P4–P8: not started.

This remains an active end-to-end research project. The present dispatch is limited to P1/P2 research and board-safety documentation.

## Confirmed facts

- User-approved normal reboot completed. The board returned over Wi-Fi SSH with a new boot ID; the reboot marker is absent; APT is idle; Jupyter and the starter-kit app are active; XRT reports the KV260 ready.
- Three post-reboot snapshots recorded `CmaFree=1,014,300 KiB`, above the existing 700,000 KiB CPU-runner floor. The earlier low-CMA allocation owner remains unknown. This does not authorize a new reboot or inference run.
- The board has a validated AArch64 CPU CLI build and input-file hash checks, but **no board VLM inference has run**.
- Current board inference still lacks current-SHA independent parser/runner review, synthetic ALPHA evidence, and an inference-specific owner window.
- Host TextVQA dev50 CPU baseline: 0.644 MMF soft accuracy, 0.68 exact normalized match, median fresh-process wall 8.558 s and P95 12.548 s. Development-only; not a KV260 result.
- Host evidence includes three selected online timelines; four audited allocator-metadata requests; four-request matrix-shape inventory; and a 50-request visual-token log. These are host evidence, not board traffic, PL timing, physical occupancy, or measured DDR bytes.
- Observed image-encode requests contain 3/5/7 batches. Selected image-prefill widths include N=60/63/64/66/70; selected vision widths include N=960/1024/1056.
- A host arithmetic screen shows an N-tile width of 8 already raises useful-column occupancy to 97.3% on the selected image-prefill nodes. This screen is not a timing result.
- Pinned llama.cpp source exposes graph node dimensions before backend allocation; shape-keyed static dispatch is therefore a strong null baseline.
- ReCoVLM directly covers heterogeneous VLM phase assignment, visual-token normalization to fixed shapes, KV transfer reduction, static KV residency, CPU LM-head work, and MoE bank-group placement. Its Orin/VU9P results do not establish KV260 feasibility.
- Current checked-in project HEAD is `094edc130489dc59dd9333e4ae6b0aa4c8013149`. The primary checkout `/home/zhiro/research/kv260-vlm` is on `master` with extensive uncommitted and untracked research artifacts; `experiments/` is about 1.3 GB and includes large traces/source archives. Do not make a broad commit or copy all raw data into worker branches.
- Worker input documents are read-only at `/home/zhiro/research/kv260-vlm`; their per-task SHA-256 manifests are in `orchestration/source_snapshots/` on this coordinator branch. Worker code and outputs belong in their isolated worktrees.

## Current research question

Do real MiniCPM-V 4.6 request shapes, ordered image groups, tensor residency, or PS–PL boundary costs create a measured K26 failure interval that remains after the strongest static phase/shape/bucket/tile/batching controls—and, if so, does that interval support a concrete mechanism under KV260 resource limits?

## Provisional hypotheses (not claims)

1. H1 image-prefill tile-tail discontinuity: weakened by the T=8 arithmetic screen and shape-visible static dispatch; survives only if target timing shows a distinct cost beyond static tuning.
2. H2 cross-batch weight reuse versus staging spill: requires actual repeated weight traffic, crop semantics, local-memory occupancy and DDR evidence.
3. H3 repeated visual-subgraph command overhead: requires PS submit/wait and PL busy/idle traces; static command batching/replay is a strong null.
4. H4 vision-to-language embedding materialization threshold: requires real boundary bytes, overlap, occupancy and transfer costs.
5. H5 image-group-dependent buffer/CMA admission cliff: requires request-correlated physical allocation evidence on an idle board; the prior low-CMA episode was not a VLM run and its cause is unknown.

Any candidate may be rejected. The current global novelty verdict remains unchanged until evidence and an independent review support a Scheduler decision.

## Blockers

- No measured KV260 VLM path, PS–PL transfer, PL timing, or physical DDR/bank/BRAM/URAM occupancy.
- No hypothesis has beaten the strongest static baseline.
- No frozen numeric tolerance / held-out quality contract for a PL path.
- No verified UART recovery route; no USB-UART was connected in the last recorded check.
- No new research-bitstream image, hash, load procedure, rollback proof, or user approval for first load.
- No Git remote; GitHub Issues, pushes and PRs are unavailable. Do not add a remote or publish data.

## Active work

- A01 Prior-Art / Novelty: delegated worker running in its isolated worktree; branch/HEAD/source hashes passed preflight.
- B01 Workload Profile: delegated worker running; initial preflight confirmation pending.
- C01 Architecture Candidates: delegated worker running; initial preflight confirmation pending.
- D01 Board Readiness / Recovery: brief and isolated worktree prepared; queued until a worker slot opens.
- R01 Adversarial Reviewer: queued; do not start until A/B/C handoffs and their exact commits are frozen.

No user-visible Codex task window has been created. A01/B01/C01 are running through delegated worker agents in their isolated worktrees; do not start duplicate writers in those branches.

## Next decision

After A/B/C deliver committed handoffs, compare each candidate against its closest prior art and strongest static control. Keep P3 at NO_GO_NOW unless an independent Reviewer finds no FAIL, the evidence supports a concrete falsifiable mechanism, numeric and board-safety contracts close, and the user explicitly approves the first research-bitstream load. D's runbook work does not itself satisfy those gates.
