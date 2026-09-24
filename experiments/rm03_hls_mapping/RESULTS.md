# RM03-B: HLS mapping sweep and OOC implementation evidence

## Scope and frozen operation

The frozen native MiniCPM-V vision-encoder operation is `Y[1120,1152] = X[1120,4304] × W[1152,4304]^T` (`ffn_up-0`). Dimensions are row/token, output-channel, reduction-channel. The HLS top is run across the complete operation and uses a fixed macro tile of 16 output channels × 32 tokens. The device is `xck26-sfvc784-2LV-c` (KV260/K26), toolchain Vitis/Vivado HLS 2024.2, with a 5.0 ns / 200 MHz target clock.

All designs expand IEEE binary16 weights exactly to binary32; activation, product, partial sum, and output are binary32. There is no quantization. Static K-lane designs change the binary32 summation association: they update one lane for every K-lane group and reduce lanes at the end. The `dynamic8` configuration preserves the original eight-way `k & 7` accumulation grouping and serves as a same-association control. Every candidate C-sim compares a real-shape 16×32 macro tile against a software golden that uses the matching accumulation order. The deterministic tile test passed with maximum absolute error 0 and relative error 0 for all six candidates; this validates the exercised tile and data pattern, not every possible model tensor or exceptional float value.

The full-top cycle counts are HLS schedule estimates for all 5.55 billion MACs. They do not include measured KV260 DDR contention, actual AXI stalls, PS/PL orchestration, or board thermal effects. The C-sim validates one macro tile, not the full top. No bitstream was loaded.

## HLS sweep

Counts are from Vitis HLS `vision_gemm_csynth.rpt`; inferred FP32 multiplier counts are from each compute-loop report. Estimated Fmax is the HLS estimate, not a routed frequency. HLS resource denominators for K26 are 1,248 DSP, 117,120 LUT, 234,240 FF, 288 BRAM18K, and 64 URAM. Full-top estimated time is cycles / 200 MHz.

| Configuration | PE and K organization | Compute II | FP32 multipliers | Full-top cycles | Time @ 200 MHz | HLS est. Fmax | DSP | LUT | FF | BRAM18K | URAM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RM02 frozen v3 | 4×4, dynamic 8-lane | 5 | 4 | 1,779,196,322 | 8.896 s | 244.14 MHz | 68 | 28,428 | 36,939 | 102 | 40 |
| RM03 K4 flattened | 4×4, static K4 | 5 | 13 | 477,586,082 | 2.388 s | 247.19 MHz | 69 | 35,172 | 30,341 | 102 | 40 |
| RM03 K4 no-flatten | 4×4, static K4 | 5 | 13 | 481,829,762 | 2.409 s | 247.19 MHz | 65 | 27,270 | 22,225 | 54 | 40 |
| RM03 dynamic8 no-flatten | 4×4, dynamic eight-way | 1 | 16 | 397,802,882 | 1.989 s | 239.52 MHz | 82 | 18,907 | 18,757 | 54 | 40 |
| RM03 K8 no-flatten | 4×4, static K8 | 5 | 26 | 267,488,642 | 1.337 s | 269.53 MHz | 104 | 41,341 | 34,786 | 54 | 40 |
| RM03 K16 no-flatten | 4×4, static K16 | 5 | 52 | 164,188,802 | 0.821 s | 265.32 MHz | 182 | 72,918 | 59,980 | 54 | 40 |
| RM03 PE2×8 K4 no-flatten | 2×8, static K4 | 5 | 13 | 482,172,482 | 2.411 s | 247.19 MHz | 69 | 26,766 | 23,052 | 54 | 40 |

Relative to frozen RM02 v3, K4/K4-no-flatten/dynamic8/K8/K16/PE2×8 K4 reduce scheduled cycles by 3.73× / 3.69× / 4.47× / 6.65× / 10.84× / 3.69×, respectively. K16 is fastest in the HLS schedule but consumes 62.3% of LUT and 62.5% of URAM before any system wrapper. Its static K16 lane order is not the same FP32 accumulation association as the frozen dynamic-eight baseline. Dynamic8 no-flatten preserves that association and improves the original schedule 4.47× while reducing HLS BRAM18K from 102 to 54; it remains a feasibility result, not a novelty claim.

The changed PE factor from 4×4 to 2×8 did not improve cycle count over 4×4 K4. Static K4 flatten-on versus no-flatten has similar latency and resource use; simply disabling flatten is not the source of the major gains. Static K8/K16 expose multiple compile-time K products and increase mapped multiplier count, trading more arithmetic resources and changed FP32 reduction order for schedule throughput.

## Effective MAC utilization

The operation contains `1120 × 1152 × 4304 = 5,553,192,960` MACs. Full-top useful MAC/cycle is that count divided by HLS full-top cycles. The theoretical compute capacity is one MAC/cycle per mapped FP32 multiplier core (the bind reports show II=1 multiplier instances). Effective utilization is useful full-top MAC/cycle divided by that multiplier count. This is an average mapped-multiplier issue utilization: it includes tile loading, output, and loop-control cycles in the full-top schedule denominator and is not a physical switching-activity counter.

| Configuration | Useful MAC/cycle | Theoretical MAC/cycle from mapped multipliers | Effective MAC utilization |
|---|---:|---:|---:|
| RM02 frozen v3 | 3.12 | 4 | 78.0% |
| RM03 K4 flattened | 11.63 | 13 | 89.4% |
| RM03 K4 no-flatten | 11.53 | 13 | 88.7% |
| RM03 dynamic8 no-flatten | 13.96 | 16 | 87.2% |
| RM03 K8 no-flatten | 20.76 | 26 | 79.8% |
| RM03 K16 no-flatten | 33.82 | 52 | 65.0% |
| RM03 PE2×8 K4 no-flatten | 11.52 | 13 | 88.6% |

