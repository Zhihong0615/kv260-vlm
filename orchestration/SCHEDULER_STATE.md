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
- E01 Current P2 Gate Reviewer: delivered and integrated. Exact snapshot `880096cc50f4d37692012136ef7d204856df40ca`; worker report commit `9830c219f4f0a8f4c6361f57a668e210e0625ef7`; coordinator merge `772fa8ad9985ee4c932226f7b9d12d2d5e70318d`. Result P0=0, P1=0, P2=7 on current parser/runner/preflight hashes. The report text meets the source-level mechanical predicate; the actual configured review gate remains closed because the runner reads two fixed review paths in the primary checkout and this review is only integrated in the isolated coordinator. No board execution readiness is implied.
- B02 Workload Pattern Evidence Analyst: delivered and integrated. Frozen snapshot `548d6229d9fbff67db5103933d9c837259d6b4f4`; all 20 hashes passed. Worker start `a7b9d5cd2e9ec2212689de0838bd46f91a9c4691`, final worker commit `eb0c7a64a9cebac30187f414a8f0b5421a7c9acf`, coordinator merge `bf7cc170c9fddcf40d843a9851958fe1d24cef6f`. Four selected host requests match their logged ordered visual-token patterns; none has graph/op-shape or allocator traces. This is offline evidence reconciliation only and promotes no method.
- B03 Selected Request Trace Builder: delivered on exact base `2f31453557cdbb1501cdda33c52c32e0a3ef7cf2`; worker commit `4d7ce5e5fa5e750833cb5a05b8b3a15364861134`. All 39 frozen source hashes passed before and after capture; all four traces and the derived group summary passed integrity checks. The independent R02 review is pending before coordinator integration.
- R02 Independent B03 Evidence Reviewer: delivered and integrated at merge `3e57050f4992ce20b452e43bd4c9bee33cf26436`. The corrected review commit `8aa54cbb28bde5a28f33a343b7db071f6afe474a` returns **PASS**, P0=0/P1=0/P2=1, on target `4d7ce5e5fa5e750833cb5a05b8b3a15364861134`. The canonical B03 activation at `f3081626b18865b87ed21690a3759b4c4ecdd24b` and B03 branch reflog both identify base `2f31453557cdbb1501cdda33c52c32e0a3ef7cf2`; the single P2 finding is an older duplicate activation file in the B03 worker tree. Source/output hashes, identities, group counts, and bounded claims passed.
- B04 Static-Key Coverage Analyst: delivered and integrated on exact B03 source base `4d7ce5e5fa5e750833cb5a05b8b3a15364861134`; worker commit `966fbf5372a0e1f47f11da999a9298625233870a`; coordinator merge with R03 `ccba27d62d4a8a845080d592fd140f28afc177a`. All eight frozen inputs passed before and after analysis. The report describes 21,936 node records with complete signature fields; 267 full keys; five group-set equivalence classes; 44 GEMM M/N/K keys with no distinct-full-key merges; and 30 collisions under the coarser op/output-shape key. B04 reports 65 signatures shared only by q34609/q35419 plus one signature shared by all four; the five other pairwise overlaps are that all-qid signature. It rejects group ordinal as additional *operator-signature information* for these four traces, but makes no backend-placement, cost, or K26 claim.
- R03 Independent B04 Evidence Reviewer: delivered and integrated at merge `ccba27d62d4a8a845080d592fd140f28afc177a`; report commit `af1e3893d2eb4cd1a7675501cff273ac2a9aa6ed` returns **PASS**, P0=0/P1=0/P2=0. Independent trace-only recomputation confirmed input/output hashes, 21,936 node records, all 24 group classes, six request-pair intersections, and coarse-key collision counts.
- E02 Runner Readiness Remediation Builder: active on exact base `7385c0b10033244b3e203a3b152ca63720207222`; activation `orchestration/activations/E02.md`. It copies the two reviewed subject files from the nine-entry frozen E01 snapshot and scopes source-only fixes for P2-1/2/3/4. It explicitly leaves P2-5/6/7, configured review paths, ALPHA proof, live resource gates, and operator-window evidence unresolved. No tests or board work are part of E02.

No user-visible Codex task window has been created. The baseline Builder tasks have completed in their isolated worktrees; R02 remains the active Reviewer and B04 is queued behind its final verdict. Do not reopen completed worker branches as writers.

## Next decision

B03 completed and passed exact-SHA independent review. It found real group-level shape variation, but no K26 cost or advantage over static shape/stride dispatch. R02 PASS includes one non-blocking P2 ambiguity from a stale duplicate activation copy in the B03 worker tree. B04 and R03 both passed; the measured four-request metadata falsifies the narrow claim that media-group ordinal adds operator-signature information beyond the full per-op key, while leaving state, allocation, placement, submission cost and all K26 effects unmeasured. E02 is active to reduce some software gate defects in an isolated source snapshot; the configured CPU-runner review gate remains closed. E01's P2-5/6/7 and external execution gates remain open. R01's exact-SHA result is **FAIL**, so no architecture candidate is selected. Keep P3 at `NO_GO_NOW`; these host tasks cannot support a method claim or authorize board execution. D's runbook is readiness documentation; it does not itself satisfy any board gate.
