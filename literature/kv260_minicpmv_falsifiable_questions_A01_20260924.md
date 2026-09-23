# Falsifiable K26 questions for complete MiniCPM-V 4.6

Date: 2026-09-24
Status: research questions only. Thresholds below are proposed preregistration values and are not frozen.

## Shared comparison contract

Freeze MiniCPM-V 4.6 checkpoint/processor, llama.cpp revision, Q4_K_M model, F16 mmproj, thread count, prompt/output cap, image set, and scorer. Measure original-image-bytes through final answer, report setup separately, and use identical warm/cold policy. Capture first-visible-token and full-request times plus stage spans, PS submit/wait, DMA, AXI bytes/stalls, PL busy/idle, buffer peak, energy, and answer quality. Graph shapes and host logical bytes remain discovery inputs, not physical-cost evidence.

For each experiment compare against the fastest equally tuned static design among: shared ViT/LLM engine and phase-specific tiles; a charged two-overlay plan where legal; fixed N buckets or two-shape compression where relevant; maximum fixed buffers and double buffering; static matrix-level dispatch; fused layout conversion/FIFO plan; bulk DDR handoff; and deterministic CPU fallback. Include setup, conversion, copy, synchronization, command, and transition costs.

**Proposed common pass bar:** at least 10% lower median full online request latency than the best static control on held-out requests, with paired 95% bootstrap confidence interval excluding zero and no more than 1 percentage point loss in official TextVQA soft accuracy. This is an engineering screen, not a novelty threshold. A positive result using an established mechanism remains an engineering result unless the decision variable or constraint is shown absent from prior art.

## Q1 — Does an image-prefill width tail survive small static tiles?

- **Question.** Do observed image-prefill widths N=60/63/64/66/70 create a per-request K26 tile/descriptor cost that an ordinary static tile/bucket cannot remove?
- **Actual trace needed.** On the real backend path, log crop/group identity and exact dispatched graph node; chosen tile/descriptor; per-tile PL cycles and tail predicates; command count; AXI bytes/stalls; PS submit/sync; and full request timeline. Verify N is present at selector time and these nodes actually reach PL.
- **Closest prior art.** ReCoVLM normalizes variable visual-token streams to fixed downstream lengths; VersaVLM and TeLLMe have static phase-specialized paths; TRINE provides runtime shape/sparsity mode selection; StreamTensor covers tiling/layout/fusion.
- **Strongest static control.** Tune fixed N tile widths 8/16/32/64/128, per-phase fixed widths, tail predication and padding, two fixed buckets, and a fixed CPU fallback. Match precision and request quality. Do not compare only against T=64.
- **Proposed pass criterion.** Meet the shared 10% request-level latency bar and show at least 15% lower measured PS+PL cost on N=66/70 cases than the best fixed tile/bucket, without increased full-request traffic.
- **Reject if.** A fixed T=8/16 or two-bucket path is within 3% on held-out requests; actual PL descriptors do not retain N; no tail-specific cycle/stall/launch penalty appears; or gains vanish after PS/DMA/sync.
- **Current evidence.** Host arithmetic-only screen maps T=8 to 97.3% useful-column occupancy on four selected shapes. This weakens a wide-tile-tail story but is not a timing model. See [padding-screen note](/home/zhiro/research/kv260-vlm/experiments/derived/minicpmv_image_prefill_ffnup_n_tile_padding_screen_round01.md), [host matrix-shape audit](/home/zhiro/research/kv260-vlm/experiments/derived/textvqa_matmul_shapes_four_request_host_audited1.json), and [shape visibility audit](/home/zhiro/research/kv260-vlm/spec/runtime_shape_visibility_audit_20260923.md).

## Q2 — Is there a measured cross-crop weight-reuse/staging crossover?

- **Question.** Do 3/5/7 ordered image groups independently execute compatible work that reloads the same vision weights from DDR, and does a grouping point reduce real traffic before activation staging spills?
- **Actual trace needed.** Recover actual batch semantics, image/crop identity/order, executed matrix sequence, physical weight bytes per group, reread distance, activation/output buffer sizes and lifetimes, BRAM/URAM peak, AXI traffic/stalls, and complete request timing. Logged token patterns alone do not prove independent jobs or repeated physical reads.
- **Closest prior art.** MEADOW packs/reuses weights and switches TPHS/GEMM by bandwidth/PE regime; Hummingbird tunes aligned multi-port transactions; UniVLM shares matrices across phases; StreamTensor plans fusion/FIFOs; ReCoVLM places expert bursts into bank groups.
- **Strongest static control.** Compare serial groups with weight double-buffering, one fixed maximum padded group, equal-shape static buckets, and a development-tuned fixed group size, all with the same movement/layout/fusion plan. Include bulk transfers and charge staging, padding, and transition costs.
- **Proposed pass criterion.** Meet the shared 10% request-level latency bar and reduce measured vision-weight DDR reads by at least 20% against the best fixed group size, while staying below 80% of usable local-memory capacity at peak and not increasing activation spill bytes.
- **Reject if.** Physical traces show no repeated weight reads to avoid; all-crop/static maximum batching is within 3%; staging spills or lowers effective AXI bandwidth enough to erase savings; or traffic falls without request latency/energy improvement.
- **Current evidence.** Existing 3/5/7 group records are host post-processor/graph observations; no board traffic or PL execution is measured. See [visual workload inventory](/home/zhiro/research/kv260-vlm/experiments/derived/textvqa_dev50_visual_workload_inventory.json) and [three-request host timeline note](/home/zhiro/research/kv260-vlm/experiments/derived/textvqa_phase_timeline_three_request_comparison_and_raw_audit.md).

