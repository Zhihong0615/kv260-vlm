# RM12 — Arithmetic-density gate and profitable offload

**Decision: `KEEP_RM10_AND_REASSESS_PERFORMANCE_TARGET`.** Retain the measured
heterogeneous split: FFN-up on four A53 cores, FFN-down on the RM10 PL engine.
The same-format specialized multiplier is numerically promising as a scalar
experiment but fails the LUT/throughput feasibility gate. No full-array route,
new bitstream, or additional VLM request was run. No method novelty is claimed.

## Frozen reference and bottleneck

The aligned reference is the corrected RM10 fixed10 source SHA-256
`31a7b26f9bf28c0ad57892184ed30b42126162111fe4c4bda82aa7847754319a`,
IP component SHA-256 `fae7fde4af5b3f5a1237d5e7717ea97622a9a8c6107ba96c97bfe6bb19feda56`,
and board `.bit.bin` SHA-256
`722387cc80b345f0b7b29bdffe61911707cf12c5c25e42867d339b4a0c6fb5d7`.
PL0 is 100 MHz. Its matched route has 323 DSP, 41,431 LUT, 55,317 FF,
8,347/14,640 CLB sites, 18.5 BRAM tiles, 40/64 URAM, and +3.564 ns setup
WNS. The 183-DSP figure belongs to the older RM09 static comparator.

| Attributed part of corrected RM10 | HLS evidence | What remains unknown |
|---|---|---|
| 64 generic F32×F32 multipliers after F16 weight widening | 3 DSP each = 192 DSP; binding latency 4 | Standalone F16→F32 conversion area; no separate module exists |
| 16 recurrent and 48 final-reduction F32 adders | 2 DSP each = 128 DSP | Independent routed CLB cost per adder |
| Other helper/stage arithmetic | HLS top 323 DSP total, 3 beyond named mul/add counts | Detailed RTL attribution for mux/control/addresses |
| K group | II=1; dependence distance 10; 1,076 trips | Independent PE-active cycles |
| Board FFN-down N=1120 call | Stage-X 1.208M cycles; compute task 114.954M cycles; 4.781 GMAC/s kernel | Compute-task split into arithmetic, supply, output or stalls |
| Board FFN-down N=280 call | Stage-X ~0.302M; compute task ~28.894M cycles; 4.756 GMAC/s kernel | Same unknown subcategories |

Compute tasks account for about 98.96% of APM task cycles, but include AXI,
storage access, result stores and possible stalls; **kernel wait is not pure
arithmetic**. APM W+X+Y bytes and effective call payload rates are measured,
but do not establish an independent DDR bandwidth ceiling. The worst routed
setup path is result-tile address to activation-cache URAM enable, mostly net
delay. With +3.564 ns WNS at frozen 100 MHz, shortening that path alone has
no demonstrated present-call throughput benefit. DSP/LUT/FF capacity is not
exhausted; 40/64 URAM and data/control distribution matter for future scaling.

## Same-format scalar arithmetic gate

Both candidates accept F16 weight bits and F32 activation bits and emit a
separately rounded F32 product. Candidate A widens F16 to F32 and uses the
same generic HLS FP multiplier class as RM10. B forms an exact 11×24-bit
significand product and handles normalization/special values with integer
logic. These are *isolated HLS tops*, not 64-lane array implementations.

| Scalar candidate, 10 ns HLS target | DSP | LUT | FF | HLS latency | HLS top interval | HLS estimated delay | CLB sites |
|---|---:|---:|---:|---:|---:|---:|---|
| A, F16 widen + generic F32 multiply | 3 | 453 | 196 | 4 cycles | 5 cycles | 7.016 ns | UNKNOWN; no microkernel place/route |
| B, specialized F16×F32 product | 1 | 2,777 | 141 | 1–4 cycles | 2–5 cycles | 6.907 ns | UNKNOWN; stopped at LUT gate |

B saves two DSP but adds **2,324 LUT per isolated top** and does not improve
the worst-case top interval. The intervals are not an array K-loop II result;
RM10 already has K-loop II=1. A no-sharing 64-lane extrapolation of the LUT
delta is +148,736 LUT, greater than the K26's entire 117,120-LUT capacity.
Top-level overhead would share differently, so this is a feasibility screen,
not a routed array prediction. There is no evidence that B increases effective
GMAC/s or creates room for a profitable wider array. It did not pass the gate
for full-system synthesis or board load.

Candidate B keeps F16 sign/exponent/fraction, including subnormals; finite
products use F32 round-to-nearest, ties-to-even and gradual underflow. It
handles infinities and signed zero, produces canonical quiet NaN for invalid
products, and does not use FMA. Against an independent host-float C-sim path,
all 65,536 F16 bit patterns × 24 F32 edge inputs plus 1,000,000 deterministic
random pairs gave **2,572,864 cases, zero mismatches** for finite outputs and
NaN class. Three captured FFN-up layers supplied **14,874,624 real product
pairs** and **12,912 same-order 10-bank reductions**, again zero A/B mismatch.
NaN payload and exceptional-case bit equivalence to the **generated AMD FPO
RTL** remains UNKNOWN; no claim of bit-exact hardware replacement follows.
There was no full FFN versus captured-output comparison for B because it
failed the hardware resource gate.

