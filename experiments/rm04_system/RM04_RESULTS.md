# RM04 — Dynamic8 boundary and coverage results

## Decision

**C — `STOP_CURRENT_PL_PATH` for the current Dynamic8 `ffn_up-0` mapping.** A board CPU capture measured the five target calls at 7.158 s total. Corrected-shape Dynamic8 requires 417,605,286 scheduled cycles per call: 10.440 s for five calls at the 200 MHz HLS target, and 11.135 s at the full-system routed clock of 187.512 MHz. The latter is a schedule-derived optimistic estimate, not a board measurement, and is already 1.56× the direct CPU time before DDR stalls or PS–PL boundary cost. Zero-overhead CPU break-even would require at least 291.71 MHz. This misses the old 13.6 s MAC-proportional CPU proxy, but that proxy is superseded by direct board timing of the exact five nodes. Do not load this image to the board. The project safety runbook still lacks a verified physical recovery route and exact known-good rollback target.

| Five-call comparison | Time | Interpretation |
|---|---:|---|
| Exact target on CPU, 4 A53 threads | 7.158 s | Direct KV260 timing, with GGML scheduler dispatch/sync in each bracket |
| Dynamic8 at integrated routed clock | 11.135 s | Optimistic HLS schedule extrapolation; excludes actual DDR stalls and CPU↔PL boundary |
| Allowed boundary budget vs exact CPU | −3.978 s | No nonnegative DMA/submit/layout cost can make this mapping break even |
| Old MAC-proportional CPU proxy | ≈13.61 s | Approximation from whole-vision time; would leave 2.47 s for boundary only if taken alone |

This stop applies to the current single-op Dynamic8 mapping. The shape coverage map identifies larger families worth re-evaluating only with a faster compute organization and new per-family CPU measurements; it does not justify integrating the current image.

## Real KV260 CPU request and tensor capture

QID 37804 used the staged MiniCPM-V 4.6 Q4_K_M model, F16 mmproj, image SHA-256 `3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f`, and the pinned llama.cpp/MTMD source commit `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`. The user-visible answer was `G`, matching the prior CPU reference.

| Measurement | Result |
|---|---:|
| CPU threads | 4; process averaged 382% CPU |
| Full request wall | 668.86 s |
| Runtime prompt eval | 652.65 s / 403 tokens |
| Five MTMD vision encode spans | 595.44 s total |
| Five isolated `ffn_up-0` target spans | 7.158 s total; 1.408–1.527 s each |
| Peak RSS | 1,876,828 KiB |
| MemAvailable before / after | 3,285,096 / 3,289,528 KiB |
| CMA free before / after | 587,680 / 598,940 KiB |
| Swap | 0 |
| Frequency during request / temperature / TTFT | UNKNOWN |

The target timings bracket the real GGML nodes with the runtime scheduler callback and include CPU graph dispatch/synchronization. They are direct board measurements for the five calls, unlike the previous MAC-proportional 13.61 s proxy. The capture CLI adds a synchronization at each selected boundary; the five MTMD encode spans total 595.44 s versus the earlier uninstrumented 590.35 s, so the capture run is slightly instrumented.

At the first target occurrence, the callback verified the immediately preceding `ffn_inp_normed-0` boundary and exact contiguous GGML signature. It saved the actual board CPU tensors:

| Tensor | GGML shape | Bytes | SHA-256 |
|---|---|---:|---|
| F16 weight `v.blk.0.ffn_up.weight` | `[1152,4304]` | 9,916,416 | `c9987b77337c39c44a2b97606985c7376fae8db641b28e35010fb3bb7942f0b7` |
| F32 activation `ffn_inp_normed-0` | `[1152,1120]` | 5,160,960 | `67694f913a045603c18971a4bb9312b6c23df7a336b567bf4f94a0b33d08b41b` |
| F32 CPU output `ffn_up-0` | `[4304,1120]` | 19,281,920 | `611eed125bd52f30c1430aae410900d92a2e6adae45e570248e49860d43a5548` |

These binary payloads stay out of Git and are retained locally beneath `experiments/rm04_system/local_tensors/`. The raw process logs, op trace, answer and resource report are likewise local and ignored; their hashes are recorded in the local capture directory.

## Corrected shape and real-tensor C-simulation

The audited runtime tensors establish `K=1152, M=4304, N=1120` for vision `ffn_up-0`. The prior HLS top used `K=4304, output=1152`. That shape instead matches a vision `ffn_down` family (`K=4304, M=1152`); the synthetic macro-tile test did not reveal the label/layout mismatch. RM04 changed the HLS constants and input/output buffer depths to the actual `ffn_up` layout and reran C-simulation and synthesis.

Corrected Dynamic8 HLS result: **417,605,286 cycles**, compute II=1, 16 inferred FP32 multipliers, HLS estimated Fmax 239.52 MHz, 81 DSP, 18,845 LUT, 18,681 FF, 54 BRAM18K, and 24 URAM. Full-operation schedule time is 2.088 s at 200 MHz. The traffic model estimates 1.7405 GB/call (8.703 GB across five calls); it is a schedule-derived port-traffic count, not measured DDR traffic. At the full-system routed clock, schedule-derived throughput is 2.493 GMAC/s and modeled traffic divided by schedule time is 0.782 GB/s; neither is measured board throughput.

