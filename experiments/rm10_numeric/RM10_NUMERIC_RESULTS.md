# RM10 numeric gate: recurrence-decoupled candidates

Status: **numeric PASS; HLS source-order cross-check passed**. The full captured
QID 37804 tensors were compared for all three reduction candidates. Every
candidate/layer meets the frozen RM09 gate: max absolute error ≤ `1e-3`, RMSE
≤ `1e-4`, cosine ≥ `0.999`. The evaluator's operation order was cross-checked
against `experiments/rm10_hls/source/vision_ffn_down.cpp`, SHA-256
`367854f27a9d30b152e85999bc7c8d0a92cf731593062f9d6fe1bbfd9777c1c2`.
This is still a numeric result only; HLS C-simulation, synthesis, route, and
board throughput are separate gates.

The capture is the corrected AArch64 CPU run described in
`experiments/rm06/RM06_RESULTS.md` (runtime SHA-256
`e019f99ff8c736f75785556438350d0fea8c05896cdf8adf044c60cacedbb34c`). Input
payloads are not committed. Their checksums are recorded in
[`capture_tensor_sha256.txt`](capture_tensor_sha256.txt) and match the RM06
capture record.

## Exact arithmetic and reduction order

All candidates convert binary16 weights exactly to binary32, multiply F32 W by
F32 X with a separately rounded FP32 multiply, accumulate in FP32 from `+0.0f`,
and return F32. The evaluator compiles with `-fno-fast-math -ffp-contract=off`;
inspection of the compiled evaluator found no fused multiply-add opcode.

- **A, `A_interleave_R5`:** use 16 residue lanes `p=k%16`; for group `g=0..268`,
  update bank `g%5` with product `k=16*g+p`. Per lane, left-fold banks 0..4,
  then left-fold lane results 0..15.
- **B, `B_split4_aligned`:** four K ranges `[0,1088)`, `[1088,2176)`,
  `[2176,3264)`, `[3264,4304)` (68/68/68/65 groups of 16). Each segment has
  16 global residue accumulators, updates in increasing K order, and left-folds
  lanes 0..15. Reduce segment sums as `(S0+S1)+(S2+S3)`.
- **C, `C_hybrid_R5_tree`:** use A's partial sums; per lane reduce as
  `(b0+b1)+(b2+b3)`, then add `b4`; finally left-fold lanes 0..15.

## Full-tensor metrics

| Layer | Candidate | Max abs | RMSE | Cosine | Gate |
|---|---|---:|---:|---:|---|
| `ffn_down-0` | A interleave R=5 | 1.14440918e-5 | 1.74393945e-7 | 0.999999999999829 | PASS |
| `ffn_down-0` | B aligned split-4 | 1.14440918e-5 | 1.72512434e-7 | 0.999999999999820 | PASS |
| `ffn_down-0` | C hybrid R=5 + tree | 1.14440918e-5 | 1.74621565e-7 | 0.999999999999798 | PASS |
| `ffn_down-13` | A interleave R=5 | 1.95950270e-6 | 1.03207764e-7 | 0.999999999999795 | PASS |
| `ffn_down-13` | B aligned split-4 | 2.20537186e-6 | 1.02934156e-7 | 0.999999999999776 | PASS |
| `ffn_down-13` | C hybrid R=5 + tree | 1.95950270e-6 | 1.03097807e-7 | 0.999999999999825 | PASS |
| `ffn_down-26` | A interleave R=5 | 2.44140625e-4 | 5.27860901e-6 | 0.999999999999943 | PASS |
| `ffn_down-26` | B aligned split-4 | 2.74658203e-4 | 5.22375879e-6 | 0.999999999999895 | PASS |
| `ffn_down-26` | C hybrid R=5 + tree | 2.44140625e-4 | 5.28761933e-6 | 0.999999999999922 | PASS |

Complete precision metrics are in
[`summary.csv`](results/captured_q37804/summary.csv). Absolute-error histogram
counts for all nine rows are in
[`absolute_error_histogram.csv`](results/captured_q37804/absolute_error_histogram.csv).
Each run used all `N*M` outputs: 1,290,240 for layer 0 and 322,560 each for
layers 13 and 26.

## Reproduction

With the corrected RM06 capture files in `TENSOR_DIR`, run:

```bash
OMP_NUM_THREADS=16 experiments/rm10_numeric/source/run_numeric_probe.sh \
  TENSOR_DIR experiments/rm10_numeric/results/captured_q37804
```

The committed runner compiles `reduction_probe.cpp` with C++17, OpenMP, `-O3`,
`-fno-fast-math`, and `-ffp-contract=off`. The run log is
[`run.log`](results/captured_q37804/run.log).
