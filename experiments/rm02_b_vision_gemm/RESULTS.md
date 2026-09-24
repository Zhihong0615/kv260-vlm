# RM02-B: MiniCPM-V vision GEMM feasibility probe

## Result

The first feasibility kernel is correct under the tested F16→F32 conversion and F32 multiply/accumulate semantics and synthesizes on the KV260 K26 device. The one selected residency/tile-shape change cuts modeled input payload traffic by 19.94% and uses 8 fewer URAMs, but does not improve HLS cycles: both configurations take about 8.896 s at the 200 MHz target. For this kernel, arithmetic/scheduling dominates the transfer lower bounds; tile residency alone is not a performance contribution.

This is host-side HLS/Vivado synthesis only. No bitstream was loaded and no KV260 measurement was run.

## Workload and frozen semantics

- Source evidence: `experiments/derived/minicpmv_hardware_relevant_workload_profile_b01.md`, “Representative native GGML shape families.” For selected qids 37804/37852, `ffn_up-0` has five graph observations each at recorded dimensions `4304×1120×1152`; the profile identifies the dominant vision matrix family as F16 weights × F32 activations → F32 output. The profile is host graph evidence, not a board execution trace.
- Profile SHA-256: `732175e8b58f42a8fe447dd16dfa9579daa13fe0721272a2f8fb7d91291a84c8`.
- Semantic dimensions used here: weight `W[output=1152, reduction=4304]` is IEEE binary16; activation `X[token=1120, reduction=4304]` is IEEE binary32; output `Y[token=1120, output=1152]` is IEEE binary32. Compute `Y[n,o] = Σ_k float32(W[o,k]) * X[n,k]`.
- The HLS datapath expands each half exactly to binary32, forms binary32 products and accumulates in eight interleaved FP32 partial sums before an FP32 reduction. Both configurations use this same code and arithmetic order. C-sim golden compares against a software reference within `1e-3 + 5e-5*|golden|`; the deterministic C-sim inputs yielded zero error across 512 outputs.
- Target: `xck26-sfvc784-2LV-c`, Vitis/Vivado 2024.2, HLS clock constraint 5.000 ns (200 MHz). AXI payload ports are 128-bit weights, 256-bit activations, and 256-bit output. Weight/activation tiles are URAM-backed; output tile is BRAM-backed.
- Total useful work: `4304 * 1120 * 1152 = 5,553,192,960 MAC` (one multiply-accumulate counted as one MAC; 11,106,385,920 FLOPs if counting multiply and add separately).

## Configurations and HLS measurements

| Metric | Static baseline v3 | One tile-residency candidate |
|---|---:|---:|
| Tile (output × token rows) | 16 × 32 | 32 × 16 |
| PE code organization | 4 × 4 | 4 × 4 |
| C-sim | PASS, max abs/rel 0 | PASS, max abs/rel 0 |
| HLS latency | 1,779,196,322 cycles | 1,779,195,962 cycles |
| Time at 200 MHz target | 8.89598161 s | 8.89597981 s |
| HLS estimated clock period | 4.096 ns | 4.096 ns |
| HLS estimated Fmax | 244.14 MHz | 244.14 MHz |
| HLS DSP | 68 | 68 |
| HLS LUT | 28,428 | 26,378 |
| HLS FF | 36,939 | 34,913 |
| HLS BRAM_18K | 102 | 70 |
| HLS URAM | 40 / 64 | 32 / 64 |
| AXI payload widths W/X/Y | 128 / 256 / 256 bits | 128 / 256 / 256 bits |
| Compute-loop achieved II | 5 | 5 |
| Inferred FP32 multipliers in compute pipeline | 4 | 4 |

The 360-cycle delta is 0.0000202% of total latency, below any meaningful performance effect at this scale. HLS reports use the 5 ns target for the absolute time; 4.096 ns is a tool estimate, not a routed clock measurement.

## Traffic, MAC utilization, and roofline

Payload traffic is calculated from the actual macro-tile load/store loops, assuming every requested value reaches the memory interface once per loop execution. It excludes AXI protocol overhead and does not claim measured DDR traffic.

