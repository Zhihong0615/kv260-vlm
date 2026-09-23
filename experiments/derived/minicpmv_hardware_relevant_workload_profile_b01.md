# MiniCPM-V hardware-relevant workload profile (B01)

Date: 2026-09-24
Evidence boundary: existing TextVQA development evidence from a host CPU run and host-only traces. No new traces, board commands, or hardware inference were run for this profile.

## Decision summary

The existing evidence is strong enough to rank which workloads a future K26 experiment should cover. It supports starting with the vision encoder/projector path, then image-embedding prefill; it also gives concrete shape families for a tile sweep and warns that the common image-prefill widths do not by themselves imply a large tail penalty. It does **not** select PE dimensions, tile size, BRAM/URAM capacity, buffer depth, DMA policy, or PS–PL partition: the timing boundary is host-only, matrix counts are graph observations, allocator ranges are host virtual metadata, and there are no measured PL cycles, physical DMA/AXI bytes, or board stalls.

## Evidence classes and population

- **HOST_MEASURED:** the TextVQA dev50 baseline used one fresh host CPU process per original image, Q4_K_M language weights, F16 mmproj, 8 threads, temperature 0, and a 48-token output limit. Its outer process-wall median is 8.558 s, P95 12.548 s, and MMF soft accuracy 0.644 over 50 development requests. This outer wall includes setup/model-load work and is not the online phase-timeline boundary or a KV260 estimate.
- **HOST_MEASURED_PHASE:** three selected development requests (qid 37804, 38299, 35419) have three alternating ordinary/traced process pairs each, with matched answers. The online boundary starts just before media-file read/decode after initialization and ends at request completion. Timed encoder spans combine graph setup, vision, projector, scheduler, and copies; phase medians across requests are not additive.
- **HOST_GRAPH_METADATA / ARITHMETIC_PROXY:** four selected development requests (qid 37804, 37852, 38169, 38299) have three matched graph-metadata traces each. Shapes, graph-node counts, and nominal MAC pairs are recorded; they are not isolated executed-kernel work or time.
- **HOST_VIRTUAL_BUFFER_METADATA:** four requests have complete dynamic offset/extent and view-source coverage, plus independently recomputed range and graph-window summaries. These are host allocator offsets and inferred graph-order relationships, not physical allocations, last-use events, DDR traffic, PL memory, or safe-reuse proof.
- **ANALYTICAL_FROM_HOST_TRACE:** the N-tile screen rounds selected image-prefill widths to candidate column tiles. It is an occupancy calculation, not a tile timing result.

## Recorded request mix

The existing host dev50 log has seven ordered post-processor image-token patterns. Counts total 50; exact pattern availability before dispatch is not established. The four requests with allocator traces cover three of these patterns.

| Ordered image-token pattern | dev50 requests | Existing allocator-traced examples |
|---|---:|---|
| `[60,64,64]` | 1 | 38169 |
| `[66,64,64]` | 4 | 38299 |
| `[60,60,60,60,60]` | 1 | none |
| `[63,63,63,63,63]` | 16 | none |
| `[70,70,70,70,70]` | 22 | 37804, 37852 |
| seven `63` values | 1 | none |
| `[64,70,70,70,70,70,70]` | 5 | none |

The four patterns without allocator shape traces have deterministic development examples 35950, 34609, 35419, and 35005 in the inventory. Qid 35419 already has a phase-timing trace with seven encoder calls, but not the four-request matrix/allocator metadata. Check image identity and runtime metadata before selecting any as a later shape-coverage trace. These counts are development-set frequencies, not deployment probabilities or held-out results.

## Host timing that sets investigation order

| qid | Encoder calls in the trace | Online input→done median (ms) | Combined vision + projector span median (ms) | Image-embedding prefill median (ms) | Text-prefill median (ms) |
|---:|---:|---:|---:|---:|---:|
| 37804 | 5 | 7,194.450 | 6,082.813 | 828.958 | 202.142 |
| 38299 | 3 | 3,820.930 | 3,198.225 | 445.782 | 153.298 |
| 35419 | 7 | 8,583.712 | 7,246.250 | 1,017.358 | 227.707 |

These host phase measurements put vision plus projector first for follow-up timing and image-embedding prefill second. They do not distinguish vision compute from projector, graph setup, upload, scheduler, or output copy. Text prefill is smaller in these three selected online traces. The timeline note does not provide a comparable isolated per-op decode phase. Do not treat `n` of three per qid as a population distribution.

