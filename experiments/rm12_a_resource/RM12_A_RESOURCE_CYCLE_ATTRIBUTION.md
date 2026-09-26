# RM12 Worker A — RM10 FFN-down resource and cycle attribution

## Scope and revision lock

This report uses the **RM10 corrected fixed10 engine**, source commit `3602eafa7de5cee187b79f8e28c186a19f6f6133`, source SHA-256 `31a7b26f9bf28c0ad57892184ed30b42126162111fe4c4bda82aa7847754319a`, IP component SHA-256 `fae7fde4af5b3f5a1237d5e7717ea97622a9a8c6107ba96c97bfe6bb19feda56`, and board `.bit.bin` SHA-256 `722387cc80b345f0b7b29bdffe61911707cf12c5c25e42867d339b4a0c6fb5d7`. The RM10 board driver's frozen identities match the corrected route package. PL0 was constrained to 100 MHz and measured at 99.999 MHz on board.

The exact FFN-down shapes are `K/M/N=4304/1152/1120` for layer 0 and `4304/1152/280` for layers 13 and 26. RM11's available board APM records are **FFN-up**, `K/M/N=1152/4304/{1120,280}`, on a different shared-engine component and bitstream. The RM11 records are retained as context in the CSV but are not a matched comparison; there are no RM11 down APM rows in this evidence set.

Use the corrected ten-bank report set at [`RM10_CORRECTED_ROUTE_RESULTS.md`](../rm10_route/RM10_CORRECTED_ROUTE_RESULTS.md) and `experiments/rm10_route/evidence/corrected_candidate/`. The older `experiments/rm10_route/RM10_ROUTE_RESULTS.md` and `evidence/full_system/` describe the superseded five-bank invalid candidate, so their utilization numbers do not identify the board-tested RM10 image.

## Arithmetic and operator map

The source widens every F16 weight to F32 using an inlined, bit-level `half_to_float` routine and then multiplies it by an F32 activation. For a 4x4 output group, issue-4 schedules 64 products per K group. The HLS binding evidence maps **64 generic F32×F32→F32 multipliers**, each at 3 DSP48E2, with latency 4: 192 DSP48E2 total. It does not map a narrower half-precision product operator. HLS does not report a standalone conversion module or conversion area; the inlined sign/exponent/fraction handling is mixed into expression, mux, and surrounding logic totals. Its separate resource cost is therefore **UNKNOWN**.

The 16 output lanes each keep ten FP32 temporal partial sums (160 FP32 accumulator cells in the local 4x4 group). The K-loop has 16 recurrent F32 adders, latency 7. The fixed final reduction maps 48 additional F32 adder instances; together, the compute has 64 mapped F32 adders at 2 DSP48E2 each (128 DSP48E2). Thus the named FP32 arithmetic operators account for 320 DSP48E2; the HLS top reports 323 DSP48E2 including helper/stage operators. The binding file and helper reports identify 64 FP32 multiplier instances and 64 FP32 adder instances; this count is not inferred from source MAC count alone.

The K-group loop trips 1,076 times, achieves II=1, and reports 1,109 loop cycles / 1,077-cycle interval; the helper latency is 1,111 cycles. The ten-bank dependence is explicitly true at distance 10. These HLS schedule figures describe the inner group, not board PE-active time or the full measured call.

## Resource and connection costs

The HLS top estimate is 323 DSP, 47,075 LUT, 50,368 FF, 54 BRAM18, and 40 URAM. Within the K-loop, HLS attributes 224 DSP, 28,094 FF, and 24,971 LUT. Its buckets include 5,425 LUT of expressions, 2,954 LUT of muxes, 13,694 FF and 768 LUT in the register bucket, and 15,824 LUT/14,400 FF inside operator and part-select instances. The buckets do not split conversion, control, address generation, and data steering into a complete independent bill of materials.

At HLS top level, the compute function reports 321 DSP, 41,717 LUT, 45,988 FF, 16 BRAM18, and 8 URAM. The stage function reports 2 DSP, 690 LUT, 584 FF. The activation cache uses 32 URAM; four weight-cache banks use 8 URAM; result tiles use 16 BRAM18. The three AXI master blocks account for 8+15+15 BRAM18 and roughly 2.9K LUT / 2.9K FF combined; AXI-Lite control is 808 LUT / 468 FF. These are HLS hierarchy estimates, not post-route source-attributed costs.

The matched **Vivado corrected full-system route** reports 323/1,248 DSP (25.88%), 41,431/117,120 CLB LUT (35.37%), 55,317/234,240 FF (23.62%), 8,347/14,640 CLB sites (57.02%), 18.5/144 BRAM tiles (12.85%), and 40/64 URAM (62.50%). URAM is the closest reported block-resource limit; DSP, LUT, and FF are not near device capacity. Setup WNS is +3.564 ns at 100 MHz, with no failing endpoints. The worst setup path is a `result_tile_10_addr` register to an activation-cache URAM enable: three logic levels, 5.116 ns routed net delay of 5.681 ns total (90.1%). The accumulator/control enable and K-loop state nets have 5,131 and 1,024 slice loads. This shows a route-level address/control distribution cost; it does **not** show that this path limits current 100 MHz board cycles.

## Measured call cycles and arithmetic-density gate

