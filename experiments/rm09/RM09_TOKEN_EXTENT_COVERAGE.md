# RM09 FFN-down token-extent coverage

## Result

The current RM07 bitstream and host hook accept only the two numbered
FFN-down extents `N=1120` for layers 0–6 and `N=280` for layers 7–26. These
match media groups with 70 image tokens. The B02 dev50 inventory contains 50
requests and 252 media groups: 140 groups (3,780 of 6,804 numbered FFN-down
calls) have those exact extents. Thus the current shape contract fully covers
22 requests, partially covers 5, and covers none of the groups in the other 23
requests. This is shape coverage only; the unmeasured groups are predictions
from the frozen host inventory and audited shape traces.

## Token count to FFN-down extent

Across the audited requests, each media group has seven FFN-down layers 0–6
with `N = 16 × tokens`, followed by 20 layers 7–26 with `N = 4 × tokens`.
The listed count is the number of those layer calls per group.

| Image tokens in group | Layers 0–6 | Layers 7–26 | Evidence |
|---:|---:|---:|---|
| 70 | 7 × N=1120 | 20 × N=280 | QID37804 board trace; QID35005 host trace |
| 66 | 7 × N=1056 | 20 × N=264 | QID38299 board trace |
| 64 | 7 × N=1024 | 20 × N=256 | QID38299 board trace; QID35005 host trace |
| 63 | 7 × N=1008 | 20 × N=252 | QID35419 host trace |
| 60 | 7 × N=960 | 20 × N=240 | QID35950 host trace |

For QID37804, the board trace records 35 `N=1120` and 100 `N=280` numbered
calls, all completed on PL across five media groups. For QID38299, the full
board trace records 81 numbered calls and zero PL calls: layers 0–6 each have
one `N=1056` and two `N=1024` calls; layers 7–26 each have one `N=264` and two
`N=256` calls. All 81 are `CPU_FALLBACK` with `layer_extent_mismatch`. Its six
additional unnumbered merger/mm.down calls fall back with `unmatched_merger`.

For QID35419, the host trace contains seven groups, each with seven
`K=4304/M=1152/N=1008` FFN-down nodes and 20 `K=4304/M=1152/N=252` nodes.
That predicts 49 and 140 calls respectively for a PS+PL run; QID35419 has not
been run on PS+PL.

## dev50 exact-shape coverage

The support column counts a group only when both layer families match the
current `N=1120/280` contract. Counts are computed from the frozen B02
`ordered_image_batch_tokens` buckets. The exact pattern inventory gives:

| Ordered tokens per request | Requests | Total media groups | Groups matching bitstream | Fully covered requests |
|---|---:|---:|---:|---:|
| `[60,64,64]` | 1 | 3 | 0 | 0 |
| `[66,64,64]` | 4 | 12 | 0 | 0 |
| `[60,60,60,60,60]` | 1 | 5 | 0 | 0 |
| `[63,63,63,63,63]` | 16 | 80 | 0 | 0 |
| `[70,70,70,70,70]` | 22 | 110 | 110 | 22 |
| `[63,63,63,63,63,63,63]` | 1 | 7 | 0 | 0 |
| `[64,70,70,70,70,70,70]` | 5 | 35 | 30 | 0 |
| **Total** | **50** | **252** | **140** | **22** |

Each media group executes 27 numbered FFN-down layers, so shape-supported
coverage is `140 × 27 = 3,780` of `252 × 27 = 6,804` calls (55.56%). Of the 27
requests with any supported groups, 22 have all groups supported and 5 have
six of seven groups supported. The latter five still require CPU fallback for
their 64-token group.

The distinction between measurement and prediction matters. QID37804 directly
confirms five supported groups (135 PL calls); QID38299 directly confirms
three unsupported groups (81 numbered fallbacks). All other dev50 coverage
counts are host predictions based on the exact token-group patterns and
audited graph shapes. QID35419's seven groups are in this predicted category.

## Static contract correction or architecture change?

The HLS source exposes runtime `active_N` and tile coordinates (`n_base`,
`tile_rows`). The host hook advances `n_base` in 32-row tiles; the HLS source
checks that each tile has the expected row count and that `tile_rows` is
divisible by `PE_N=4`. The hard `active_N` allow-list accepts only 280 or 1120;
the host hook separately applies the matching layer-specific equality checks.
All observed extents (240, 252, 256, 264, 960, 1008, 1024, 1056, 1120, and 280)
are divisible by four and at most 1120, so they fit the existing source-level
tile contract.
This makes the QID38299 zero-PL result evidence of the current shape gate, not
evidence that a different compute architecture is required. HLS execution and
routing for newly admitted extents remain unmeasured.

For the observed workload, widening the static shape contract to the needed
4× and 16× token extents is a baseline coverage correction. The smaller
FFN-down layer family uses `N=4×tokens`; for example, `N=252` and `N=264` are
not multiples of 16. An experiment that changes only extent validation and
call accounting, then runs the same tiled datapath correctly on every listed
extent, would falsify an architecture-novelty claim for that change. A novelty
claim would need a separate design-level mechanism and measured benefit over
this exact-shape static baseline, with resource and timing evidence.

## Evidence and reproduction

- B02 dev50 inventory: `orchestration/evidence_snapshots/B02_workload_pattern_audit/experiments/derived/textvqa_dev50_visual_workload_inventory.json`, SHA-256 `dc3b6da619d3947c0022ec1b8f9be5e5bb3e1d9f9204d460108f1017072a25be`.
- B03 QID35005, QID35419, QID35950 host graph traces: `experiments/raw/textvqa_selected_optrace_B03/`; SHA-256 values are recorded in `experiments/raw/textvqa_selected_optrace_B03/run.json`. QID35419 trace: `5e369bf5cfb529e06db69b1c0e54b9638d28ee0b77df37a88f061a04c4a20035`.
- QID37804 board trace: `experiments/rm08/evidence/rm08-vlm-q37804-20260925T063228Z/rm08_pl_trace.txt`, SHA-256 `ded13fa28b9e63ba4af8618a6fd5d860f7bab1b14dd6e7886c96f24c9c56ffd8`.
- QID38299 full board trace copied by the board owner: `/home/zhiro/.codex/worktrees/rm04-dynamic8-integration/kv260-vlm/experiments/rm09/evidence/pl-q38299-20260925T091523Z/q38299-pl-trace.txt`, SHA-256 `4adc72a2fa36891efe4afc5dc410a533121a7b0e544980c505a6bd1b588500a2`.
- Current HLS extent guard and 32-row/4-row-tail checks: `experiments/rm07/source/bounded_k16/vision_ffn_down.cpp`; tile dimensions: `experiments/rm07/source/bounded_k16/vision_ffn_down.hpp`.
- Current host hook extent gate: `experiments/rm08/runtime_patch/llama.cpp-kv260-ffn-down.patch`.

No HLS build, new route, board access, or inference was performed for this
analysis. The inventory and host graph traces are read-only inputs.
