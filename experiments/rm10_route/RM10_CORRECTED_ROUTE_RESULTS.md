# RM10 corrected 10-bank A full-system route

Status: **full Vivado route, bitgen, DRC, and XSA validation passed** for the corrected ten-bank A candidate. The route used the frozen source/IP named below. The full-tensor numeric gate passed the frozen gate on `ffn_down-0`, `ffn_down-13`, and `ffn_down-26`; the full-top RTL co-simulation checked 4,096 output lanes and passed. Board testing and end-to-end MiniCPM-V validation are separate and have not been performed by this route task. Do not infer board throughput from the routed image.

## Frozen candidate and correctness evidence

- Rescue source commit: `3602eafa7de5cee187b79f8e28c186a19f6f6133`; route-branch cherry-pick: `96e2fdc`.
- Source SHA-256: `31a7b26f9bf28c0ad57892184ed30b42126162111fe4c4bda82aa7847754319a`.
- IP VLNV: `xilinx.com:hls:vision_ffn_down_tile:1.0`.
- IP `component.xml` SHA-256: `fae7fde4af5b3f5a1237d5e7717ea97622a9a8c6107ba96c97bfe6bb19feda56`.
- Export ZIP SHA-256: `b54c4ac0a15dc4501c3d1d470eeb2664fe9e2e60cf0d9ba7a0cfd9fdcca82e6b`.
- All 70 files in the committed IP package pass `experiments/rm10_a_resource_aware/artifacts/ip_repo/SHA256SUMS`.
- The K loop pipelines at II=1 with a true recurrence distance of 10. The generated schedule reads at ST_25 and writes at ST_34; the bound FP32 adder latency is 7 cycles. The design reduces four K products through a balanced pairwise tree before updating one of ten temporal FP32 banks, then performs a deterministic FP32 reduction of the ten banks.
- Full-top RTL co-simulation: 4,096 output lanes checked; PASS. Raw log: `experiments/rm10_a_resource_aware/evidence/a_ra_fixed10/hls/csim_csynth_cosim.log`.
- Frozen full-tensor numeric gate:

| Tensor | Max absolute error | RMSE | Cosine | Gate |
|---|---:|---:|---:|---|
| `ffn_down-0` | 9.5367431641e-6 | 1.7537096173e-7 | 0.99999999999985 | PASS |
| `ffn_down-13` | 2.1904706955e-6 | 1.0718580912e-7 | 0.99999999999980 | PASS |
| `ffn_down-26` | 3.0517578125e-4 | 5.2901536699e-6 | 0.99999999999996 | PASS |

The numeric manifest is `experiments/rm10_a_resource_aware/evidence/a_ra_fixed10/numeric/SHA256SUMS`. The RM10 candidate HLS report lists the K-loop latency as 1,109 cycles, trip count 1,076, and interval 1.

## Full-system Vivado route

Vivado 2024.2 implemented the RM09 static-extent PS/AXI-Lite/three-master/SmartConnect/HP0-DDR/APM topology on KV260 part `xck26-sfvc784-2LV-c`. PL0 remained constrained to 100 MHz (10 ns); no clock sweep was run. Synthesis, placement, routing, bitgen, routed DRC, XSA creation, and `validate_hw_platform` completed successfully.

| Metric | Corrected route |
|---|---:|
| PL0 constraint | 100.000 MHz |
| Post-route WNS / TNS | +3.564 ns / 0.000 ns |
| Setup failing endpoints | 0 / 146,565 |
| Post-route WHS / THS | +0.010 ns / 0.000 ns |
| Hold failing endpoints | 0 / 146,532 |
| DSP48E2 | 323 / 1,248 (25.88%) |
| CLB LUT | 41,431 / 117,120 (35.37%) |
| CLB FF | 55,317 / 234,240 (23.62%) |
| CLB sites | 8,347 / 14,640 (57.02%) |
| BRAM tiles | 18.5 / 144 (12.85%); 10 RAMB36 and 17 RAMB18 |
| URAM | 40 / 64 (62.50%) |
| Routable nets | 101,495 fully routed; 0 routing errors |
| Congestion | No placer-final or router-initial congestion windows above level 5 |
| Methodology report | 0 checks |
| DRC | 0 errors; DSP pipeline warnings/advisories remain in the raw report |

The slack-derived period is `10.000 - 3.564 = 6.436 ns`, or approximately **155.4 MHz**. This is an interpretation of timing slack under the 100 MHz constraint, not a second implementation clock or a measured board frequency; the image remains configured for 100 MHz.

The worst setup path is from a K-loop `result_tile_10_addr` register to an activation-cache URAM enable. Data delay is 5.681 ns, of which 5.116 ns (90.1%) is routed net delay; the path has only three logic levels (two CARRY8 cells and one LUT6). This critical path is memory-address/control routing, not an FP32 adder data path. The worst hold path starts at an FP32 `fadd` input buffer and closes at +0.010 ns, with no failing hold endpoints. The accumulator/control enable net has 5,131 slice loads and the K-loop state net has 1,024 slice loads; Vivado inserted BUFGCE drivers. DSP48 resources are distributed mainly across clock regions X1Y0 (119) and X1Y1 (123), with the remaining 81 across X0Y0, X2Y0, X0Y1, X2Y1, and X1Y2. The 40 URAMs are placed 12 in X2Y0, 16 in X2Y1, and 12 in X2Y2. No placer-final or router-initial congestion window exceeded level 5.

Against the frozen RM09 static route (183 DSP, 66,769 LUT, 12,563/14,640 CLB sites), the corrected route uses 140 more DSPs but 25,338 fewer LUTs and 4,216 fewer CLB sites. CLB-site occupancy is 57.02%, down from 85.81%. This is a routed resource comparison only; it does not establish higher board throughput.

## Artifacts

The exact raw Vivado reports, IP package file hashes, bitstream/XSA identities, and Vivado log are under [`evidence/corrected_candidate/`](evidence/corrected_candidate/). Their `SHA256SUMS.txt` is verified. Build outputs are in the ignored local build directory:

- `.bit`: `/home/zhiro/research/kv260-vlm-workers/RM10-full-route/experiments/rm10_route/build/corrected_candidate/kv260_rm10_recurrence_decoupled.runs/impl_1/kv260_rm10_recurrence_decoupled_wrapper.bit`
- Bitstream SHA-256: `18ba853551f85ce1814332eacd370264696a93423fbf5a408e028b307c18ac23`
- XSA: `/home/zhiro/research/kv260-vlm-workers/RM10-full-route/experiments/rm10_route/build/corrected_candidate/kv260_rm10_recurrence_decoupled.xsa`
- XSA SHA-256: `a85ff605c6e5dbe52a4e413ce38499b70d6c1bc857509ff5433d1f03f5934e0b`

No board image was loaded. No standalone board GMAC/s, family latency, or QID 37804 request time is available yet.