## Matrix shape and nominal-work inventory

Run order below is A–D = qid 37804, 37852, 38169, 38299. Counts and work are host graph observations from three traces per request; nominal MAC pairs are an arithmetic proxy from recorded dimensions and batch axes.

| Phase | `MUL_MAT` graph nodes A/B/C/D | Zero-extent nodes A/B/C/D | Nominal MAC pairs (B) A/B/C/D |
|---|---:|---:|---:|
| Vision encoder | 855/855/513/513 | 0/0/0/0 | 1204.542/1204.542/647.011/667.661 |
| Image-embedding prefill | 935/935/561/561 | 5/5/3/3 | 174.165/174.165/93.552/96.537 |
| Text prefill | 1122/1122/748/748 | 5/5/3/3 | 26.628/25.135/23.642/23.144 |
| Token decode | 187/2431/374/187 | 0/0/0/0 | 0.752/9.772/1.503/0.752 |

Representative native GGML shape families, in recorded `M×N×K` order:

| Phase / output | Observed shapes and graph-node counts per request |
|---|---|
| Vision / `node_3` | A/B: `1120×1152×588` (5); C: `960×1152×588` (1), `1024×1152×588` (2); D: `1024×1152×588` (2), `1056×1152×588` (1) |
| Vision / `ffn_up-0` | A/B: `4304×1120×1152` (5); C: `4304×960×1152` (1), `4304×1024×1152` (2); D: `4304×1024×1152` (2), `4304×1056×1152` (1) |
| Image prefill / `ffn_up-0` | A/B: `3584×70×1024` (5); C: `3584×60×1024` (1), `3584×64×1024` (2); D: `3584×64×1024` (2), `3584×66×1024` (1) |
| Token decode / `ffn_up-0` | A/B/C/D: `3584×1×1024` with 1/13/2/1 graph-node observations |

The aggregate vision trace is predominantly F16-weight × F32-activation → F32-output matrix metadata (850 nodes in the one-request export), with five F16 × F16 → F32 observations. Language-side matrix metadata uses mixed Q4_K/Q6_K weights and F32 activations. The selected image-prefill `ffn_up-0` family is Q4_K × F32 → F32. These dtypes identify candidate arithmetic and interfaces; they do not establish the FPGA numeric implementation or conversion cost.

### Image-prefill tile control

Across the four audited requests, the selected Q4_K image-prefill `ffn_up-0` family has 16 graph-node observations: N=60 (1), 64 (4), 66 (1), and 70 (10), with M/K fixed at 3584/1024. If padded columns execute, the existing analytical screen reports:

| N tile | Useful-column occupancy | Padded/useful MAC-pair ratio |
|---:|---:|---:|
| 8 | 97.302% | 1.0277× |
| 16 | 90.167% | 1.1091× |
| 32 | 78.634% | 1.2717× |
| 64 | 62.616% | 1.5970× |
| 128 | 52.832% | 1.8928× |

This makes fixed T=8 an essential static null control for any width-64 tail hypothesis: N=60/64 round to 64 and N=66/70 to 72. The arithmetic screen omits loop/setup cost, predication, DMA, and utilization; it cannot choose a fast tile. Runtime source makes N visible before backend allocation, so shape-keyed static dispatch is also a strong control.

## What buffer records do and do not establish

The four allocator-comparison requests each have three traced and three ordinary processes, all matching frozen answers. Dynamic offset/extent and view-source coverage is 1.000 for all compared phases; raw recomputations found no bounds or view-source discrepancy. The summarized host graph-local dynamic peaks are 38.12–41.70 MiB for vision and 5.76–6.11 MiB for image prefill; deduplicated allocator-range union peaks are 25.81–28.23 MiB and 5.51–5.84 MiB, respectively. These labels describe host virtual-buffer records only. Inferred same-slot overlaps occur at an unobserved consumer boundary, and true last-use events remain unknown. They cannot size PL local memory, demonstrate legal reuse, set a double-buffer depth, or be relabeled as DDR bytes.

The traces therefore justify making buffer/lifetime instrumentation a priority if a PL boundary is later built, but they do not support a buffer allocation decision today. The PS–PL boundary also remains unresolved: host public-call spans combine vision/projector work and output copy; there are no physical handoff byte counts, DMA timing, command counts, synchronization gaps, AXI stalls, or producer/consumer overlap measurements.

