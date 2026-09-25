# SUPERSEDED: RM10 A five-bank resource-aware revision

This handoff describes the earlier five-bank artifact. The correctness audit
found its dependence pragma was not a true RAW declaration and its schedule
revisited each bank before the previous write committed. Do not route or use
this artifact. See the current ten-bank handoff in `HANDOFF.md`.

Status: **HLS C-simulation passed, full captured tensor numeric gate passed, HLS synthesis passed, exported IP frozen. No route or board measurement is included.**

## Architecture

This is a single resource-aware revision of candidate A. The existing top
interface, AXI bundles, bounded buffers, shape limits, and F16 weight / F32
activation / F32 output data path are unchanged. Each 4x4 output group issues
four adjacent K products per output, for 64 source MACs per group. Four F32
products are reduced as `(p0+p1)+(p2+p3)`, then added to one of five F32 temporal
banks selected by `group % 5`; the final bank reduction is
`((b0+b1)+(b2+b3))+b4`.

The `DEPENDENCE` pragma gives the inter-iteration dependence a distance of 5.
That matches the bank function exactly: a bank written in group `g` is first
written again in `g+5`. The synthesized FAdd latency is 5 cycles, so the loop
can legally issue at II=1 while retaining the dependence. The pragma does not
declare the dependency absent.

## HLS result

| Measure | Result |
|---|---:|
| K groups per 4x4 output group | 1076 |
| K-loop achieved II | 1 |
| K-loop latency | 1109 cycles |
| K-loop pipeline iteration latency | 35 cycles |
| K-loop mapped FP32 multipliers | 64 |
| K-loop mapped FP32 adders | 40 |
| HLS estimated Fmax | 261.25 MHz |
| Top DSP | 323 |
| Top LUT | 43,235 |
| Top FF | 45,835 |
| Top BRAM18 | 54 |
| Top URAM | 40 |

The top report uses 5.0 ns target clock and estimates 3.828 ns. The compute
helper uses 321 DSP, 37,877 LUT, 41,455 FF, 16 BRAM18, and 8 URAM; activation
storage accounts for the other 32 URAM at top level. These are HLS estimates,
not routed resource or timing results.

The HLS C-simulation passed all 4096 checked output lanes. Raw reports and logs
are in `evidence/a_ra/hls/report/` and `evidence/a_ra/hls/vitis_hls.log`.

## Full-tensor numeric gate

The evaluator mirrors the exact reduction order above and is built with
`-fno-fast-math -ffp-contract=off`. All captured outputs for `ffn_down-0`
(N=1120), `ffn_down-13` (N=280), and `ffn_down-26` (N=280) pass the frozen
gate: max absolute error <= 1e-3, RMSE <= 1e-4, cosine >= 0.999.

| Tensor | Max abs | RMSE | Cosine | Gate |
|---|---:|---:|---:|---|
| ffn_down-0 | 1.14440918e-5 | 1.84391821e-7 | 0.9999999999998126 | PASS |
| ffn_down-13 | 2.32458115e-6 | 1.14033927e-7 | 0.9999999999997770 | PASS |
| ffn_down-26 | 2.74658203e-4 | 5.47304092e-6 | 0.9999999999999192 | PASS |

Element-level error histograms are in `evidence/a_ra/numeric/absolute_error_histogram.csv`;
summary metrics are in `evidence/a_ra/numeric/summary.csv`. Capture input
checksums are in `evidence/a_ra/numeric/capture_tensor_sha256.txt`; tensor
payloads remain outside Git.

## Full-operation schedule projection

The top-level report prints unknown total latency because `tile_rows` is a
runtime argument, so these are explicit schedule-derived cycle projections,
not measured RTL or board cycle counts. They project the inner HLS schedules
over the frozen invocation pattern (N tiled by 32 rows, nine 128-output-channel
compute calls per activation tile, eight 16-channel weight tiles per compute
call). The fixed child-loop evidence is in `report/csynth.rpt`:

- weight-tile load: 8608 iterations, II=1, 8612-cycle helper latency;
- each 4-row n-block across four 4-channel m-groups: 4570 cycles;
- output packing: `2*tile_rows` words, II=1, four-cycle iteration latency;
- activation staging: `538*tile_rows` words, II=1, four-cycle iteration latency.

The projection uses `8*(8612 + (tile_rows/4)*4570 + (2*tile_rows+3))`
cycles per compute call and `538*tile_rows+3` staging cycles per activation
tile. It excludes host/driver gaps and AXI backpressure.

| N | Tile rows | Compute calls | Projected total cycles | At 100 MHz |
|---:|---|---:|---:|---:|
| 1120 | 35 x 32 | 315 | 114,604,945 | 1.14605 s |
| 280 | 8 x 32 + 24 | 81 | 28,806,307 | 0.28806 s |

## Frozen source and exported IP

The HLS source is `source/vision_ffn_down.cpp`, with `RM10_ARCH=4`. Its SHA-256
is `9fa209202f5a5efe65e24ffb813d02155838f0c7e4b4380d2d9896d828495a56`. The exported IP VLNV is
`xilinx.com:hls:vision_ffn_down_tile:1.0`.

- IP package ZIP: `artifacts/ip/export.zip`.
- Vivado IP repository root: `artifacts/ip_repo`.
- Component metadata: `artifacts/ip_repo/xilinx_com_hls_vision_ffn_down_tile_1_0/component.xml`.
- Component SHA-256: `d4843820fcbe07f50ae609af2854b1e87aa6e3d38c1f7928f94d7c1ea2aea1dc`.
- Package ZIP SHA-256: `f285bb72d024c8fb35752c376eab17fad7b18c7163ca89fbe4a3db04dca5d492`.
- Whole package file manifest: `artifacts/ip_repo/SHA256SUMS`.
- Export reproduction: `scripts/export_rm10_a_ra_ip.sh`.

No source changes should be made to this frozen package before route consumes
it. There is no routed WNS/WHS, congestion, board standalone result, or
integrated request result yet.
