# RM03-B: HLS mapping root cause

> **RM04 correction:** This report's original frozen operation was mislabeled `ffn_up-0`. Its constants (`K=4304, M=1152, N=1120`) match `ffn_down`, not the real `ffn_up-0` contract captured on KV260 (`K=1152, M=4304, N=1120`). The schedule diagnosis below applies to the old compiled shape. RM04 corrected Dynamic8 for the true `ffn_up-0` shape and validated a real tensor tile; see [`RM04_RESULTS.md`](../rm04_system/RM04_RESULTS.md).

## Frozen workload and hot loop

The operation is `X[1120,4304] * W[1152,4304]^T`: binary16 weights expand exactly to binary32; products, partial sums and output are binary32. The RM02 source fully unrolls a nominal 4×4 output microtile while requesting `PIPELINE II=1` on K. The frozen v3 report gives the flattened compute loop 137,728 iterations, 86-cycle iteration latency and achieved II=5 (target 1).

## Diagnosed II=5 constraint

The preserved RM02 Vitis console log (`artifacts/rm02_static_v3_reference/solution1.log`, lines 145–149) provides the decisive evidence. For proposed II values 1, 2, 3 and 4, HLS 200-880 emits the same carried distance-1 dependence on local array `accum`: one store is the update `accum[i][j][partial] += ...` at source line 111; the other is the zero initialization at line 90. The tool accepts II=5 immediately after those four violations. This is an HLS memory/lifetime dependence between the per-microtile reset and the update after nested-loop flattening; it is distinct from a true arithmetic recurrence in one partial accumulator. The report directly establishes the constraint responsible for II=5.

The updated RM03 experiment with `LOOP_FLATTEN off` and static K lanes still reports II=5, but its diagnostic changed: the loop is now only the K-group loop, and the carried dependence is between a store and load of HLS's local `empty` temporary at the update site. With K_LANES=4, that bank is updated once per pipelined group, so the new form has an ordinary distance-1 accumulator feedback. This first static-lane probe therefore does **not** prove that loop flattening alone fixes II. The completed RM03 dynamic-eight-lane/no-flatten control validates that distinction: `artifacts/hls/rm03_pe4x4_dynamic8_noflat/vitis_hls.console.log` accepts compute-loop II=1 (the loop covers 4,304 k values), while its full-top latency is 397,802,882 cycles. The dynamic partial index presents the eight accumulator banks as distance-eight updates; no-flatten prevents the reset/update alias from reappearing through flattened outer loops. The static K4/K8/K16 candidates remain II=5 because each unrolled K group updates each statically selected partial accumulator on every group iteration. Their lower total cycles come from issuing more K products per group, not from achieving a smaller group-loop II.

## Why 16 source products become four multipliers

The loop report lists only four `fmul_32ns_32ns_32_5_max_dsp_1` IP instances, U47–U50. The schedule binds the 16 statically unrolled i/j product sites onto `FMul_maxdsp` cores with latency 4 and operator II=1. No source or Tcl directive caps the count; RM02 `ALLOCATION ... limit=16` was an upper ceiling and still synthesized four. The inferred count is thus Vitis automatic operator sharing. Four II=1 units give a 16/4 = 4-cycle resource lower bound for 16 products per source K step; that alone does not explain the observed II=5, which is why the separate dependence warning above matters.

The hot loop's dynamic `partial = k & 7` also creates eight-way `sparsemux` paths before accumulator updates. These are directly visible in the scheduler report but are not identified by the HLS 200-880 message as the II=5 cause.

The same detailed HLS loop report allocates 66 DSP: 4 FP32 multipliers × 3 DSP = 12; 26 distinct full-DSP FP32 adders × 2 DSP = 52; and two small address `mac_muladd` operators = 2. The four accumulator-update adders are no-DSP fabric instances. The two load pipelines add one address `mac_muladd` each, yielding 68 DSP in the full top. This separates arithmetic resource sharing from the loop-carried accumulator reset dependence.

## Controlled experiment scope

RM03 completed six configurations: static K4 flattened, static K4/K8/K16 without flattening, dynamic-eight without flattening, and PE2×8 static K4. All preserve the workload dimensions and F16→F32 multiply / F32 accumulate precision, with a per-configuration C-sim golden for one representative 16×32 tile. Static K changes binary32 accumulation association; dynamic-eight retains the original eight-way association. Detailed cycles, utilization, traffic, HLS resources, and OOC route evidence are in `RESULTS.md`. All new source and generated artifacts are under `experiments/rm03_hls_mapping/`; RM02 source/reports remain frozen. No bitstream is loaded.

## Evidence pointers

- Frozen source with exact reset/update sites: `experiments/rm02_b_vision_gemm/vision_gemm.cpp`, lines 90 and 111.
- HLS 200-880 log and final pipelining result: `experiments/rm02_b_vision_gemm/reports/baseline_static_v3_m16_n32/project/solution1/solution1.log`, lines 145–149.
- Loop summary and resource inventory: `experiments/rm03_hls_mapping/artifacts/rm02_static_v3_reference/compute_loop_csynth.rpt`.
- Operator schedule and dynamic `sparsemux` paths: `experiments/rm03_hls_mapping/artifacts/rm02_static_v3_reference/compute_loop_verbose_schedule.rpt`.
- Initial RM03 static K-lane/no-flatten probe: `experiments/rm03_hls_mapping/artifacts/hls/rm03_pe4x4_k4_noflat/`.
