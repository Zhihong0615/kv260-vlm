# RM07 — Extent-capable bounded-buffer FFN-down engine

Status: **HLS, real-tensor C-simulation, full-system synthesis, placement, routing, and bitgen passed. No bitstream has been loaded on the KV260.**

## One engine for N=1120 and N=280

The same `vision_ffn_down_tile` top accepts only `active_N ∈ {1120,280}`. K/M stay 4304/1152. The host issues 32-token activation-stage commands and 128-output compute-batch commands. N=280 has eight 32-row tiles and one 24-row tail; the tail iterates six four-row groups and does not calculate padded rows. K=17216 merger, FFN-up, and attention operators are outside this RM.

The top uses the same FP16 weight conversion, sixteen FP32 partial accumulators, and final FP32 reduction order as the RM06 K16 path. Numerical results below compare the new extent top against CPU-captured Y.

## Real tensor numerical regression

Each capture runs nine bounded compute commands: three token positions (including the last tile) × three 128-output bands. It checks every output in those sampled ranges.

| Capture | Shape K/M/N | Sampled outputs | Max abs error | RMSE | Cosine |
|---|---|---:|---:|---:|---:|
| `ffn_down-0` | 4304/1152/1120 | 36,864 | 2.38419e-6 | 1.48677e-7 | 0.999999999999939 |
| `ffn_down-13` | 4304/1152/280 | 33,792 | 1.01328e-6 | 1.08837e-7 | 0.999999999999858 |
| `ffn_down-26` | 4304/1152/280 | 33,792 | 2.13623e-4 | 5.27333e-6 | 0.999999999999965 |

These are sampled output regions, not full-tensor comparisons or end-to-end quality measurements. HLS C-simulation passed for all three captures and for both scheduled shapes.

## HLS result and II root cause

Vitis HLS 2024.2 target: xck26-sfvc784-2LV-c, 200 MHz.

| Metric | Final HLS estimate |
|---|---:|
| Compute-loop II | 5 |
| K-loop iterations | 269 |
| Actual FP32 multipliers | 52 |
| HLS estimated Fmax | 265.32 MHz |
| DSP | 184 |
| LUT | 73,995 |
| FF | 60,445 |
| BRAM18 | 54 |
| URAM | 40 / 64 |

The K-loop II=5 comes from the distance-one FP32 partial-accumulator recurrence (`accum[i][j][p] += w*x`), not a dynamic-extent penalty. The nominal 4×4×16 source lane product is 256, but HLS binds 52 actual FP32 multipliers. The short root-cause and loop schedule are in [RM07_HLS_ROOT_CAUSE.md](RM07_HLS_ROOT_CAUSE.md).

The HLS loop reports give 452,024 cycles for a 32-row, 128-output compute command and 356,248 cycles for a 24-row tail command. Activation staging takes 17,231 and 12,927 scheduled cycles, respectively. An RTL co-simulation was stopped after six minutes while still executing its first compute transaction; the reported cycles are composed from the final synthesis loop schedule, not claimed as board or RTL co-simulation timing.

## Bounded staging pool

No whole W/X/Y tensor is allocated in CMA. One serialized working pool is enough for the current command protocol:

| Buffer | Bytes |
|---|---:|
| W: 128 × 4304 × FP16 | 1,101,824 |
| X: 32 × 4304 × FP32 | 550,912 |
| Y: 32 × 128 × FP32 | 16,384 |
| **Total** | **1,669,120 B = 1.592 MiB** |
| Page-rounded allocation | **1,671,168 B = 408 pages = 1.594 MiB** |

Ownership is serialized: CPU packs a tile, PL reads W/X or writes Y during one command, then CPU reuses the buffer and copies the output tile to the ordinary destination tensor. No overlap is assumed. Optional ping-pong W/X/Y buffers would use 3,338,240 raw bytes or 3,342,336 bytes (816 pages, 3.187 MiB); this double buffer is not selected in the schedule or cost results.

AXI data widths are 128-bit for W and 256-bit for X/Y. `max_*_burst_length=64`, so the configured burst caps are 1 KiB for W and 2 KiB for X/Y. A W batch is 1,101,824 bytes (1,076 bursts at the contiguous cap; up to about 1,080 if each 16-row tile begins a separate burst stream). Full X staging is 550,912 bytes (269 bursts); a 24-row X tail is 413,184 bytes (202 bursts). A full Y batch is 16 KiB (8 bursts), and the tail output is 12 KiB (6 bursts).

## 27-layer family schedule and transfer model

The scheduled operation cycles compose as:

```text
N=1120: 35 × stage_X(32) + 35 × 9 × compute(32)
N=280:  8 × stage_X(32) + stage_X(24)
        + 8 × 9 × compute(32) + 9 × compute(24)
```

| Shape group | Calls | HLS scheduled cycles/op | Time/op at 187.512 MHz |
|---|---:|---:|---:|
| N=1120 | 35 | 142,990,645 | 0.762568 s |
| N=280 | 100 | 35,902,735 | 0.191469 s |
| **Family** | **135** | **8,594,946,075 total** | **45.837 s** |

W is reread from the bounded buffer for each token tile. This makes family PL payload 22.539 GB: W 21.072 GB, X 1.157 GB, Y 0.310 GB. This traffic includes the repeated W tile loads and is not a one-weight-read-per-layer assumption.