## Profitable-offload and request budgets

The FFN-up CPU reference is RM05's earlier instrumented A53 build; the RM11
PL figures are three real standalone calls weighted to the 35 N=1120 and
100 N=280 request distribution. This is a **cross-run budgeting estimate**,
not a 135-call execution or a same-binary paired speedup. In contrast,
QID 38299 and 35419 CPU/RM10 request pairs below use the same runtime,
four threads, frozen input and `/usr/bin/time -v` full-process wall boundary.
That boundary includes model setup and is held fixed within each pair.

| Operator/goal | CPU reference | PL total-call time | Profitability or target budget |
|---|---:|---:|---|
| FFN-up N=1120, one call | 1.431 s | 1.664 s | Need >0.233 s total-call reduction |
| FFN-up N=280, one call | ~0.356 s | ~0.421 s | Need >0.065 s total-call reduction |
| FFN-up 135-call family | 86.440 s | 100.324 s estimated; 80.870 s kernel | At current 19.454 s boundary, kernel must fall below 66.986 s even to break even (1.207× kernel improvement) |
| FFN-up 1.5× family screen | 86.440 s | 100.324 s estimated | PL total <=57.627 s; at current boundary kernel <=38.173 s (2.119× kernel improvement) |
| FFN-down 135-call family | 250.124 s earlier CPU trace | **83.082 s RM10 measured** | Preserve RM10; new shared support cannot materially regress this call time |

With zero FFN-up boundary, the current estimated kernel alone would have only
`86.440/80.870 = 1.069×` CPU headroom. Removing packing/submit by itself
cannot establish a strong FFN-up accelerator. Future operator selection must
rank `CPU_time - PL_total_time`, not functional MAC coverage.

The FFN-up family is 333.192 GMAC. At the present boundary, break-even needs
`>4.974 GMAC/s` kernel throughput; the 1.5× family screen needs
`>=8.728 GMAC/s`. The 64-multiplier, 100 MHz raw roof is 6.4 GMAC/s:
the latter target requires at least **88 parallel multipliers even at 100%
use**, or about 136 at the currently observed ~64.4% up kernel/roof ratio.
Those are arithmetic lower bounds, not a buildable PE configuration; the
candidate B LUT result provides no credible resource path to that expansion.

The whole-request target is defined relative to **same-runtime CPU-only**;
the last column gives the fraction of *RM10's remaining wall* that would have
to be sped up by an effective 5× or 10× complete-call factor (no new boundary).
The infinity value is the absolute minimum coverage. These are arithmetic
ceilings, not projections for candidate B.

| QID / media groups | CPU / RM10 wall | Target | Allowed wall | More time to save | Min remaining-wall coverage, infinite / 5× / 10× |
|---|---:|---:|---:|---:|---:|
| 38299 / 3 | 368.51 / 285.53 s | 2× | 184.255 s | 101.275 s | 35.5% / 44.3% / 39.4% |
| 38299 / 3 | 368.51 / 285.53 s | 4× | 92.128 s | 193.403 s | 67.7% / 84.7% / 75.3% |
| 38299 / 3 | 368.51 / 285.53 s | 5× | 73.702 s | 211.828 s | 74.2% / 92.7% / 82.4% |
| 35419 / 7 | 822.35 / 619.70 s | 2× | 411.175 s | 208.525 s | 33.6% / 42.1% / 37.4% |
| 35419 / 7 | 822.35 / 619.70 s | 4× | 205.588 s | 414.113 s | 66.8% / 83.5% / 74.2% |
| 35419 / 7 | 822.35 / 619.70 s | 5× | 164.470 s | 455.230 s | 73.5% / 91.8% / 81.6% |

For remaining-wall coverage `p` at complete-call speedup `s`, savings are
`p(1-1/s)`. Even the 2× request target needs roughly one third of RM10's
remaining wall eliminated by ideal hardware. A small FFN-up-only change
cannot deliver a 4× or 5× request result. No fusion experiment is justified
without a measured reduction in repeated DDR reads, supply cycles or
intermediate materialization; the current up boundary estimate alone is
insufficient, and nonlinear/bias/residual ordering must remain intact.

## Milestone disposition and evidence

The current same-format arithmetic specialization reduces DSP but worsens
LUT density, with no established throughput improvement and no array route.
The addressed URAM enable path is a **conditional** target only if a later
denser candidate fails place/route; present 100 MHz timing passes and its
board-cycle impact is unmeasured. Keep RM10 and reassess the desired
end-to-end target against the measured opportunity table. Do not run a known
slower unified FFN request or restart broad scheduler/precision sweeps.

Primary data and source are in [resource/cycle attribution](../rm12_a_resource/RM12_A_RESOURCE_CYCLE_ATTRIBUTION.md)
with its two CSVs, and [arithmetic probe handoff](../rm12_arithmetic/HANDOFF.md)
with `source/`, `evidence/hls/{A,B}/`, `evidence/real_tensors/`, and a checked
SHA-256 manifest. The prior board context is [RM11 milestone](../rm11/RM11_MILESTONE_RESULTS.md).
