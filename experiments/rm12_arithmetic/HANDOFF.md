# RM12 Worker B — F16-weight × F32-activation product probe

Status: **stop the precision-specialized microkernel route**. The existing RM10
operator does not use the 11-bit F16 significand width: HLS binds a generic
32×32 F32 multiplier. A mixed 24×11 significand product cuts the isolated DSP
count from three to one, but the correctly rounded special-value path raises
the isolated HLS LUT estimate by 2,324 LUTs and does not establish a useful
throughput gain. No full-array synthesis, place/route, or board image was run.

## Aligned RM10 evidence

The inspected source is the frozen ten-bank RM10 source, SHA-256
`31a7b26f9bf28c0ad57892184ed30b42126162111fe4c4bda82aa7847754319a`; its
packaged component SHA-256 is
`fae7fde4af5b3f5a1237d5e7717ea97622a9a8c6107ba96c97bfe6bb19feda56`.
The generated AMD Floating-Point Operator wrapper is
`fmul_32ns_32ns_32_5_max_dsp_1`: both input ports and the result are 32 bits,
each fraction width is 24 bits, and `C_MULT_USAGE=3`. The bound fixed10 HLS
report has 64 such multiplier instances in the K loop, each charged 3 DSP and
145 LUT, with operator binding latency 4. The K loop itself reaches II=1.
This establishes that widening the half weight did not let AMD HLS infer an
11-bit multiplier.

Those operator counts are from the aligned fixed10 binding report, not an
extrapolation from an older image. The corrected RM10 Vivado route reports
323 DSP, 41,431 LUT, and 8,347/14,640 CLB sites, with +3.564 ns WNS at the
100 MHz constraint. The recorded worst setup path is memory/address/control
routing rather than the F32 multiplier path.

## Candidates and measured HLS result

Both scalar tops accept `(weight_bits:16, activation_bits:32)` and return one
F32 product as 32 bits. A is the existing exact half-to-F32 conversion
followed by a separately rounded C++ F32 multiply. B decodes both operands,
forms the exact 11×24-bit significand product, normalizes it, and rounds once
to F32. The HLS script targets the KV260 part at 10 ns (100 MHz).

| Candidate | Product operator | DSP | LUT | FF | HLS latency | HLS top interval | Estimated delay |
|---|---|---:|---:|---:|---:|---:|---:|
| A, conversion + F32 multiply | `fmul_32ns_32ns_32_3_max_dsp_1` | 3 | 453 | 196 | 4 cycles | 5 cycles | 7.016 ns |
| B, F16×F32 specialized | `mul_24ns_11ns_35_1_1` | 1 | 2,777 | 141 | 1–4 cycles | 2–5 cycles | 6.907 ns |

The table is for the complete isolated HLS top, including its conversion,
rounding/control, and `ap_ctrl_hs` interface. It is not a pure operator-core
area comparison. Both estimated delays are below 10 ns. B's best-case interval
comes from short exceptional paths; its worst-case interval is the same as A.
The top is not loop-pipelined, so these intervals do not establish a K-loop
throughput improvement. RM10 already issues its K loop at II=1.

A no-sharing screen that scales the measured isolated LUT delta
(`2,777 - 453 = 2,324 LUT`) over 64 simultaneous products gives +148,736 LUT,
above the whole device's 117,120-LUT capacity. Treat this only as a conservative
feasibility screen: top-level control and interface logic will not replicate
exactly like product logic, and it is not a full-kernel estimate or routed
prediction. Standalone CLB mapping was not run after this LUT gate failed; no
CLB improvement is claimed.

## Arithmetic semantics and limits

- For finite F16 weights, `B` decodes sign, 5-bit exponent, and 10-bit
  fraction. Normal values use `(1024+fraction) × 2^(exponent-25)`; subnormal
  values use `fraction × 2^-24`. Thus every nonzero F16 subnormal expands to a
  normal F32 value exactly; it is not flushed to zero.
- F32 activation normals use a 24-bit significand and exponent offset
  `field-150`; F32 subnormals use their fraction times `2^-149`. Their exact
  significands are multiplied (up to 35 bits) and the product is rounded to
  F32 round-to-nearest, ties-to-even. F32 output underflow is gradual. The
  product sign is the XOR of operand signs, including signed zero and infinity.
- Any NaN input and `0 × infinity` produce canonical positive quiet NaN
  `0x7fc00000` in B. The regression treats any NaN payload as equivalent; it
  does not establish bit-for-bit payload equivalence with AMD FPO RTL or the
  routed RM10 image. That hardware special-case comparison remains **unknown**.
- No multiply-add fusion is used. B emits a separately rounded F32 product;
  any external F32 accumulator and reduction order remain separate and must be
  kept unchanged by a future integration.

## Numerical validation

The independent software reference is candidate A's `float` multiplication,
compiled in Vitis C simulation with `-fno-fast-math -ffp-contract=off`. Candidate
B uses integer significand arithmetic and does not call A's conversion or
multiplication path.

- Boundary/random C simulation checked all 65,536 F16 bit patterns against 24
  F32 edge values, plus 1,000,000 deterministic random pairs: **2,572,864 total,
  zero mismatches**. Finite outputs, signed zeros, infinities, and subnormal
  products are compared bitwise; NaNs are compared by NaN class.
- The QID 37804 board-captured FFN-up W/X inputs for layers 0, 13, and 26 were
  read from the RM11 capture directory. Its `tensors.sha256` was checked at the
  source directory; no tensor payload was copied here. The probe covered every
  captured F16 weight (4,958,208 per layer), pairing it with a real captured
  activation using `n=m mod N`. Across all layers that is **14,874,624 real
  product pairs** and **12,912 same-order 10-bank reductions**, with zero
  A/B mismatches. This checks product equivalence on real values and preserves
  the reduction order in the probe; it is not a full FFN-vs-captured-output
  comparison, and it does not verify AMD FPO RTL NaN payload behavior.

Raw Vitis HLS logs, C-simulation summaries, reports, and generated operator
wrappers are under `evidence/hls/{A,B}/`. The real-tensor input checksums and
probe log are under `evidence/real_tensors/`.

## Prior-art scope

XtraMAC explicitly identifies promotion of low-precision inputs into AMD FPO's
fixed high-precision datapath as the mixed-precision baseline and reports that
specialized mantissa products can reduce resource use. Its public core applies
FTZ/DAZ behavior, so it is not a drop-in arithmetic reference for this task.
[XtraMAC paper](https://arxiv.org/abs/2605.06052) ·
[FloPoCo FPMult documentation](https://www.flopoco.org/operators_5.0.git.html)
describes different widths for the two inputs and result plus correctly-rounded
operation, but says this mixed-width component interface is not exposed through
the command line. Neither source provides evidence that a custom implementation
will fit the current KV260 workload better than the measured HLS probe.

## Reproduction

```bash
RM12_VARIANT=A bash experiments/rm12_arithmetic/scripts/run_hls.sh
RM12_VARIANT=B bash experiments/rm12_arithmetic/scripts/run_hls.sh
bash experiments/rm12_arithmetic/scripts/run_real_tensor_probe.sh \
  /home/zhiro/research/kv260-vlm-workers/RM11-A-unified/experiments/rm11_unified_ffn/evidence/board_capture/q37804-cpu/results/tensors
```

The microkernel probes are complete. Do not proceed to a full array or route
from this branch: the measured LUT delta fails the no-go gate, and the current
engine's loop and routed critical path offer no arithmetic-throughput opening.
