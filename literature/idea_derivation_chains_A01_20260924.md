# Constraint-specific idea derivation in close FPGA / LLM / VLM work

Date: 2026-09-24. Scope: P1 prior-art synthesis for MiniCPM-V 4.6 on KV260. This is a research question review, not a contribution selection or hardware result.

## Answer

No method claim survives the prior-art review and current local evidence. Close papers already connect concrete bottlenecks to phase assignment, static shape normalization, memory movement, streaming/fusion, command aggregation, runtime mode selection, and persistent state. The source checkout contains host traces and arithmetic screens, but no KV260 MiniCPM-V inference or physical PS–PL/DDR cost evidence.

The remaining work is to test whether a particular measured MiniCPM-V/K26 cost discontinuity persists after a best static plan. A model or board difference alone is not novelty. The accompanying hypothesis sheet names four experiments and proposed pass/reject rules; these are provisional measurement thresholds, not a global go/no-go decision.

## Eight-link paper chains

Each chain records: observation, root cause, why prior methods fail, decision variable, mechanism, strongest in-paper baseline, evidence boundary, and a regime that defeats the idea. “Strongest baseline” means the strongest relevant comparison that paper actually uses; it does not imply a fair cross-paper or MiniCPM-V comparison.

### ReCoVLM — fixed-shape compression across an FPGA/GPU boundary