Using the real QID 37804 board tensors, HLS C-sim compared a 16×32 tile (512 outputs) against the board CPU output:

| Mapping | Max absolute error | RMSE | Cosine | Bitwise-equal outputs |
|---|---:|---:|---:|---:|
| Dynamic8, same eight-way partial accumulation | 1.1921e-6 | 1.5523e-7 | 0.9999999999999822 | 93 / 512 |
| K16, changed reduction association | 7.1526e-7 | 1.5489e-7 | 0.9999999999999819 | 60 / 512 |

This validates the selected real tile only. Dynamic8 remains the matching-association baseline; K16 has good error on this tile but still is not the board-integrated path.

## Vision operator coverage

The audited QID 37804 trace has 855 vision matmul graph observations: 850 F16×F32→F32 and 5 F16×F16→F32. The Dynamic8 point directly supports contiguous F16×F32→F32 with `K=1152, M=4304, N=1120`.

| Coverage class | Vision MAC share | Four-thread board vision-time proxy |
|---|---:|---:|
| Directly supported at current frozen shape | 16.136% | 95.26 s |
| Same arithmetic datapath, compile-time shape change required | 71.887% | 424.38 s |
| Requires a different datapath | 11.840% | 69.90 s |
| Not worth offloading in this first pass | 0.137% | 0.81 s |

The time column is only a per-family proportional estimate from the request-level 590.348 s board vision timer; no family except the five `ffn_up-0` calls has an isolated board timing. Most parameter-change coverage consists of FFN down/up and attention projections. The different-datapath class includes the K=17,216 merger shapes and F16×F16 patch embedding. Full per-shape rows, call counts, bytes, and nominal MACs are in `coverage/vision_operator_coverage_q37804.csv`.

## PS–PL build and boundary measurements

The KV260 block design contains PS HPM0 AXI-Lite control, three HLS AXI4 memory-mapped masters through SmartConnect to PS HP0 DDR, Dynamic8, and a three-slot AXI Performance Monitor. These masters are the memory mover; this design has no separate AXI DMA IP. Vivado 2024.2 completed implementation, routing, DRC, bitstream generation, and XSA validation for `xck26-sfvc784`.

| Full-system implementation metric | Result |
|---|---:|
| Routed `clk_pl_0` | 187.512 MHz |
| Post-route WNS / TNS | +0.848 ns / 0.000 ns; 0 failing setup endpoints |
| Worst setup data path | 3.868 ns, of which 3.752 ns (97.0%) is routed net delay |
| LUT / device | 24,311 / 117,120 (20.76%) |
| FF / device | 30,229 / 234,240 (12.91%) |
| DSP / device | 81 / 1,248 (6.49%) |
| BRAM tile / device | 24 / 144 (16.67%) |
| URAM / device | 24 / 64 (37.50%) |
| Route errors | 0 |
| Bitstream SHA-256 | `041992089becb6167bafdd1d16b569a20a567de389e8e25b8bf211eb59d474d9` |
| XSA SHA-256 | `4ef820e8457284d211c31904d3ba21a3bbc93a4c850ba0e10cfef8d7b1ef843a` |

The system timing report lists 564 internal endpoints unconstrained due to constant clocks, while reporting all user-specified constraints met. The maximum clock above is the reported routed `clk_pl_0`, not the 200 MHz HLS target. The concise HLS, routed timing, utilization, and route-status reports are archived under `experiments/rm04_system/evidence/` with SHA-256 checksums. Full project files and the generated bitstream remain local under the ignored `build/` directory.

No research bitstream was loaded. Board PL cycles, measured DMA latency/bytes, submit/sync time, CPU packing, effective DDR bandwidth, standalone wall time, and CPU-vs-PL five-call execution therefore remain **UNKNOWN**. The runbook prohibits first load until a physical recovery path and exact known-good rollback target are verified. The measured CPU time is already below the schedule-derived Dynamic8 compute time at the routed clock, so this current mapping does not justify a risky load. This is a compute-floor no-go, not a measurement of PS–PL boundary cost.

## Reproduction inputs

- Corrected HLS sources and real-tensor C-sim: `experiments/rm03_hls_mapping/source/`
- HLS synthesis report: `experiments/rm04_system/evidence/vision_gemm_csynth.rpt`
- System BD additions and build script: `experiments/rm04_system/add_dynamic8_bd.tcl`, `experiments/rm04_system/build_kv260_rm04.tcl`
- Pinned KV260 starter-kit source fetch: `scripts/rm04/fetch_kv260_base.sh`
- Coverage analyzer: `scripts/rm04/build_vision_coverage_map.py`
- Tensor-capture builder and board-run scripts: `scripts/rm04/`
- Pinned base design source: `Xilinx/kria-base-hardware` commit `a722daa4536784a888693299eed46fb2ac0841a3` (local clone under ignored `vendor/`; not a Git dependency of the project)
- Full-system implementation reports: `experiments/rm04_system/evidence/{system_timing_summary_routed,system_utilization_placed,system_route_status}.rpt`