## Reproducibility and frozen inputs

The source checkout is `/home/zhiro/research/kv260-vlm`, read-only for this task. The exact nine brief inputs were verified against `/home/zhiro/research/kv260-vlm-orchestration/orchestration/source_snapshots/TASK_B01.sha256`; all returned `OK`.

| Frozen source input | SHA-256 |
|---|---|
| `status/PROJECT_STATUS.md` | `4b9d21165f74ae43a5ad01103762857bc5d36c2819a1e2d252db7ea07a23c802` |
| `status/go_no_go.md` | `16c10d283170670466fb69f54f324d76c3fdfbdd61d52bc46585bcb403038738` |
| `literature/kv260_vlm_falsifiable_hypotheses_20260923.md` | `bc5d15f8a5d9c5e8490e19ebfc02bfbf3be92ceae1143a8bcce326b67336f55d` |
| `experiments/derived/textvqa_dev50_visual_workload_inventory_ANALYSIS_NOTE.md` | `70ab778e6b844ddb6ec1f3be6d8dfe7f7cbfe76507b6f5bb30b70b453b20a4ac` |
| `experiments/derived/textvqa_matmul_shapes_four_request_host_audited1_ANALYSIS_NOTE.md` | `fee2b6d63b0854d8396dff390fafdf4a8509943cd8c69949c09c4ced0675d056` |
| `experiments/derived/textvqa_allocator_metadata_four_request_comparison_audited4_ANALYSIS_NOTE.md` | `25385c95503869f4a15a1c38f900a3434c80659d34816d37e463ae256e101b41` |
| `experiments/derived/textvqa_phase_timeline_three_request_comparison_and_raw_audit.md` | `f696c6774e86ce89ff9904101fb5b61cfea2e623e5bec64be3b78821bb469c75` |
| `experiments/derived/host_phase_timeline_boundary_spec.md` | `21e96d93ddb943f83b97afafe9ddbb70d5213db434ca2c0ba3126d4b7c85a8e7` |
| `experiments/derived/minicpmv_image_prefill_ffnup_n_tile_padding_screen_round01.md` | `f76a35f3552d491c74109d33270873b7617fa8d0f17060786f8fd09894663c98` |

Additional exact provenance recorded by those inputs: dev50 source-run SHA-256 `d92fa666e25ad8fb2b9e06d03c806cda890319664bed4fc503f1837bcf066050`; dataset-manifest SHA-256 `62c32317029e40895ffd8e476e8a845416dac9d1d9490dfd6efb5f28a4374962`; visual inventory script SHA-256 `004b5fb22014b87b10ba881b13610c04077a756de4e02c3733b55354ef3666e0`; audited matrix inventory SHA-256 `d7ff1e08955e4b8d3b0598f957ecbbdbf970da01055190ad5c79270712ef4082`; tile-screen script SHA-256 `6c23e7cb4c5d6595cda115869a9e47ba0505f017fcb8434b9f17ce34e7640431`; copied phase-tracer source SHA-256 `913eac0c6f943925a5eb1f3c4cad279bd8d29f00215708355e1b53bee32960fc`; and tracer binary SHA-256 `53b10837fb0fc7ce3a1fe2291a6ec0d3b62ddeffc2dfbc39b53dfc6a1205d09a`.

Reproduce this profile by verifying the frozen manifest, then recomputing the comparisons directly from the nine frozen notes: use the dev50 pattern counts; preserve A–D run order in the matmul note; compare per-request online medians with phase medians without summing across requests; and round each of the 16 N observations by `ceil(N/T)·T` for the tile screen. No raw input was modified or copied into this branch. The profile calculations are descriptive; they do not require a new trace or a hardware-specific assumption.

## Top hardware-relevant workloads