The 45.837-second HLS schedule includes interface movement at the scheduled no-stall beat rate. The loop-schedule residual after subtracting those minimum port-transfer times is 38.569 seconds. The serial staging model adds the PL movement at the assumed effective DDR bandwidth plus two additional DDR touches per payload for CPU tensor-to-stage and stage-to-tensor copies. It excludes host submit/sync time, cache maintenance, and unmeasured bus contention, so the per-command budget is shown as a separate constraint.

| Effective DDR bandwidth | PL transfer | CPU staging copies | Family estimate | Request estimate | Request speedup | Mean submit/sync budget/cmd to beat CPU family |
|---:|---:|---:|---:|---:|---:|---:|
| 0.5 GB/s | 45.078 s | 90.156 s | 173.802 s | 592.028 s | 1.129× | 3.592 ms |
| 1 GB/s | 22.539 s | 45.078 s | 106.186 s | 524.412 s | 1.274× | 6.774 ms |
| 2 GB/s | 11.269 s | 22.539 s | 72.377 s | 490.603 s | 1.362× | 8.365 ms |
| 4 GB/s | 7.390 s | 11.269 s | 57.228 s | 475.454 s | 1.406× | 9.077 ms |

The request model uses the frozen 668.35 s CPU request and 250.124 s FFN-down family time: `T' = 668.35 - 250.124 + T_family`. Zero-boundary core-only ideal is 38.569 s for the family (request 456.795 s, 1.463×). The modeled effective DDR break-even is 0.320 GB/s including the three total DDR touches, assuming zero submit/sync overhead and bandwidth below the W-port cap. The PL-payload-only break-even is 106.5 MB/s. These are schedule projections, not board measurements. Re-running at the final routed PL clock of 187.512 MHz leaves the table unchanged.

## Full-system and board-load status

The final single-image PS + AXI-Lite + three HLS AXI masters + SmartConnect/HP0 DDR + APM system completed Vivado 2024.2 synthesis, place, route, and bitgen. The HLS IP is connected to PS DDR through HP0; the APM monitors W/X/Y AXI traffic.

| Post-route system metric | Result |
|---|---:|
| PL clock achieved / constraint | 187.512 MHz (`clk_pl_0`, 5.333 ns) |
| Setup WNS / TNS | +0.425 ns / 0 ns; 0 failing endpoints |
| Hold WHS / THS | +0.010 ns / 0 ns; 0 failing endpoints |
| DSP48E2 | 184 / 1248 (14.74%) |
| CLB LUTs | 66,603 / 117,120 (56.87%) |
| CLB registers | 67,541 / 234,240 (28.83%) |
| CLB sites | 12,936 / 14,640 (**88.36%**) |
| Block RAM | 10 RAMB36 + 17 RAMB18 (18.5 BRAM tiles) |
| URAM | 40 / 64 (62.50%) |
| Route / DRC / bitgen | 0 unrouted nets; DRC 0 errors; bitgen passed |

The routed clock is the PS-generated `clk_pl_0` rate, not a faster independently characterized Fmax. Positive setup and hold slack show timing closure at 187.512 MHz. CLB site occupancy is already high despite LUT use of 56.87%, so this system has limited placement headroom.

Generated artifacts (kept in the ignored local build directory):

- Bitstream: `experiments/rm07/build/bounded_k16_system/kv260_rm07_bounded_k16.runs/impl_1/kv260_rm07_bounded_k16_wrapper.bit`
- Bitstream SHA-256: `1d537918b45bc9a53afb290beecda379918b7fd1a14374d6b5173358d8291942`
- XSA: `experiments/rm07/build/bounded_k16_system/kv260_rm07_bounded_k16.xsa`
- XSA SHA-256: `583362606be4e6829cdde3f4e1a4689f6ec775d1b51ce7dd840caed188fbd805`
- HLS IP archive SHA-256: `1536980e629aec70704dd567ec74e8665f287e2ce2627f77f96c1c407e18d779`
- Tracked evidence copies: [`evidence/`](evidence/) (HLS reports, three C-sim logs, route status, timing and utilization)
- Original Vivado reports: `experiments/rm07/build/bounded_k16_system/rm07_timing_post_route.rpt` and `rm07_utilization_post_route.rpt`

No custom image has been loaded. The separate read-only recovery audit found the starter-kit app active but no installed RM06/RM07 app, no connected USB-UART, and no tested recovery path. The candidate rollback command is `sudo xmutil unloadapp && sudo xmutil loadapp k26-starter-kits`; it is **not verified**. Do not load the bitstream until there is an independent recovery path and the app-loading/rollback procedure is confirmed on this board. This RM has no board latency, DDR bandwidth, or end-to-end PL measurement.

## Decision

**A — `GO_BOARD_FFN_FAMILY`, as the next gated board experiment only.** One bitstream covers both extents, sampled real tensors pass C-simulation, the HLS interface uses bounded W/X/Y tiles with a calculated 1.594 MiB page-rounded single staging pool (versus the previous ~32.77 MiB full-tensor contiguous requirement), and the routed system meets 187.512 MHz. The PS-side packing/submit runtime is not implemented or measured yet. At the conservative 0.5 GB/s serialized model, family time is 173.802 s versus 250.124 s CPU and predicted request time is 592.028 s versus 668.35 s (1.129×, before command overhead). This is enough to justify a measured board experiment, not enough to claim speedup. The model allows only 3.592 ms mean submit/sync per command at 0.5 GB/s. The experiment remains gated because recovery is not verified; actual PS/PL execution, DMA bandwidth, end-to-end latency, and full-tensor output quality are still unmeasured. If board submission/transfer cost erases the modeled margin, move to C; if kernel wins but data movement dominates, move to B.
