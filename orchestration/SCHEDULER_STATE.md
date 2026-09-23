# Scheduler State — KV260 + MiniCPM-V 4.6

Updated: 2026-09-24  
Coordinator branch: `orchestration/dispatch-20260924`  
Coordinator worktree: `/home/zhiro/research/kv260-vlm-orchestration`  
Worker baseline: `094edc130489dc59dd9333e4ae6b0aa4c8013149` on local `master`  
Git remote: `origin` → `https://github.com/Zhihong0615/kv260-vlm.git` (HTTPS; authenticated via GitHub CLI and system Keyring; private repository has no default branch/refs yet)

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
- A01/B01/C01/D01 completed from the exact clean baseline with all frozen input hashes passing; their handoffs are integrated on this coordinator branch. Their results preserve the distinction between host/analytical evidence and missing K26 measurements.

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
- `origin` is authenticated and readable; GitHub reports the private repository has no default branch and `git ls-remote --heads origin` returns no refs. No branch, issue, PR, or project data has been pushed. Any remote publication remains a separate explicit action. No credential is in the URL or project files.

## Active work

- A01 Prior-Art / Novelty: delivered and integrated. Final worker HEAD `ca2e2101027eb3596b6747c6a5e91bcc80df6f00`; coordinator merge `ac888a540a22be96bafe9976471dc6c41838d5ce`. Verdict: no method claim survives current evidence/prior-art comparison.
- B01 Workload Profile: delivered and integrated. Final worker HEAD `16bd6abf60a92bacca74d6f28124fb085b865153`; coordinator merge `e43406f62ff4fc9226b1bf5c07fea485b43842b7`. Host traces prioritize vision/projector then image-prefill but do not select hardware dimensions.
- C01 Architecture Candidates: delivered and integrated. Final worker HEAD `d0c52e94830ca17b5629e2f1f703840ab84e09ac`; coordinator merge `12b32d191000bbf1acfd71cbe7ed4c7c292796dd`. Verdict: none is strong enough; no measured K26 failure interval or advantage over static controls.
- D01 Board Readiness / Recovery: delivered and integrated. Final worker HEAD `ead34c7873dc0582e8ba4aa6c0b95b043edd7c91`; coordinator merge `e2c6d11b6e60739a3a804cd6643853e088dbde9c`. Runbook is fail-closed; physical recovery and image-specific rollback remain unverified.
- R01 Adversarial Reviewer: delivered and integrated. Exact target `6dd1a83c4c771570b992a7ac83ec7de3d41ef60b`; worker review commit `ea1bfff920c1dc6571c0258935ad6697ea6a2225`; coordinator merge `7657525a147ce08ac2a3ac6b75a919b4fa6ebb8a`. Overall **FAIL**: no candidate has a K26-specific observed failure regime or beats its strongest static control. H1–H3 remain measurement questions only; H4/H5 are screened out. The review strengthens the current P3 `NO_GO_NOW`; it does not alter the frozen source `status/go_no_go.md` or authorize implementation.
- E01 Current P2 Gate Reviewer: active on frozen snapshot `880096cc50f4d37692012136ef7d204856df40ca`; current parser, runner, preflight, focused test source, contract, dry-plan and stale prior reviews are hash-recorded in `orchestration/evidence_snapshots/E01_p2_static_gate_review/SOURCE.sha256`. Its clean isolated worker starts at `d5ab097050a74bf0eeec35a6d3b635e238ea25e9` and is prohibited from tests, dry plans, SSH, board access, inference, and source edits.
- B02 Workload Pattern Evidence Analyst: active on frozen snapshot `548d6229d9fbff67db5103933d9c837259d6b4f4`; all 20 hashes pass. Clean worker starts at `a7b9d5cd2e9ec2212689de0838bd46f91a9c4691`; scope is offline reconciliation of four existing host cases, with no new inference or evidence collection.

No user-visible Codex task window has been created. A01/B01/C01 are running through delegated worker agents in their isolated worktrees; do not start duplicate writers in those branches.

## Next decision

E01's current-SHA static review is in progress. R01's exact-SHA result is **FAIL**, so no architecture candidate is selected; continue P1/P2 evidence work and search for a measured failure interval before reconsidering P3. Keep P3 at `NO_GO_NOW` unless independent evidence supports a falsifiable mechanism that beats strongest controls, numeric and board-safety contracts close, and the user explicitly approves the first research-bitstream load. E01 may only resolve or strengthen the CPU-only runner review gate; it does not authorize board execution. D's runbook is readiness documentation; it does not itself satisfy any board gate.