## Q3 — Does the vision-to-language embedding boundary cause an avoidable K26 copy or capacity cliff?

- **Question.** Does the actual MiniCPM-V embedding handoff materialize or copy a tensor in a way that adds PS–PL/DDR time or exceeds usable local storage?
- **Actual trace needed.** Record producer/consumer tensor shape, dtype, stride, and address; copy/convert operations and bytes; DDR/AXI transactions; actual on-chip occupancy alongside compute/interface buffers; producer-consumer overlap; PS wait; and first-token/full-request timeline. Do not infer transfer from host logical bytes.
- **Closest prior art.** StreamTensor covers stream layout conversion, fusion, and FIFO sizing; UniVLM reduces and streams VLM intermediates; Memory-Centric VLM Deployment accounts for PS–PL movement and matrix dispatch; ReCoVLM compresses before GPU-to-FPGA KV transfer. Hummingbird's offloaded language embedding table differs from MiniCPM's visual-language input embedding; compare only the general boundary-measurement issue.
- **Strongest static control.** Compare with a statically fused producer/consumer pipeline using pre-sized FIFOs and explicit conversion, a maximum-size preallocated buffer with double buffering, and a bulk DDR handoff with matrix-level dispatch.
- **Proposed pass criterion.** Meet the shared 10% request-level latency bar and remove at least 20% of measured boundary bytes or wait time versus the best static fused/bulk plan, with peak local use below 80% of post-interface usable BRAM/URAM.
- **Reject if.** Runtime hands one shared buffer directly to the consumer; copy/wait is under 5% of online latency; the tensor fits with the static compute/buffer plan without spill; or static fusion is within 3%.
- **Current evidence.** A host graph estimates F32 input_embed as [1024,N]; 1.89 MiB at maximum logged token sum 484 is conditional arithmetic, not measured materialization, copy, PS–PL traffic, or K26 residency. See the existing [hypothesis memo](/home/zhiro/research/kv260-vlm/literature/kv260_vlm_falsifiable_hypotheses_20260923.md#h4--vision-to-language-embedding-materialization-crosses-a-practical-local-memory-threshold).

## Q4 — Do repeated image groups expose command gaps after matrix-level dispatch?

- **Question.** Is per-operation submit/doorbell/wait cost large enough on the actual K26 software path that a fixed command template per known graph bucket wins after address patching?
- **Actual trace needed.** Timestamp PS submit, doorbell, IRQ/poll, wait, DMA descriptors, PL busy/idle, sequence hashes, shape/address changes, and full request spans. Confirm repeated host graph nodes execute as repeated PL jobs.
- **Closest prior art.** Memory-Centric VLM Deployment dispatches once per matrix and puts tiling in hardware; GLITCHES aggregates small load instructions; TRINE overlaps ready DAG branches; the AICAS single-request GPU system uses preallocation and bucketized CUDA Graphs.
- **Strongest static control.** Compare per-matrix launch, largest fixed command batch that fits, fixed replay lists for each N bucket with address patching, and any legal static/persistent sequence. Keep movement, buffers, and CPU fallback identical.
- **Proposed pass criterion.** Meet the shared 10% request-level latency bar, cut measured online PS wait/PL idle by at least 25% versus the best static matrix-level or replay control, and keep command preparation/address patching below 5% of saved time.
- **Reject if.** Dispatch/wait is under 5% of request time; PL stays busy through apparent host gaps; static replay is within 3%; address/sequence preparation erases savings; or a repeated graph node does not become repeated hardware work.
- **Current evidence.** Host timings are x86 phase spans and graph traces, not A53/XRT launch times or PL busy cycles; command replay is not established.

## Rejected as a distinct method claim now

A generic N-keyed GEMM/GEMV or phase-mode selector does not survive: pinned runtime source exposes node shape before backend assignment, and observed N=1 decode versus N=60–70 prefill can be handled by a static phase/shape lookup. VersaVLM, TeLLMe, Hummingbird, and TRINE further cover phase paths, mode choice, or adaptive configuration. A future test may use that lookup as a control, but the current record gives no variable that beats it. See the [runtime visibility audit](/home/zhiro/research/kv260-vlm/spec/runtime_shape_visibility_audit_20260923.md) and [P3 status](/home/zhiro/research/kv260-vlm/status/go_no_go.md).

## Stop rule

Do not elevate any question to a method until it beats the strongest static control on held-out requests after transfer, launch, layout, synchronization, transition, and answer-quality costs. If all questions are rejected, record a negative engineering result. These proposed criteria do not authorize board activity or change the existing P3 NO_GO_NOW gate.