| Payload bytes for complete GEMM | Static 16×32 | Candidate 32×16 |
|---|---:|---:|
| Unique weights (`1152×4304×2`) | 9,916,416 | 9,916,416 |
| Unique activations (`1120×4304×4`) | 19,281,920 | 19,281,920 |
| Weight tile reread multiplier | 35 | 70 |
| Activation tile reread multiplier | 72 | 36 |
| Weight read payload | 347,074,560 | 694,149,120 |
| Activation read payload | 1,388,298,240 | 694,149,120 |
| Output write payload (`1120×1152×4`) | 5,160,960 | 5,160,960 |
| **Total payload** | **1,740,533,760 B (1.621 GiB)** | **1,393,459,200 B (1.298 GiB)** |
| Arithmetic intensity | 3.191 MAC/B | 3.985 MAC/B |

The candidate exchanges twice as many weight reads for half as many activation reads; because activations are twice the byte width, total payload falls by 19.94%. It also halves the local activation tile and doubles the local weight tile; HLS maps this to 32 vs 40 URAMs.

Utilization definitions use the complete operation and reported total cycles:

- 4×4 code-level PE peak: `16 MAC/cycle × 200 MHz = 3.2 GMAC/s`. Utilization is `5,553,192,960 / (16 × cycles) = 19.51%` for both; useful throughput is about `624 MMAC/s` at the 200 MHz constraint.
- HLS actually instantiates four FP32 multiplier operators in the compute pipeline. Relative to that inferred four-multiplier ceiling (`4 MAC/cycle × 200 MHz = 0.8 GMAC/s`), the average is about `78.0%` (`5,553,192,960 / (4 × cycles)`). The achieved inner-loop II is 5. This explains why the source’s nominal 16-output microtile is not a 16-MAC/cycle implementation.

DDR roofline is conditional because no K26 DDR benchmark has been taken. At an assumed sustained aggregate bandwidth of 4.8 GB/s, payload transfer lower bounds are 0.363 s (baseline) and 0.290 s (candidate); at 1.0 GB/s they are 1.741 s and 1.393 s. Even the slower 1.0 GB/s bound is far below the ~8.896 s HLS compute estimate. Thus the current schedule is compute/scheduling-bound under these assumptions; the reduced traffic did not move total latency.

## Vivado synthesis feasibility

Vivado 2024.2 synthesis was run on both HLS-generated RTL with the emitted floating-point IP Tcl files sourced first. No placement or route was run.

| Metric | Static v3 | Candidate |
|---|---:|---:|
| Vivado post-synthesis WNS at 5 ns | +1.612 ns | +1.452 ns |
| Worst reported data-path delay | 3.252 ns | 3.412 ns |
| DSP48E2 | 68 | 68 |
| CLB LUTs | 23,583 | 22,433 |
| CLB registers | 29,708 | 27,641 |
| BRAM tiles | 47.5 | 31.5 |
| URAM | 40 | 32 |

This is synthesis timing, not placed timing. Top-level input/output delays are unspecified. The standalone HLS IP exposes AXI ports directly; the I/O utilization number is not a board pinout feasibility result because a real design connects the AXI ports to the PS/interconnect inside a system wrapper.

## Research decision

**Tile-residency hypothesis for latency: not supported by this probe.** The aspect-ratio change cuts estimated payload 19.94% and URAM by 20%, yet total HLS cycles change by only 360 of 1.779 billion. The tool reports four FP32 multipliers and II=5 in both designs. The measurements indicate that memory traffic is not the limiting factor in this synthesized workload model; the HLS arithmetic schedule is. This rejects a traffic-only performance claim for these two tile shapes, but it does not establish board DDR behavior or end-to-end VLM speedup.

The synthesis data support one immediate next hardware question for the coordinator: inspect why a 4×4 unrolled source microtile maps to four FP32 multipliers and II=5 before proposing a higher PE count. That is a measured static-baseline limitation, not a novelty claim.

## Artifact locations

- Kernel/golden/HLS flow: `vision_gemm.cpp`, `vision_gemm.hpp`, `tb.cpp`, `run_hls.tcl`.
- Vivado post-synthesis flow: `run_vivado_post_synth.tcl`.
- Legal frozen HLS reports: `reports/baseline_static_v3_m16_n32_csynth.rpt`, `reports/tile_residency_candidate_m32_n16_csynth.rpt`; original low-efficiency first-round report remains `reports/baseline_m16_n32_csynth.rpt` and was not overwritten. The reviewed intermediate `baseline_rev1` report is retained as `reports/baseline_rev1_m16_n32_csynth.rpt`.
- Vivado reports: `reports/vivado_baseline_static_v3_m16_n32/` and `reports/vivado_candidate_m32_n16_ipgen/`.
- Full tool console logs and generated projects are retained under `reports/` for audit/reproduction.