1. **Vision encoder plus projector, first timing/partition priority.** The three selected host online traces show combined spans of 3.20–7.25 s, with 3 or 5 or 7 encoder calls. The four graph-traced requests show large F16 matrix families, including vision `ffn_up-0` N values 960/1024/1056/1120 and M/K 4304/1152, plus a fixed `node_3` family around N=960–1152. These records are strong enough to select shape coverage and make vision/projector the first end-to-end stage to measure. They do not identify K26 throughput, project-vs-vision share, PE aspect ratio, or tile.
2. **Image-embedding prefill `ffn_up-0`, first tile-shape falsification.** Four audited requests give 16 Q4_K graph observations at N=60/64/66/70, M/K=3584/1024; the dev50 inventory shows both repeated 5×70 and mixed 7-group patterns. Include T=8, a tuned larger tile, and a fixed two-shape/bucket control before attributing costs to T=64 padding. This is shape/tile prioritization evidence, not a speed claim.
3. **Repeated image/crop batches, buffering and DMA priority.** Existing requests cover 3/5/7 ordered encoder calls and seven token patterns. They are sufficient to define coverage cases—including `[64,70,70,70,70,70,70]`—for future buffer-capacity, reuse, and DMA tests. Post-processor token logs do not establish crop identity, independent executed work, repeated-weight DDR reads, physical lifetime, or whether PS–PL can stream the producer/consumer boundary.
4. **Text prefill and token decode, lower initial PL priority but keep CPU fallback.** Four-request arithmetic proxies show much smaller nominal work than vision/image-prefill; decode graph counts vary with request output (1/13/2/1 selected `ffn_up-0` observations). These do not establish target latency or justify a decode engine. Keep Q4_K/Q6_K mixed-weight support and CPU fallback in the eventual interface/quality contract; treat LM-head/logits and sampling boundary costs as unmeasured.

## Remaining unknowns ranked by importance

1. **Actual K26 critical path, executed kernels, and attainable acceleration.** This decides which stage should receive PL resources and whether image-prefill tile work matters end-to-end. Existing host timing cannot answer it. Smallest resolving measurement: after the runner/parser, synthetic-ALPHA, owner-window, image, and design-approval gates are satisfied, collect one bounded board trace for one representative 3-group, 5-group, and mixed 7-group request, with phase spans, actual backend/kernel assignments, per-op shape/dtype, end-to-end and first-token time, CPU/PL overlap, and repeatability bounds. Stop before measurement if any gate is missing; stop promoting a candidate if its best static CPU/PL control ties within measured run uncertainty or if its phase is not on the critical path.
2. **True crop/batch semantics and pre-dispatch shape coverage.** This decides whether token width or ordered group count is a valid descriptor key and what shapes a tile/buffer plan must support. Existing token logs are post-processor observations, and raw image dimensions/patterns do not prove pre-dispatch visibility. Smallest resolving host measurement: first audit image identity/runtime metadata for the four already selected patterns without allocator shape traces (35950, 34609, 35419, 35005); qid 35419 already has phase timing but lacks the four-request matrix inventory. Only if the existing files do not answer, capture one metadata-only trace per missing exact pattern with source-image identity, crop order, actual backend graph node, M/N/K, dtype, strides, and batch axes. Stop when each uncovered pattern has one verified shape record; do not infer population timing weights from one request per pattern.
3. **Physical lifetimes, repeated-weight traffic, DMA bytes, and usable on-chip capacity.** This decides single/double buffering, local-memory budget, batch grouping, and whether cross-batch reuse is possible. Host offsets/range unions cannot answer it. Smallest resolving measurement: once a fixed PL implementation exists and board use is authorized, instrument one 5×70 and the mixed 7-group case for per-tensor DMA/AXI read/write bytes, buffer ownership and allocate/free/last-use boundaries, local-store high-water marks after logic reservation, reuse distance, stalls, and whether producer output is copied or consumed in place. Stop reuse/buffering claims if no repeated physical reads or live-range conflict is observed, or if a best static pool/bulk handoff matches within uncertainty.
4. **PS–PL launch, synchronization, and handoff cost.** This decides command granularity, replay/batching, whether to fuse/stream, and which operations should remain on PS. The host public-call spans combine compute and copies; no project adapter or PL submission path exists. Reuse the bounded board trace above to record PS submission, DMA start/end, sync, PL idle gaps/stalls, and handoff bytes at every relevant boundary. Stop command-aggregation work if measured boundary cost is not material to request latency or a tuned static matrix-level dispatch ties.
5. **Representativeness and quality on held-out requests.** Dev50-selected traces establish example shapes, not a deployment distribution; current numeric/quality tolerances and held-out criteria are unfrozen. Once a concrete candidate and controls exist, freeze a held-out set that includes all observed pattern classes, exact preprocessing, output cap, scoring and stop threshold before comparing. Stop if the best candidate fails the frozen quality budget or gains do not exceed uncertainty.

Current source-status blocker: board VLM inference is recorded as paused pending current-SHA parser/runner review, synthetic ALPHA evidence, and an inference-specific owner window. This task did not access the board or change any stage gate.