Primary source: [FCCM 2026 paper, DOI 10.1109/FCCM68464.2026.00026](https://doi.org/10.1109/FCCM68464.2026.00026). The full publisher PDF and page/hash record were read locally; see the [audited mechanism card](/home/zhiro/research/kv260-vlm/literature/notes/recovlm.md).

1. **Observation.** In its LLaVA-family edge setup, vision/prefill, single-token decode, variable retained visual-token length, and MoE weight access stress different parts of the system.
2. **Root cause.** One device/precision/dataflow does not fit all phases; pruning makes the FPGA decoder's KV and work lengths input-dependent; fragmented expert bursts add memory bubbles.
3. **Why prior methods fail.** The paper argues generic pruning can lose quality, unnormalized variable token counts disturb a fixed downstream pipeline, and token-at-a-time GPU decode is inefficient. These motivations apply to its models and platform.
4. **Decision variable.** Phase-to-device assignment and retained visual-token budget, with downstream lengths normalized to fixed intermediate and final targets P and Z.
5. **Mechanism.** GPU vision and cross-modal prefill; FPGA decode; ARM LM head/sampling; coarse spatial merging plus query-aware filtering to fixed shapes; mixed precision; static sink/ring KV regions; streamed fusion; burst-aligned MoE placement by DDR bank group.
6. **Strongest baseline.** The paper reports GPU-only complete-VLM and FPGA-only prefill/decode comparisons. Coverage is asymmetric, so neither is a clean matched full-system null for every stage.
7. **Evidence boundary.** Measurements use Orin Nano + PCIe + VU9P at 300 MHz, batch one, and LLaVA-1.5-7B or MoE-LLaVA-1.8B-4e. Reported 576-to-32-token transfer latency falls 87.6%; 32-token relative benchmark accuracy is 89.4% and 88.9%. These are not MiniCPM-V/KV260 results; no artifact reproduction was inspected.
8. **Failure regime.** The split/compression benefit fails if filtering cost or quality loss exceeds saved decode/transfer cost, if fixed-shape compression gives no downstream benefit, or if the bottleneck is elsewhere. Generic fixed-shape normalization, boundary transfer reduction, static KV cache, and bank-group placement are occupied claims.

### StreamTensor — layout and token-rate information for composed dataflow

Primary source: [MICRO 2025 full paper, arXiv HTML](https://arxiv.org/html/2509.13694), published DOI 10.1145/3725843.3762817. See the [source-checkout mechanism card](/home/zhiro/research/kv260-vlm/literature/notes/streamtensor.md).

1. **Observation.** Producer and consumer can process the same logical tensor in incompatible iteration/layout orders; fusion can save intermediate storage but introduce conversion, rate mismatch, stalls, or deadlock.
2. **Root cause.** Ordinary shape/dtype types omit stream iteration maps, while kernel fusion, layout, FIFO depth, rates, and limited on-chip memory interact globally.
3. **Why prior methods fail.** Per-kernel optimization and naive fusion do not expose cross-kernel constraints, so they may choose incompatible layouts or undersized buffers.
4. **Decision variable.** Iterative tensor type/layout, fusion plan, tile/resource allocation, and FIFO depth.
5. **Mechanism.** Encode affine stream layout in an iterative tensor type; insert ping-pong converters when needed; explore fusion under an on-chip cap; solve token-rate/FIFO constraints; generate host/DMA runtime support.
6. **Strongest baseline.** Reported comparisons include Allo, DFX, and A100 on paper-specific tasks; the main FPGA result is on U55C, not a KV260 VLM null.
7. **Evidence boundary.** FPGA results use U55C/Vitis 2024.1, W4A8, 16 GB HBM, and 41 MB on-chip memory. GPT-2 latency is 0.76x Allo and 0.64x A100; fused intermediate storage is 14.8–16.8% of evaluated unfused layers. These capacities and LLM-only evaluations differ from K26.
8. **Failure regime.** Fusion is defeated if layout conversion/FIFO/host costs erase traffic savings, if no fitting K26 schedule exists, or if an equally tuned static fused path ties. Stream layout, fusion, and FIFO sizing are not open generic contributions.

### TRINE — runtime mode choice, top-k pruning, and DAG overlap

Primary source: [TRINE full arXiv paper](https://arxiv.org/html/2603.22867v1).

1. **Observation.** Multimodal ViT/CNN/GNN/NLP graphs mix dense, sparse, and irregular kernels; runtime token/edge sparsity and independent DAG branches change utilization.
2. **Root cause.** One dataflow wastes resources across dense and sparse regimes, fixed sparsity misses runtime variation, and sequential scheduling leaves independent branches idle.
3. **Why prior methods fail.** The paper identifies modality-specific accelerators, fixed/limited pruning support, and no general combination of multimodal work, runtime pruning, and dependency-aware overlap.
4. **Decision variable.** Per-layer matrix shape N/M/K, observed sparsity p, PE array width, operation mode, ready-DAG block, and top-k value.
5. **Mechanism.** A single bitstream shares a PE array across WS/OS systolic, 1xCs SIMD, RADT, and normal SIMD; an in-stream top-k gates later work; DALO schedules independent blocks across RPUs.
6. **Strongest baseline.** DALO-on/off ablations isolate overlap; pruning-on/off isolates token reduction. RTX 4090 and Orin Nano comparisons are cross-platform context, not matched K26 controls.
7. **Evidence boundary.** The authors report placed/routed U50/ZCU104 designs, INT8, TinyCLIP, MDETR, and MissionGNN. DALO improves throughput up to 79.2% on multi-RPU U50; ZCU104's single RPU sees no DALO benefit for the stated MDETR case. No MiniCPM-V or K26 test is shown.
8. **Failure regime.** If a graph has no independent branches, runtime sparsity does not change the best mode, or mode/queue overhead exceeds saved cycles, adaptation loses. Generic runtime PE modes, token-aware scheduling, pruning, or DAG scheduling are prior art.

### Persistent-State Dataflow — keep recurrent state on chip

Primary sources: [IPDPSW 2026 DOI](https://doi.org/10.1109/IPDPSW71298.2026.00064) and [full arXiv HTML](https://arxiv.org/html/2603.05931v1). See the [source-checkout mechanism card](/home/zhiro/research/kv260-vlm/literature/notes/persistent_state.md).

1. **Observation.** Batch-one Gated DeltaNet decode performs about 4.2M FLOPs while reading/writing 32 FP32 128x128 recurrent matrices, about 2 MiB, per token.
2. **Root cause.** Repeated round-trips of fixed recurrent state through GPU HBM make the operation memory-bound at low arithmetic intensity.
3. **Why prior methods fail.** A normal step makes three full state passes and reloads state each token; arithmetic optimization that retains those transfers leaves the dominant cost intact.
4. **Decision variable.** Value heads per iteration H_iter, subject to full-state BRAM fit and DSP/FF/LUT/routing limits.
5. **Mechanism.** Hold 2 MiB state in dual-port BRAM; algebraically combine output with update to reduce three passes to two; pair heads through GVA; pipeline preparation, compute, and store.
6. **Strongest baseline.** Sequential GDN on the official H100 PyTorch reference and a naive FPGA pass-count model. H_iter=8 is a cycle-derived estimate; the physically routed H_iter=2 design is the implemented point.
7. **Evidence boundary.** U55C/Vitis HLS, one Qwen3-Next-style GDN layer, FP32. H_iter=2 is placed/routed at 263 MHz and 161.7 us/token; H_iter=4 fails routing; H_iter=8's 63.2 us and H_iter=16's 77.4 us are cycle estimates, with H_iter=16 regressing from pipeline interval/routing pressure. This is not MiniCPM-V/K26.
8. **Failure regime.** Residency loses if state cannot fit with compute/buffers, boundary transfers dominate, or the target has no GDN recurrence. Generic persistent state and fused reuse are prior art.

### Hummingbird — DDR port arbitration and transaction alignment on KV260

Primary sources: [ICCAD 2025 paper DOI](https://doi.org/10.1109/ICCAD66269.2025.11241002) and [author preprint full text](https://arxiv.org/html/2507.03308v1).

1. **Observation.** Earlier KV260 LLaMA2-7B decode reported about 84% theoretical bandwidth use; multiple AXI ports still contend in the Zynq memory controller. FP16 embeddings also occupy a large fraction of a quantized model footprint.
2. **Root cause.** Concurrent port arbitration and row/bank switching from poorly aligned transactions waste DDR bandwidth; a lightly accessed embedding table consumes scarce capacity.
3. **Why prior methods fail.** Adding ports does not achieve aggregate theoretical bandwidth, and keeping all embeddings/weights/KV resident exceeds memory limits for the target model/context.
4. **Decision variable.** Per-port bytes per transaction and column-aligned base address; also embedding residency/offload and GEMV DSP/reduction organization.
5. **Mechanism.** Align four-port transactions to a DRAM column/group-column window; tune BTT; use GEMV activation reuse and a hybrid DSP chain; add GQA-aware buffering; offload embeddings, with direct SD-to-PL transfer avoiding intermediate PS DDR/DMA.
6. **Strongest baseline.** Prior KV260 LLaMA2-7B result at 4.9 tokens/s and 84% bandwidth use, plus unoptimized BTT and embedding-transfer ablations. Conditions differ from Hummingbird's model.
7. **Evidence boundary.** KV260 board deployment of GPTQ W4 LLaMA3-8B and W8 KV reports 4.8 tokens/s at short-context prefill:decode 32:32 and 94% bandwidth efficiency. Embedding-loading falls from 152 ms to 1.5 ms with fast seek plus bypass. This is LLM-only; language embedding-table transfer is not the MiniCPM visual-to-language embedding handoff.
8. **Failure regime.** If the actual K26 trace has no row/port conflict, if transfer is already coalesced, or if embedding setup is not on the online path, these mechanisms cannot improve the request. Generic K26 DDR alignment/bandwidth/offload claims are covered.

### MEADOW — attention intermediate traffic and compressed weight fetch

Primary source: [MLSys 2025 official proceedings paper](https://proceedings.mlsys.org/paper_files/paper/2025/file/259a5df46308d60f8454bd4adcc3b462-Paper-Conference.pdf).

1. **Observation.** At low external-memory bandwidth, OPT prefill repeatedly stores/fetches attention intermediates, while batch-one decode spends most latency fetching weights.
2. **Root cause.** GEMM-style attention materializes intermediate tokens; repeated dense weights exceed low-power DRAM bandwidth.
3. **Why prior methods fail.** Quantization and sparsity reduce bytes or operations but do not alone remove intermediate round-trips or repeated weight values.
4. **Decision variable.** For Q+softmax(QKᵀ)V, choose GEMM or token-parallel/head-sequential (TPHS) by bandwidth/PE count; also choose lossless weight packing and bit packing.
5. **Mechanism.** Pipeline TPHS attention to eliminate intermediate DRAM fetch/store; pack unique values and encode weights compactly; use GEMM where the roofline favors it.
6. **Strongest baseline.** Same architecture's GEMM mode; also ported CTA and FlightLLM settings. The best dataflow depends on external bandwidth and PE count.
7. **Evidence boundary.** Authors evaluate OPT-125M/1.3B and DeiT ViT on ZCU102. At 1–6 Gbps they report up to 2.5x prefill and 1.5x decode reductions versus GEMM, and over 40% end-to-end reduction versus selected prior works. Results are paper-specific.
8. **Failure regime.** At sufficiently high bandwidth/PE count, their study selects GEMM over TPHS. If K26 is compute-bound or dispatch/layout cost dominates, the switch has no payoff. Generic data packing, attention fusion, and movement savings are covered.

### TeLLMe — distinct prefill/decode dataflows for a ternary edge LLM

Primary sources: [FPGA 2026 DOI](https://doi.org/10.1145/3748173.3779191), [full author preprint](https://arxiv.org/html/2510.15926v2), and [author project repository](https://github.com/UCI-CORSA/TeLLMe_FPGA_2026).

1. **Observation.** Edge LLM latency includes prefill as well as autoregressive decode; decode-only design leaves first-token delay. Ternary weights are poorly served by ordinary multiplier DSPs.
2. **Root cause.** Low-bit linear layers mix with FP16/INT8 attention and elementwise stages; prefill and decode differ; KV260 URAM and routing are constrained.
3. **Why prior methods fail.** Earlier embedded LLM accelerators could omit prefill or rely on generic math resources; lookup engines for small perception tasks did not solve LLM weight-buffer interaction and streaming.
4. **Decision variable.** Ternary group size and TLMM parameters G,T,Q,U under LUT/URAM limits; attention path selected separately for prefill and decode.
5. **Mechanism.** Grouped-activation table-lookup matmul, URAM weight-buffer analysis, streaming quant/dequant/elementwise fusion, reversed fused prefill attention, and decode-specific attention. ARM NEON LM head is included in end-to-end timing.
6. **Strongest baseline.** Equal-PE naive attention (14.3 ms vs 7.6 ms at prefill length 128), TLMM variants, and SECDA/LLaMAF edge FPGA comparisons. Cross-model throughput is not directly comparable.
7. **Evidence boundary.** KV260/Vitis 2024.1 at 250 MHz, BitNet 0.73B W1.58A8; up to 143 prefill and 25 decode tokens/s. End-to-end latency is measured with PYNQ Runtime; breakdown is cycle-accurate RTL simulation. Resource report uses 98.5 BRAM and 60 URAM, 94% URAM utilization; ARM LM head adds 9 ms. This is not MiniCPM-V.
8. **Failure regime.** Ternary arithmetic does not transfer to frozen Q4_K/F16 MiniCPM-V without changing model/quality. Static phase-specific buffering/fusion is established prior art; a scheduler must beat that static plan.

### VersaVLM — precision and overlays follow a measured phase split

Primary source: [AICAS 2026 official proceedings page](https://2026.ieee-aicas.org/publication/). Full paper note/page map: [source-checkout evidence](/home/zhiro/research/kv260-vlm/literature/notes/aicas_versavlm.md).

1. **Observation.** For SmolVLM2, many unnormalized attention numerators fall below uniform INT8's first positive value; prefill and decode sit on different compute/memory sides of the phase roofline.
2. **Root cause.** Uniform INT8 destroys small attention values, while one phase mapping misses reuse/bandwidth balance in the other.
3. **Why prior methods fail.** A uniform attention representation loses small values, and one design pays for the wrong compute/memory pattern.
4. **Decision variable.** Attention value encoding and phase-to-overlay transition point.
5. **Mechanism.** Log8 numerator encoding, distinct prefill/decode arrays/memory schedules, and llama.cpp runtime loading of the second bitstream at the phase boundary.
6. **Strongest baseline.** CPU-FP16 is the quality/performance reference. For any shared/single-bitstream candidate, its full two-overlay configuration with switch charged is the direct static control.
7. **Evidence boundary.** KV260/SmolVLM2 with W8A8 prefill and AWQ weights/INT8 KV decode. A 501-token prompt plus 1024 generated tokens reports 350.7 s CPU vs 97.1 s VersaVLM, counting an 803.916 ms switch; OCRBench is 55/120 CPU vs 50/120 FPGA. Not MiniCPM-V.
8. **Failure regime.** If one static phase plan matches the two overlays after transition/CPU/quality costs, no planner is needed; phase specialization and two bitstreams are not novel.

### UniVLM — share hardware across sequential vision and language phases

Primary source: [AICAS 2026 official proceedings page](https://2026.ieee-aicas.org/publication/). Full paper note: [source-checkout evidence](/home/zhiro/research/kv260-vlm/literature/notes/aicas_univlm.md).

1. **Observation.** ViT runs before LLM prefill/decode, so matrix resources are mutually exclusive; materialized MHA/MLP intermediates and separate engines consume resources.
2. **Root cause.** Sequential phases use related matrix/attention hardware, but separate engines duplicate resources and naive order creates storage/reorder traffic.
3. **Why prior methods fail.** Separate engines reserve resources in inactive phases; generic mixed precision with host roundtrips adds latency.
4. **Decision variable.** Shared static/dynamic GEMM assignment and K/V/Q, attention-tile, head, and MLP projection order.
5. **Mechanism.** W5A8 path, time-multiplexed ViT/LLM GEMM blocks, tiled/interleaved MHA, and streamed/interleaved Up/Gate/SiLU/Down.
6. **Strongest baseline.** Separate-engine resource comparison and FP precision quality baseline; sharing ablation isolates hardware savings but excludes system-interface logic.
7. **Evidence boundary.** KV260/SmolVLM2 at 250 MHz reports 24.29 prefill and 14.28 decode tok/s, 4.96 W, and OCRBench/ScienceQA-IMG drops of 3.4/5.9 points. These are author measurements for a different model/quantization.
8. **Failure regime.** If static time-multiplexing/fusion meets MiniCPM-V quality and resource limits, a dynamic scheduler is not justified. Cross-stage sharing and VLM buffer reduction are covered.

### Memory-Centric VLM Deployment — bandwidth and command granularity from the interface budget

Primary source: [AICAS 2026 official proceedings page](https://2026.ieee-aicas.org/publication/). Full paper/result qualification: [source-checkout evidence](/home/zhiro/research/kv260-vlm/literature/notes/aicas_memory_centric_vlm.md).

1. **Observation.** A prefill tile's operand demand is about 40 B/cycle and decode about 129 B/cycle against a theoretical 64 B/cycle four-channel interface; per-tile PS handshakes burden movement.
2. **Root cause.** Decode weight traffic, noncontiguous layouts, fine-grained control, and activation movement exceed useful bandwidth or introduce gaps.
3. **Why prior methods fail.** More MACs cannot fix an interface deficit; tile-by-tile host configuration adds control cost.
4. **Decision variable.** Transfer layout/granularity, overlap depth, activation residency, and dispatch at matrix rather than tile granularity.
5. **Mechanism.** Four AXI reads, double-buffering, tile-major prefill activations, one bulk-loaded decode activation, and hardware-controlled tile loops after a single matrix-level dispatch.
6. **Strongest baseline.** Sequential component ablations and the official AICAS track baseline. The paper says the submitted design retained some GEMMs on APU; its fully offloaded prefill number is from an extended build.
7. **Evidence boundary.** KV260/SmolVLM2 at 300 MHz; track result reports 50.452 prefill and 38.552 decode tok/s, with separate extended-build GEMM measurements. The distinction must be preserved.
8. **Failure regime.** If measured K26 is not bandwidth/control limited, or a best static matrix-level movement/fusion plan ties, no planner increment exists. Generic PS–PL movement, overlap, and matrix dispatch are covered.

### GLITCHES — state transfer and instruction aggregation across GPU/FPGA

Primary source: [HPEC 2024 conference paper PDF](https://ieee-hpec.org/wp-content/uploads/2024/09/112.pdf). Measurement qualifications: [source-checkout evidence](/home/zhiro/research/kv260-vlm/literature/notes/p1_followup_20260923.md).

1. **Observation.** GPU-prefill/FPGA-decode pays KV transfer and many small weight/quantization-metadata instructions.
2. **Root cause.** KV crosses GPU to host to FPGA over PCIe; dynamic HBM management and fine-grained commands add scheduler overhead.
3. **Why prior methods fail.** Kernel-only comparisons omit cross-device state movement and instruction-scheduler cost; late HBM allocation can fragment.
4. **Decision variable.** Offline reserved HBM addresses, per-layer KV-transfer overlap, and small-load aggregation size.
5. **Mechanism.** Reserve state storage before runtime, overlap KV prefetch, and merge small loads without claiming fewer total bytes.
6. **Strongest baseline.** Measured transfer comparisons and simulated GPU-only/multi-FPGA deployment; the paper distinguishes measured transfers from simulated FPGA/system performance.
7. **Evidence boundary.** GPU LLaMA2-7B FP16, U280 about W4A8, PCIe and HBM. KV transfer was measured 50 times; FPGA kernel and multi-card results are cycle-accurate/system simulation. Not physical K26 VLM evidence.
8. **Failure regime.** If K26 PS–PL handoff has no transfer/dispatch stalls or static batching removes them, the mechanism does not transfer. Phase handoff and small-command aggregation are prior art.

### LUT-LLM — explicit channel/port planning in one fixed design

Primary sources: [FCCM author preprint full text](https://arxiv.org/html/2511.06174v2) and [author repository](https://github.com/LUT-FPGA/LUT-LLM). See [source-checkout follow-up note](/home/zhiro/research/kv260-vlm/literature/notes/p1_followup_20260923.md).

1. **Observation.** Aggregate peak bandwidth hides per-port/channel demand; lookup computation may stall on HBM contention despite enough arithmetic throughput.
2. **Root cause.** Lookup tables, weights, activations, and KV compete for independently addressable HBM resources and buffers.
3. **Why prior methods fail.** A single GB/s number or fixed assignment hides local contention; arithmetic reduction does not create ports.
4. **Decision variable.** Lookup representation and HBM channel map, plus phase mode and temporal buffer sharing.
5. **Mechanism.** One V80 design handles prefill/decode, uses 2D lookup/dataflow attention, temporally shares buffers, and assigns channels to tables, weights, input, output, and KV.
6. **Strongest baseline.** GPU comparisons and FPGA configurations in its evaluation. Its public artifact recipe derives some end-to-end estimates from RTL simulation cycles and a latency calculator, not all direct board measurements.
7. **Evidence boundary.** Author preprint/repository use co-quantized Qwen3 1.7B on V80 HBM. No KV260 or frozen MiniCPM-V result; model training, quality, memory and HBM topology differ.
8. **Failure regime.** If K26 has no measured port contention or the best static channel/buffer map ties, adaptive planning adds no evidence. Generic dual-phase and port-aware allocation claims are covered.

## Cross-paper conclusion

- **Phase and shape:** VersaVLM and TeLLMe separate prefill/decode; TRINE switches PE modes at runtime; ReCoVLM normalizes retained tokens to fixed downstream lengths; Hummingbird tunes aligned transfers.
- **Traffic and intermediate storage:** MEADOW, StreamTensor, UniVLM, and Memory-Centric VLM Deployment cover packed weights, streaming/fusion, FIFO/layout, shared engines, and matrix-level transfer control.
- **State and placement:** ReCoVLM uses static sink/ring storage and bank-group expert mapping; Persistent-State Dataflow keeps recurrent state resident; LUT-LLM and Hummingbird quantify port/channel behavior; older LCMM/DNNK covers lifetime reuse.
- **Control overhead:** GLITCHES aggregates small loads; Memory-Centric VLM Deployment uses matrix-level dispatch; TRINE overlaps ready DAG branches. Generic command replay/batching is high-risk.

These findings eliminate generic method claims. They do not establish that the same mechanism has the same cost or best parameters for MiniCPM-V/KV260. The read-only checkout has MiniCPM-V host traces, post-processor image-shape logs, arithmetic padding screens, and source-level selector visibility, but no board VLM execution, physical DDR traffic, actual PS–PL transfer, PL cycle trace, or physical buffer lifetime. Thus no request-specific K26 failure regime is established. A contribution requires a distinct decision variable that beats an equally tuned static plan after full-request and quality costs.

## Local evidence basis

Project facts above are bounded by the verified source snapshots in the coordinator checkout:

- [Existing falsifiable-hypothesis memo](/home/zhiro/research/kv260-vlm/literature/kv260_vlm_falsifiable_hypotheses_20260923.md).
- [Source-access ledger](/home/zhiro/research/kv260-vlm/literature/source_access.md).
- [Current project status](/home/zhiro/research/kv260-vlm/status/PROJECT_STATUS.md), including P1 in progress, no board inference, and P3 NO_GO_NOW.
- [Prior-art matrix](/home/zhiro/research/kv260-vlm/literature/prior_art_matrix.csv), including LCMM/DNNK, AICAS VLM papers, StreamTensor, ReCoVLM, GLITCHES, and LUT-LLM.
