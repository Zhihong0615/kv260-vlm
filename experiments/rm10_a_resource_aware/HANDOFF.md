# RM10 A revision: ten-bank recurrence fix

Status: ten-bank source is frozen in this commit. HLS C-sim, HLS synthesis, and
full-top C/RTL co-simulation pass. Full-tensor numeric gate for the changed
10-bank reduction order is pending; route/board measurements are not claimed.

## Correctness audit and repair

The earlier five-bank source package is **invalid for route/board use**. Its
HLS schedule loaded selected `accum` at ST_26 and stored the new value at ST_35,
a nine-stage gap, while the bank was revisited after only five loop iterations.
The HLS report also explicitly warned: `Assuming false dependence as a
"true/false" selection was not specified` for the pragma
`variable=accum inter distance=5`. That pragma did not encode the intended true
RAW recurrence. The old C-sim could not expose the scheduled RTL feedback issue.
The old source/report narrative is retained in `HANDOFF_FIVE_BANK_SUPERSEDED.md`
and its original Git commit.

The current A implementation uses ten temporal banks and explicitly declares
`#pragma HLS DEPENDENCE variable=accum inter true distance=10`. In fresh HLS
schedule evidence, the accumulator read is at ST_25 and store is at ST_34.
Thus the next same-bank read at group distance 10 occurs one iteration after
the prior store. HLS records the true dependence pragma without a false-
dependence warning. The bound recurrence FAdd is latency 7, II=1.

## HLS and RTL evidence

| Measure | Result |
|---|---:|
| Issue products per 4x4 output group | 64 |
| K groups | 1076 |
| K-loop achieved II / latency | 1 / 1109 cycles |
| K-loop interval / total helper latency | 1077 / 1111 cycles |
| K-loop mapped FP32 multipliers | 64 |
| K-loop mapped FP32 accumulation adders | 16 |
| Total bound FP32 adders across design | 64 |
| Total HLS resources | 323 DSP, 47,075 LUT, 50,368 FF, 54 BRAM18, 40 URAM |
| HLS estimated Fmax | 259.26 MHz |

The 10-bank C-simulation passes all 4096 output lanes. Full-top RTL
co-simulation also passes all 4096 lanes for the existing two-transaction
`tile_rows=4` testbench, which executes the full 1076-group K reduction across
the output batches and exercises repeated bank revisits. The captured log is
`evidence/a_ra_fixed10/hls/csim_csynth_cosim.log`.

Detailed HLS reports and verbose schedule/binding evidence are in
`evidence/a_ra_fixed10/hls/`.

## Full-operation schedule projection

These are schedule-derived projections, not board measurements. The updated
per-compute-call projection uses the fresh 4600-cycle n-block loop schedule:
`8*(8612 + (tile_rows/4)*4600 + (2*tile_rows+3))`. Activation staging is
`538*tile_rows+3` cycles per activation tile.

| N | Projected cycles | At 100 MHz |
|---:|---:|---:|
| 1120 | 115,209,745 | 1.15210 s |
| 280 | 28,957,507 | 0.28958 s |

The projection covers the frozen invocation tiling, including nine output
batches per activation tile. It excludes host/driver gaps and AXI backpressure.

## Numerical status

F16 weights, F32 activations, and F32 accumulation/output are unchanged. The
10-bank balanced reduction order differs from the prior five-bank evaluator;
therefore its prior numeric metrics are not reused. The exact real-tensor gate
for layers 0/13/26 is pending and must pass max abs <= 1e-3, RMSE <= 1e-4,
cosine >= 0.999 before board use.

## Frozen source and IP

- Source: `source/vision_ffn_down.cpp` compiled with `RM10_ARCH=4`.
- Source SHA-256: `31a7b26f9bf28c0ad57892184ed30b42126162111fe4c4bda82aa7847754319a`.
- IP repository: `artifacts/ip_repo`.
- IP component: `artifacts/ip_repo/xilinx_com_hls_vision_ffn_down_tile_1_0/component.xml`.
- Component SHA-256: `fae7fde4af5b3f5a1237d5e7717ea97622a9a8c6107ba96c97bfe6bb19feda56`.
- Export ZIP: `artifacts/ip/export.zip`.
- Export ZIP SHA-256: `b54c4ac0a15dc4501c3d1d470eeb2664fe9e2e60cf0d9ba7a0cfd9fdcca82e6b`.
- Package-file manifest: `artifacts/ip_repo/SHA256SUMS`.
