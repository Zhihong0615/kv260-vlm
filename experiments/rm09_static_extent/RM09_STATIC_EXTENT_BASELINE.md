# RM09 static FFN-down extent baseline

## Result

The RM07 tiled datapath already handles the audited extents. Its only hard N
gate blocked them. This candidate changes that gate to `4 <= active_N <= 1120`
and `active_N % 4 == 0`; the host patch keeps an exact per-layer whitelist for
the observed workloads. K=4304, M=1152, F16 W × F32 X → F32 accumulation and
reduction order, 32-row activation cache, four-row compute granularity, and
bounded W/X/Y staging are unchanged.

QID38299's 81 numbered calls are therefore shape-admissible (subject to a new
bitstream and runtime being built and loaded); QID35419's predicted N=1008/252
calls are also admissible. The audited dev50 inventory's five token groups
cover all 252 media groups / 6,804 numbered FFN-down calls, versus 140 groups /
3,780 calls under the frozen N=1120/280 gate. These are coverage counts, not
new board measurements.

## C-simulation and golden checks

Vitis HLS 2024.2 C-simulation used deterministic generated inputs for the four
new representative extents. Each case computed the final token tile and one
128-output band, then compared every produced value bit-for-bit against a CPU
golden that uses the same 16-lane FP32 partial sums and final reduction order.
It also checked that padded tail rows were not written.

| N | Final tile | Compared outputs | Max abs error |
|---:|---:|---:|---:|
| 1008 | base 992, 16 rows | 2,048 | 0 |
| 252 | base 224, 28 rows | 3,584 | 0 |
| 1056 | base 1024, 32 rows | 4,096 | 0 |
| 264 | base 256, 8 rows | 1,024 | 0 |

The non-four-aligned N=1006 was rejected. Frozen N=1120/280 remain covered by
the archived RM07 real-tensor C-simulation results in `experiments/rm07/`;
those frozen captures are not available at the new extents, so the added cases
use generated goldens.

## One HLS synthesis and RM07 comparison

One `csynth_design` ran for the candidate on xck26-sfvc784-2LV-c at a 5.0 ns
target. The compute K loop remained II=5, 269 iterations, 1,360 cycles, and 52
FP32 multiplier instances. HLS estimated 265.32 MHz (3.769 ns), matching the
RM07 estimate. These are HLS estimates; the candidate was not routed.

| HLS top resource | RM07 | Extent baseline | Delta |
|---|---:|---:|---:|
| DSP | 184 | 183 | -1 |
| LUT | 73,995 | 74,385 | +390 (+0.53%) |
| FF | 60,445 | 60,583 | +138 (+0.23%) |
| BRAM18 | 54 | 54 | 0 |
| URAM | 40 | 40 | 0 |

The widened guard kept the estimated Fmax unchanged, with a small LUT/FF
increase. Vivado route, board loading, and board timing were not run.

## Per-shape schedule model

Vitis leaves top-level runtime latency as `?` because `active_N` and tile loop
counts are arguments. The table below is a composed **no-stall HLS schedule
model**, not a measured per-shape run or board latency. It uses the candidate
report's 8,612-cycle weight-tile load, 5,982 cycles per four-token compute
group, 2 cycles per packed output word plus 4 cycles of pack overhead, and the
unchanged RM07 activation-stage cost of `538 × rows + 15`. One compute command
processes eight weight tiles; each token tile uses nine 128-output commands.

```text
compute(rows) = 8 × (8612 + (rows / 4) × 5982 + 2 × rows + 4)
stage(rows)   = 538 × rows + 15
op(N)         = full_tiles × (stage(32) + 9 × compute(32))
                + tail_term, when N mod 32 != 0
```

| Tokens | Wide extent / tiles | Wide cycles per FFN-down op | Narrow extent / tiles | Narrow cycles per FFN-down op |
|---:|---|---:|---|---:|
| 60 | 960 / 30×32 | 122,634,690 | 240 / 7×32 + 16 | 30,968,856 |
| 63 | 1008 / 31×32 + 16 | 129,076,608 | 252 / 7×32 + 28 | 32,269,152 |
| 64 | 1024 / 32×32 | 130,810,336 | 256 / 8×32 | 32,702,584 |
| 66 | 1056 / 33×32 | 134,898,159 | 264 / 8×32 + 8 | 34,189,815 |
| 70 | 1120 / 35×32 | 143,073,805 | 280 / 8×32 + 24 | 35,923,543 |

The token-70 model is 0.058% above RM07's archived 142,990,645 / 35,902,735
cycles per operation because this candidate synthesis reports 8,612 / 5,982
cycles for those loop units versus RM07's 8,611 / 5,978. The result supports a
coverage-baseline correction: the shape restriction was not an architecture
barrier. The added validation has a small estimated area cost and no estimated
clock-rate penalty.

## Reproduction and artifacts

Run `scripts/rm09/run_static_extent_csim.sh` and
`scripts/rm09/run_static_extent_hls.sh`. Both place build products under
`/tmp`; the completed runs were:

- C-sim root: `/tmp/rm09-static-extent-csim-20260925T095635Z-104491`
- HLS synthesis root: `/tmp/rm09-static-extent-20260925T095753Z-105433`
- Candidate HLS top report: `project/solution1/syn/report/vision_ffn_down_tile_csynth.rpt`
- Candidate K-loop report: `project/solution1/syn/report/p_anonymous_namespace_compute_weight_batch_Pipeline_VITIS_LOOP_97_9_csynth.rpt`