These are HLS schedule-derived utilization figures, not physical activity counters. They quantify full-top useful work relative to each configuration’s mapped FP32 multiplier issue capacity; DDR stalls and physical clock effects are not represented.

## Traffic and DDR roofline

The byte model follows the loop order in the HLS top, assuming each macro tile reloads its full operand segment and there is no cache reuse between outer-loop iterations:

| Traffic | Calculation | Bytes |
|---|---:|---:|
| Weights | `1152 × 4304 × 2 B × 35 token tiles` | 347,074,560 |
| Activations | `1120 × 4304 × 4 B × 72 output-channel tiles` | 1,388,298,240 |
| Output writes | `1120 × 1152 × 4 B` | 5,160,960 |
| Total |  | 1,740,533,760 B (1.621 GiB) |

Arithmetic intensity is 3.19 MAC/B. Assuming 4.8 GB/s sustained DDR payload bandwidth gives a traffic-only lower bound of 0.363 s; assuming 1.0 GB/s gives 1.741 s. These bandwidths are assumptions, not KV260 measurements. K16's 0.821 s @200 MHz schedule would require about 2.12 GB/s to avoid becoming traffic-bound under this model; dynamic8's 1.989 s schedule would require about 0.875 GB/s. Actual accelerator performance cannot be inferred until AXI/DDR stalls and the board path are measured.

## Vivado synthesis and OOC route

A full-top Vivado synthesis was generated for K16 and dynamic8. In both cases, the full-top placement attempt treated the standalone top's unwrapped `m_axi` interfaces as package I/O and failed with a bonded I/O demand of 1,808 versus 189 available (`Place 30-68` / `Place 30-99`). This is not evidence of compute-fabric placement failure. The raw failed logs and post-synthesis reports are preserved in `artifacts/vivado/`.

To obtain an internal compute-core route without inventing a PS wrapper, each RTL core was implemented once out-of-context with the same device and 5 ns clock, virtual I/O, and no external AXI delay constraints. Both completed `opt_design`, placement, physical optimization, and routing. **These are OOC feasibility numbers, not board timing or a full-system result.** Vivado warns that `HD.CLK_SRC` is unset, limiting clock-skew estimation. The WNS-derived equivalent periods below are `5 ns − WNS`; they are only a rough timing comparison under that OOC constraint.

| OOC configuration | Post-route WNS | WNS-derived period / frequency | Worst data path | Post-route resources |
|---|---:|---:|---|---|
| K16 | +0.225 ns, 0 failing setup endpoints | 4.775 ns / ≈209.4 MHz | Compute FSM state register → FP32 multiplier input; 4.771 ns path delay, 4.432 ns routed net | 55,052 LUT total; 54,760 FF; 182 DSP; 23.5 BRAM tiles; 40/64 URAM |
| Dynamic8 | +0.557 ns, 0 failing setup endpoints | 4.443 ns / ≈225.1 MHz | DSP output → activation-tile URAM address; 3.956 ns path delay, 3.679 ns routed net | 12,800 LUT total; 17,602 FF; 82 DSP; 23.5 BRAM tiles; 40/64 URAM |

Vivado K26 denominators are 117,120 LUT, 234,240 FF, 1,248 DSP, 144 BRAM tiles (288 BRAM18K equivalents), and 64 URAM. Thus OOC K16 uses 47.0% LUT, 23.4% FF, 14.6% DSP, 16.3% BRAM tiles, and 62.5% URAM; dynamic8 uses 10.9%, 7.5%, 6.6%, 16.3%, and 62.5%, respectively. The 40 URAM used by both is the fixed full-K tile storage and is the most restrictive shared resource. The routed core results do not constrain package pins, PS integration, clock-source properties, DDR timing, or board power/thermal behavior.

## Result and next decision

The HLS data shows that static K8/K16 expansion can sharply lower schedule cycles by exposing more FP32 multiplier instances; the K16 design is the fastest synthesis result. Its OOC route is positive at the 5 ns target but has only 0.225 ns WNS, a long routed control-to-multiplier path, and 62.5% URAM use before integration. The dynamic-eight-way no-flatten design is slower than K8/K16 but retains the original accumulation association, halves BRAM18K relative to RM02 v3, and routes with a larger OOC slack. Neither result alone establishes an architecture contribution: the full PS–PL–DDR path and numerical accuracy on actual model tensors remain unmeasured. Preserve K16 as the speed/resource upper point and dynamic8 as the association-preserving lower-risk reference for subsequent system-level evaluation.

## Reproduction and evidence

- HLS source, testbench, Tcl: `source/vision_gemm.cpp`, `source/vision_gemm.hpp`, `source/tb.cpp`, `source/run_hls.tcl`.
- Root-cause analysis: `RM03_HLS_ROOT_CAUSE.md`.
- Curated HLS synthesis/C-sim evidence: `artifacts/hls/<configuration>/`.
- Full-top Vivado synth reports and failed package-I/O logs: `artifacts/vivado/vivado_rm03_{k16,dynamic8}/`.
- OOC Vivado synth/route timing/utilization reports and logs: `artifacts/vivado/vivado_ooc_rm03_{k16,dynamic8}/`.
- Original full Vivado work directories and routed DCPs remain at `reports/vivado_ooc_rm03_{k16,dynamic8}/`; routed DCPs are not needed to read the evidence and are not included in Git.
- The six uncurated HLS projects and complete output trees are retained locally under `reports/<configuration>/project/` for drill-down; the committed console logs and key reports provide the compact reproducibility record.