The RM10 standalone harness brackets each HLS task with the APM global cycle counter and accumulates deltas by task kind. For the primary FFN-down calls, the supported split is `TASK_STAGE_X` versus `TASK_COMPUTE_W`. Stage-X task cycles are about 1.04% and compute-task cycles about 98.96% of the APM elapsed cycles. **Compute-task cycles are not pure arithmetic cycles**: they include the HLS compute task's internal storage accesses, AXI reads/writes, result stores, and any stalls. PE-active cycles, weight-fetch cycles, output-write cycles, and address-stall cycles are **UNKNOWN**.

Host packing, XRT sync-to/from, control submission, and output unpack are measured separately in wall milliseconds; they have no PL cycle counter and their PL-cycle equivalents are **UNKNOWN**. The Y-write byte count is measured by APM, but no output-write cycle split exists. The CSV records these unsupported fields literally as `UNKNOWN`.

| Down call | MACs | FP32 FLOP proxy | APM W+X+Y bytes | Measured APM intensity | Kernel GMAC/s | Stage / compute task cycles | Pack / XRT sync-to / sync-from / unpack (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ffn_down-0`, N=1120 | 5,553,192,960 | 11,106,385,920 | 371,517,440 | 29.895 FLOP/B | 4.781 | 1,207,955 / 114,954,302 | 185.890 / 1.676 / 1.347 / 27.133 |
| `ffn_down-13`, N=280 | 1,388,298,240 | 2,776,596,480 | 95,358,464 | 29.117 FLOP/B | 4.756 | 302,022 / 28,893,749 | 48.196 / 0.429 / 0.343 / 6.816 |
| `ffn_down-26`, N=280 | 1,388,298,240 | 2,776,596,480 | 95,358,464 | 29.117 FLOP/B | 4.756 | 302,030 / 28,893,698 | 47.395 / 0.427 / 0.320 / 6.759 |

The arithmetic-density denominator uses actual APM-observed W read, X read, and Y write bytes for each one-call captured tensor run. The 64 multipliers at 100 MHz imply a simple mapped peak of 6.4 GMAC/s; the observed task-throughput is about 74.7% of that peak. This is an arithmetic/counter gate, not proof of PE utilization, memory boundedness, DDR saturation, or an achieved DDR roof. In particular, the APM payload rate is not divided into a claimed platform bandwidth ceiling.

RM11's three APM rows show the same stage-versus-compute task instrumentation for the unified up mapping, at 99.999 MHz, but use a changed source/IP and transposed K/M. They remain `CONTEXT_ONLY` in the machine table and do not support an RM10 down speedup comparison.

## Conditional structure and stop condition

RM12's current evidence supports **KEEP_RM10**, not an immediate architecture task. The best conditional structure to try *if a future denser array fails route* is bank-local address/enable distribution for the activation-cache URAM interface. The corrected route's worst path is on that control/address connection and is overwhelmingly routed net delay, but WNS is already +3.564 ns at the frozen 100 MHz and the current task counters do not attribute stalls to that path. A control split therefore has no measured present-throughput case.

RM12 Worker B's bounded microkernel result reports that a precise 24x11 multiplier saves only 2 DSP while adding about 2,324 LUT per operator and gives no 10 ns interval gain; it does not clear the arithmetic-density/resource gate, and the full-array route was gated off. This is not a basis for an arithmetic-array change.

If a later, separately justified denser candidate fails route, allow one targeted address/enable distribution experiment at the same 100 MHz target. **Stop** if the target net delay/fanout and WNS do not improve from this baseline, or if the change adds material LUT/URAM cost without a supported call-cycle counter benefit. Do not infer a board speedup from WNS, and make no novelty claim from this route-level hypothesis.

## Evidence paths

- HLS source and design: `experiments/rm10_a_resource_aware/source/vision_ffn_down.cpp`, `evidence/a_ra_fixed10/hls/report/vision_ffn_down_tile_csynth.rpt`, `.../p_anonymous_namespace_compute_weight_batch_Pipeline_VITIS_LOOP_168_9_csynth.rpt`, `.../design.bindinfo.xml`, and `.../p_anonymous_namespace_compute_weight_batch_Pipeline_VITIS_LOOP_168_9.verbose.sched.rpt`.
- Packaged generated RTL: `experiments/rm10_a_resource_aware/artifacts/ip_repo/xilinx_com_hls_vision_ffn_down_tile_1_0/hdl/verilog/` (including the 32-bit `fmul`/`fadd`, compute loop, AXI, part-select, and URAM modules).
- Correct route: `experiments/rm10_route/RM10_CORRECTED_ROUTE_RESULTS.md`, `evidence/corrected_candidate/utilization_post_route.rpt`, `critical_paths_post_route.rpt`, `timing_post_route_setup.rpt`, and `frozen_ip_sha256.txt`.
- Matched board identity and RM10 APM calls: `experiments/rm10_boardprep/evidence/rm10-a-ra-q37804-20260926T084944Z/driver.log`, `tensor-0.log`, `tensor-13.log`, `tensor-26.log`, and `RESULTS.md`.
- RM11 excluded APM context: `experiments/rm11_unified_ffn/RM11_RESULTS.md` and `evidence/board_measurement/rm11-ffn-up-20260926T111621Z/ffn_up-{0,13,26}.log`.

Machine-readable tables: [`rm10_resource_attribution.csv`](rm10_resource_attribution.csv) and [`rm10_rm11_board_cycle_attribution.csv`](rm10_rm11_board_cycle_attribution.csv).
