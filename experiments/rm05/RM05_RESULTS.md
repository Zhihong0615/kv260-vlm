# RM05 — Strong Static Compute Baseline and Vision Operator Selection

Date: 2026-09-24
Decision: **`GO_K16_OR_HIGHER_STATIC`**, narrowly for the measured FFN-down shape; this is a feasibility decision, not a novelty claim.
No bitstream was loaded. No PS–PL or DMA measurement is claimed.

## 1. Corrected K16 `ffn_up-0`

The actual tensor is `K/M/N = 1152/4304/1120` (`F16 weight × F32 activation → F32 output`). C-sim passed on a real tensor 16×32 output tile: max absolute error `7.15e-7`, RMSE `1.55e-7`, cosine similarity `0.999999999999982` (60/512 values bitwise equal).

| Metric | Corrected K16 result |
|---|---:|
| Full-shape HLS cycles | 197,670,886 |
| Compute-loop II | 5 (`VITIS_LOOP_147_10`) |
| Inferred FP32 multipliers | 52 |
| HLS estimated Fmax | 265.32 MHz |
| HLS resources | 181 DSP, 72,847 LUT, 59,910 FF, 54 BRAM18K, 24 URAM |
| OOC post-route timing | WNS +0.471 ns at 5 ns target; 0 failing setup endpoints |
| OOC WNS-derived Fmax | 220.80 MHz (equivalent period 4.529 ns; approximate) |
| OOC post-route resources | 181 DSP, 55,250 LUT, 54,622 FF, 23.5 BRAM tiles, 24 URAM |
| Five-call projected compute at routed Fmax | 4.476 s |
| Board CPU `ffn_up-0`, five calls | 7.156 s |
| CPU / FPGA compute-only margin | 1.60× |

The route is out-of-context, uses a 5 ns virtual clock, and has no PS/DDR path constraints. Its worst path is a compute-FSM control register to an FP32 adder input; the 4.524 ns path delay is 87% routed net delay. Vivado reports `HD.CLK_SRC` unset, so the slack-derived frequency is only a feasibility estimate. At a 1.5× end-to-end target, the five-call boundary budget is just **0.294 s total** (58.8 ms/call); this shape is compute-competitive but boundary-sensitive.

## 2. Correctly relabeled K16 `ffn_down-0`

The old RM03 `K/M/N = 4304/1152/1120` K16 result is the real `ffn_down` shape. Direct timing from the completed QID 37804 board request gives five calls totaling **20.628 s**. The individual calls were `4.116, 4.110, 4.179, 4.108, 4.115 s` (median `4.115 s`).

Existing K16 evidence for this exact shape is 164,188,802 full-op cycles, II=5, 52 FP32 multipliers, 182 DSP, 72,918 LUT, 59,980 FF, 54 BRAM18K, and 40 URAM. Its OOC route has WNS +0.225 ns at 5 ns, or approximately 209.4 MHz. Five routed-frequency compute calls project to **3.920 s**, a **5.26× compute-only margin** over the measured CPU calls. A 1.5× end-to-end target still permits up to 9.832 s total boundary cost across those calls. This is the strongest measured offload opportunity in this round. A real `ffn_down` tensor numerical check remains required before integration.

## 3. KV260 request and resource record

- Request: QID `37804`, four A53 threads (`-t 4 -tb 4`), CPU-only, no warmup, no PL.
- Image: `58d543df7eab2bfc.jpg`, SHA-256 `3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f`.
- Model SHA-256: `8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773`.
- mmproj SHA-256: `ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293`.
- llama.cpp/MTMD source commit: `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`.
- Instrumented AArch64 board CLI SHA-256: `b53a6f74bfa471dcd40e71a2f506768951d621b7ac691dc3efbd6bf3d598f70d`.
- Process wall time: **668.35 s**; answer `G` (matches the frozen host answer). Prompt-eval time `648.023 s`; decode `0.919 s`.
- `/usr/bin/time`: peak RSS `1,872,616 KiB` (about 1,829 MiB), no swap, exit 0. CPU frequency sampled at 1.333 GHz on all four cores. Temperature: `UNKNOWN` (no thermal-zone sensor exposed).
- Memory: MemAvailable was about 3.29 GB before and 3.32 GB after; minimum observed during inference was about 1.95 GB. `CmaFree` was about 599,060 KiB before, fell to 21,876 KiB during CPU inference, and recovered to 552,028 KiB afterward. Despite the transient CMA reduction, the full request completed.
- The request had five image/vision batches: encoder time summed to 590.515 s; image-decode time summed to 48.785 s; combined vision encode+decode was **639.300 s**.

The board trace timed 845 selected MUL_MAT calls across 15 exact `(K,M,N,dtype)` shapes in seven operator families. These selected shapes account for 1,195.46 GMAC, or 99.25% of the 1,204.54 GMAC in the existing QID 37804 vision coverage trace. Summed target-node time is 583.783 s (91.3% of measured vision encode+decode). These are single-request callback intervals, not a multi-run statistical estimate or a PS–PL boundary measurement.

## 4. Board-measured vision operator Pareto

`time/MAC` is the aggregate elapsed-node interval divided by MACs, in ns/MAC. `Vision share` uses the measured 639.300 s encode+decode interval. The aggregate combines the listed shape variants; use the per-shape CSV for exact dimensions.

