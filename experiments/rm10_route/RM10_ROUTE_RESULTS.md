# RM10 five-bank provisional route result

Status: **`PROVISIONAL_INVALID` — full physical implementation completed for
the frozen A-rescue package, but its scheduled accumulator recurrence is
invalid. Do not load this bitstream.** The HLS schedule shows an accumulator
load at ST_26 and store at ST_35, while the source declares distance 5 and the
fadd latency is 7 cycles. The route is archived as evidence for this rejected
package; no board-performance result may be derived from it.

## Frozen input and route

- Route branch: `codex/rm10-full-route`; route Tcl/scaffolding commit: `606bc98`.
- A-rescue source commit before cherry-pick: `6116dbec1059d381773dd0d12b4356fb588d4ad8`.
- Route-branch cherry-pick of that source/IP commit: `3815fb1`.
- A-rescue source SHA-256: `9fa209202f5a5efe65e24ffb813d02155838f0c7e4b4380d2d9896d828495a56`.
- IP VLNV: `xilinx.com:hls:vision_ffn_down_tile:1.0`.
- Export ZIP SHA-256: `f285bb72d024c8fb35752c376eab17fad7b18c7163ca89fbe4a3db04dca5d492`.
- IP `component.xml` SHA-256: `d4843820fcbe07f50ae609af2854b1e87aa6e3d38c1f7928f94d7c1ea2aea1dc`.
- All 70 committed files in the Vivado IP repository pass
  `experiments/rm10_a_resource_aware/artifacts/ip_repo/SHA256SUMS`.
- Vivado 2024.2; KV260 part `xck26-sfvc784-2LV-c`; full RM09 static-extent
  PS/AXI-Lite/three-master/SmartConnect/HP0- DDR/APM topology; PL0 constrained
  to 100 MHz (10 ns). Only the HLS IP implementation changed.
- Vivado synthesis, place, route, bitgen, routed DRC, XSA creation, and
  `validate_hw_platform` all completed. Routed DRC had 0 errors; report
  methodology found 0 checks. There were warnings/advisories (including DSP
  pipeline suggestions), listed in the raw DRC report.

## Routed results

| Metric | RM10 A-rescue full system |
|---|---:|
| Requested PL0 clock | 100.000 MHz |
| Post-route setup WNS / TNS | +3.935 ns / 0.000 ns |
| Setup failing endpoints | 0 / 136,555 |
| Post-route hold WHS / THS | +0.010 ns / 0.000 ns |
| Hold failing endpoints | 0 / 136,522 |
| DSP48E2 | 323 / 1,248 (25.88%) |
| CLB LUT | 37,624 / 117,120 (32.12%) |
| CLB FF | 52,160 / 234,240 (22.27%) |
| CLB sites | 7,812 / 14,640 (53.36%) |
| BRAM tiles | 18.5 / 144 (12.85%); 10 RAMB36 and 17 RAMB18 |
| URAM | 40 / 64 (62.50%) |
| Routable nets | 96,459 fully routed; 0 routing errors |
| Congestion | No placer-final or router-initial congestion windows above level 5 |

The post-route slack-derived single-clock period is `10.000 - 3.935 = 6.065 ns`,
or about **164.9 MHz**. This is a timing-model interpretation at the 100 MHz
constraint, not a separate clock sweep or a board clock measurement. The
bitstream remains configured for the 100 MHz PL0.

The worst setup path is inside the K compute loop, from
`ap_enable_reg_pp0_iter34_reg/C` to `tmp_2_reg_15885_reg[22]/D`. Its data delay
is 5.825 ns: 0.476 ns logic and 5.349 ns routed net delay (91.8% of the path).
The 961-load accumulator/control net accounts for 4.772 ns of that route
segment. The top path is therefore dominated by a high-fanout fabric net, not
the FP32 add datapath. The worst 20 setup paths show no URAM endpoint; the
result-tile RAM path appears lower in the report. All 40 URAMs are clocked on
PL0 and distributed across clock regions X2Y0 (8), X2Y1 (16), and X2Y2 (16).
The router reported no remaining overlaps or failed nets.

The routed image uses 140 more DSPs than the frozen RM09 static route
(323 vs. 183), while reported LUTs fall from 66,769 to 37,624 and CLB-site
occupancy from 12,563/14,640 (85.81%) to 7,812/14,640 (53.36%). FFs fall from
67,564 to 52,160; BRAM and URAM remain 18.5 tiles and 40. These are routed
resource totals for these two implementations.

## Correctness boundary and performance status

The software full-tensor numeric evaluator passed the frozen gate for
`ffn_down-0/13/26`, and HLS C-simulation passed 4,096 checked lanes. Neither
establishes RTL recurrence correctness. The frozen HLS synthesis report's
operator table lists FP32 `fadd` latency **7**; source line 166 sets
`DEPENDENCE variable=accum inter distance=5`; parent inspection of the detailed
schedule confirms the accumulator load/store positions are five stages apart
while the bound adder has seven-cycle latency. Treat the reported II=1 schedule
and all derived operation-cycle/throughput projections as invalid for this
package. No board image was loaded, and this bitstream/XSA must not be used for
board performance testing.

No board image was loaded. There is no standalone board GMAC/s, family time,
or QID 37804 request time for this candidate. The HLS schedule projection in
[`HANDOFF.md`](../rm10_a_resource_aware/HANDOFF.md) is not a measured board
result and is not valid as a throughput estimate for this package.

## Artifacts

Raw signoff reports, package hashes, and the Vivado log are under
[`evidence/full_system/`](evidence/full_system/). The bitstream and validated
XSA remain in the local ignored build directory:

- Bitstream:
  `experiments/rm10_route/build/full_system/kv260_rm10_recurrence_decoupled.runs/impl_1/kv260_rm10_recurrence_decoupled_wrapper.bit`
- Bitstream SHA-256:
  `8db28dafa52bc5ff4a85208665aea3f4de6d9866f5d77c8d434de2f8f887f139`
- XSA:
  `experiments/rm10_route/build/full_system/kv260_rm10_recurrence_decoupled.xsa`
- XSA SHA-256:
  `9f26633c2e9494aba5eef9c5caf641840086b4d6411239a550f1e31a1f42665d`
- SHA-256 for every tracked raw route report and manifest:
  [`evidence/full_system/SHA256SUMS.txt`](evidence/full_system/SHA256SUMS.txt)

Reproduce the full implementation with the committed scripts
[`run_full_system.sh`](../../scripts/rm10/run_full_system.sh) and
[`full_system.tcl`](../../scripts/rm10/full_system.tcl), setting
`RM10_IP_REPO` to the frozen package directory listed in the input section.
