# RM10 HLS candidate results

## Baseline diagnosis

The archived RM07 verbose schedule and XML are in [`evidence/baseline`](evidence/baseline). The critical loop is `VITIS_LOOP_97_9` (source line 97, K reduction). Its achieved II is 5 for 269 iterations; the loop report gives 1,358 cycles (1,350-cycle interval). The archived XML labels the violation **Memory Dependency**, distance 1, with the loop location at line 97 and accumulator declaration at line 105. The verbose schedule resolves the lowered scalar: it loads `add1002706` at line 116, adds the product, then stores it back. The reported violation is therefore the accumulator feedback, although HLS does not label it an arithmetic dependence.

The scheduled `FAddSub_nodsp` operation for that update has latency 5, II 1, and 2.94 ns delay; the corresponding `FMul_maxdsp` has latency 4 and II 1. The load/FAdd appears at `ST_10`, with the pipelined FAdd operation represented through `ST_15`; the schedule does not identify a separate accumulator feedback mux stage or register stage, so both are **UNKNOWN**. The existing source has 16 independent residue-lane accumulators per output. Preserving those lanes, hiding a five-cycle feedback requires at least 5 temporal banks per lane: 80 partial accumulators per output, 1,280 across the 16 outputs in a 4x4 tile. This is a recurrence bound only. The current loop also issues 256 source MACs per iteration with 52 mapped multipliers, so the independent resource lower bound is `ceil(256/52) = 5`; eliminating the feedback alone cannot lower II while keeping that loop body and multiplier capacity.

## Candidate comparison

Counts below are HLS estimates for the same standalone tile. “Cycles” gives the K-loop latency and its steady interval. One 4x4 reduction tile performs 68,864 MACs. Effective MAC/cycle is that work divided by the reported K-loop interval. HLS estimates are not routed results.

| Candidate | Reduction organization | II | K-loop cycles (interval) | FP32 mul / add cores in K loop | Effective MAC/cycle | Top DSP / LUT / FF | BRAM18 / URAM | HLS Fmax estimate | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Baseline | 16 residue lanes, sequential final lane fold | 5 | 1,358 (1,350) | 52 / 52 | 51.0 | RM09 frozen: 183 / 66,769 / FF not reported | BRAM not reported / 40 | Board clock 100 MHz | Pass baseline |
| A | Five rotating banks per residue lane; bank left-fold, then residue left-fold | 5 | 1,357 (1,350) | 52 / 52; 72 additional FP32 add cores in the finalization logic | 51.0 | 303 / 163,222 / 154,236 | 54 / 40 | 206.85 MHz | Fail: II unchanged; LUT exceeds device capacity |
| B | Four parallel contiguous segments of 68/68/68/65 K groups; each keeps 16 residue chains; fixed four-way final tree | 5 | 365 (345) | 205 / 205; 48 additional FP32 add cores in finalization | 199.6 | 722 / 285,013 / 277,792 | 54 / 120 | 244.86 MHz | Fail: II unchanged; LUT, FF, and URAM exceed device capacity |
| C | A’s five rotating banks; balanced pairwise bank reduction plus fifth bank, then residue left-fold | 5 | 1,357 (1,350) | 52 / 52; 60 additional FP32 add cores in finalization | 51.0 | 279 / 158,874 / 150,156 | 54 / 40 | 206.85 MHz | Fail: II unchanged; LUT exceeds device capacity |

For A and C, HLS still reports a distance-1 `accum` store-to-load dependence in the K loop (source line 143). The dynamic `group % 5` index did not let the scheduler prove that successive updates address distinct banks. The final reduction tree in C is outside the recurrent update and did not change the K-loop schedule. B keeps four separate distance-1 accumulator recurrences; it raises the multiplier count to 205, reducing K-loop interval through much greater arithmetic parallelism, but still achieves II 5 and exceeds the K26 fabric and URAM capacities before routing.

The actual HLS top reports are `vision_ffn_down_tile_csynth.rpt` under each candidate evidence directory. The loop reports and full HLS logs are alongside them. The clock figures are synthesis estimates only. No candidate reached route: A and C exceed the device LUT count (117,120 available); B exceeds LUT (117,120), FF (234,240), and URAM (64) limits. Thus CLB occupancy, routed Fmax, WNS/WHS, congestion, and URAM routing are **not available**.

Top-level HLS latency remains unknown for all three candidates because runtime `active_N`/tile control keeps the top latency dynamic. The reported K-loop latencies are for the inner 4x4 output reduction tile, not a complete model-family call.

## Functional and numeric checks

The C-simulation testbench passed for A, B, and C (4,096 output words equal 4304 for the all-ones input). The arithmetic remains F16 weight conversion to F32, separate F32 multiply and add, F32 partials and output; compilation disables FP contraction. The numeric worker cross-checked the exact source operation orders and reports all 9 `ffn_down-0`, `ffn_down-13`, and `ffn_down-26` rows pass the frozen RM09 numerical gate. No board or integrated request was run because none passed the scheduler/resource gate.

The source cross-checked by the numeric worker has SHA-256 `367854f27a9d30b152e85999bc7c8d0a92cf731593062f9d6fe1bbfd9777c1c2` (`source/vision_ffn_down.cpp`).

## Conclusion for these three candidates

None of A/B/C lowers the K-loop II. A and C preserve baseline throughput and fail LUT capacity; B gains throughput only by replicating arithmetic beyond the K26 fabric budget, while retaining II 5. These three candidates do not justify route or board testing. The root-causing resource constraint is visible independently of the recurrence: 256 source MACs divided among 52 mapped multipliers already requires five cycles per source loop iteration.