| Family | Calls | MAC | Board CPU time | ns/MAC | Vision share |
|---|---:|---:|---:|---:|---:|
| FFN down | 140 | 360.96 GMAC | 274.254 s | 0.760 | 42.90% |
| FFN up | 140 | 444.26 GMAC | 171.056 s | 0.385 | 26.76% |
| Attention output projection | 140 | 96.61 GMAC | 59.995 s | 0.621 | 9.38% |
| Q projection | 140 | 96.61 GMAC | 26.243 s | 0.272 | 4.10% |
| V projection | 140 | 96.61 GMAC | 25.389 s | 0.263 | 3.97% |
| K projection | 140 | 96.61 GMAC | 25.331 s | 0.262 | 3.96% |
| Patch embedding | 5 | 3.79 GMAC | 1.516 s | 0.400 | 0.24% |

A notable measured shape effect: `ffn_down-0` and `ffn_up-0` each perform 5.553 GMAC per call, but their five-call board times are 20.628 s versus 7.156 s (4.126 s versus 1.431 s/call, about 2.88× slower for down). That makes the exact down orientation a much stronger CPU opportunity than MAC counts alone predict.

## 5. CPU-vs-FPGA opportunity

| Operator shape | Board CPU evidence | Existing K16 compute evidence | Classification |
|---|---|---|---|
| FFN down `K/M/N=4304/1152/1120` | `ffn_down-0`: 5 calls, 20.628 s; the 35-call request-wide shape costs 145.907 s | Exact-shape K16: 164.189M cycles/op, ≈209.4 MHz OOC, 3.920 s/5 calls | **HIGH_VALUE_OFFLOAD** |
| FFN up `1152/4304/1120` | `ffn_up-0`: 5 calls, 7.156 s; 35-call shape costs 50.163 s | Corrected K16: 197.671M cycles/op, 220.8 MHz OOC, 4.476 s/5 calls | **MARGINAL**, only 0.294 s boundary budget for 1.5× |
| FFN down `4304/1152/280` | 100 calls, 104.218 s | No exact-shape HLS/route result | **MARGINAL**, synthesize this shape before generalizing K16 coverage |
| FFN up `1152/4304/280` | 100 calls, 36.277 s | No exact-shape HLS/route result | **MARGINAL**, exact-shape result missing |
| Attention output `1152/1152/{1120,280}` | 140 calls, 59.995 s total | No exact-shape K16 result | **MARGINAL**, exact-shape result missing |
| Q/K/V `1152/1152/{1120,280}` | 420 calls, 76.962 s total | No exact-shape K16 result | **MARGINAL**, exact-shape result missing |
| Merger FFN up `4608/17216/280`; down `17216/1152/280` | 5 calls each, 84.616 s and 24.129 s | Current synthesized HLS configs do not cover these extreme K/M shapes | **NEEDS DIFFERENT SHAPE CONFIGURATION** |
| Patch embedding `588/1120/1152`, F16×F16→F32 | 5 calls, 1.516 s | Different activation precision; no measured benefit | **CPU_KEEP** |

Only exact-shape HLS/Vivado results are used for projected FPGA times. No peak-GOPS extrapolation is used. The family totals show FFN down/up dominate vision time, but do not imply the existing K16 build covers the N=280 or merger shapes.

## 6. RM05 decision and next gate

**Decision: `GO_K16_OR_HIGHER_STATIC`.** Continue toward a minimal standalone PL feasibility test using the exact `ffn_down` `4304/1152/1120` shape. The down result has enough compute-only margin to justify boundary measurement; the corrected `ffn_up` result is a secondary candidate only if total five-call boundary cost can be kept below about 0.294 s for a 1.5× end-to-end target.

Before integration, capture and compare a real `ffn_down` tensor numerically, then measure its DMA/submit/sync/layout cost on the same call contract. Keep N=280 and merger families unclaimed until exact HLS/Vivado results exist. No bitstream or novelty claim follows from this feasibility decision.

## Artifacts

- [`q37804_vision_family_summary.csv`](results/q37804_vision_family_timing/q37804_vision_family_summary.csv)
- [`q37804_vision_family_cpu_timing.csv`](results/q37804_vision_family_timing/q37804_vision_family_cpu_timing.csv)
- [`q37804_vision_operator_call_timing.csv`](results/q37804_vision_family_timing/q37804_vision_operator_call_timing.csv)
- [`q37804_optrace.jsonl`](results/q37804_vision_family_timing/q37804_optrace.jsonl)
- [`stderr.log`](results/q37804_vision_family_timing/stderr.log), [`stdout.log`](results/q37804_vision_family_timing/stdout.log), [`resource.txt`](results/q37804_vision_family_timing/resource.txt)
- Corrected-up K16 HLS/top-loop/C-sim and Vivado reports: [`hls_top_csynth.rpt`](results/k16_ffn_up_corrected_shape/hls_top_csynth.rpt), [`hls_compute_loop_csynth.rpt`](results/k16_ffn_up_corrected_shape/hls_compute_loop_csynth.rpt), [`hls_csim.log`](results/k16_ffn_up_corrected_shape/hls_csim.log), [`timing_post_route.rpt`](results/k16_ffn_up_corrected_shape/timing_post_route.rpt), [`utilization_post_route.rpt`](results/k16_ffn_up_corrected_shape/utilization_post_route.rpt)
