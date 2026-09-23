# Independent raw-trace review: four-request host MUL_MAT shapes

Date: 2026-09-23. The reviewer parsed all 12 raw `op_trace.jsonl` files for qids 37804, 37852, 38169 and 38299 without calling `compare_matmul_shapes_across_allocator_runs.py`. For each `MUL_MAT` graph node, it checked `K=src0.ne[0]=src1.ne[0]` and `output.ne[0:2]=[src0.ne[1],src1.ne[1]]`, then recomputed node counts, zero extents, selected M×N×K distributions and the nominal product `M*N*K*output.ne[2]*output.ne[3]`. The reviewed derived JSON has SHA-256 `d7ff1e08955e4b8d3b0598f957ecbbdbf970da01055190ad5c79270712ef4082`; it records each source trace SHA-256.

| Qid | Phase | Graph nodes | Zero-extent nodes | Nominal MAC pairs |
|---:|---|---:|---:|---:|
| 37804 | image embedding prefill | 935 | 5 | 174,165,196,800 |
| 37804 | text prefill | 1,122 | 5 | 26,627,635,200 |
| 37804 | token decode | 187 | 0 | 751,663,104 |
| 37804 | vision encoder | 855 | 0 | 1,204,542,259,200 |
| 37852 | image embedding prefill | 935 | 5 | 174,165,196,800 |
| 37852 | text prefill | 1,122 | 5 | 25,134,790,656 |
| 37852 | token decode | 2,431 | 0 | 9,771,620,352 |
| 37852 | vision encoder | 855 | 0 | 1,204,542,259,200 |
| 38169 | image embedding prefill | 561 | 3 | 93,551,591,424 |
| 38169 | text prefill | 748 | 3 | 23,641,946,112 |
| 38169 | token decode | 374 | 0 | 1,503,326,208 |
| 38169 | vision encoder | 513 | 0 | 647,011,270,656 |
| 38299 | image embedding prefill | 561 | 3 | 96,537,280,512 |
| 38299 | text prefill | 748 | 3 | 23,144,331,264 |
| 38299 | token decode | 187 | 0 | 751,663,104 |
| 38299 | vision encoder | 513 | 0 | 667,660,566,528 |

Within each request, the three trace processes agree on these values and on the selected target shape counts. Qid 38169 and 38299 have identical vision/image-prefill graph-window totals, but one vision `ffn_up-0` node has `N=960` versus `N=1056`, respectively; their image-prefill `ffn_up-0` variant has `N=60` versus `N=66`. The remaining two windows in each phase use common `N=1024` (vision) and `N=64` (image prefill) shapes. The derived report reproduces these distributions without discrepancy.

Every zero-extent `MUL_MAT` node has `N=0`, `M=248094`, and `K=1024`; it is a `result_output` node and contributes zero nominal MAC pairs. All observed input/output batch dimensions in these 12 traces are one. Thus the formula is checked for this dataset, but nonunit batch behavior was not independently exercised. Graph-node observations are not timed executed kernels, and nominal MAC pairs are an arithmetic proxy rather than CPU time, DDR traffic or PL throughput. No hardware work was performed.
