# Four-request host MUL_MAT shape comparison

Run order A–D: qid 37804/37852/38169/38299. Each has three matched metadata-traced CPU processes; the table uses case 02 after checking whether exact name/dtype/dimension/stride histograms match cases 03 and 06. All four within-request checks: True/True/True/True.

| Phase | MUL_MAT graph nodes A/B/C/D | Zero-extent nodes A/B/C/D | Nominal MAC pairs, billions A/B/C/D |
|---|---:|---:|---:|
| image_embedding_prefill | 935/935/561/561 | 5/5/3/3 | 174.165/174.165/93.552/96.537 |
| text_prefill | 1122/1122/748/748 | 5/5/3/3 | 26.628/25.135/23.642/23.144 |
| token_decode | 187/2431/374/187 | 0/0/0/0 | 0.752/9.772/1.503/0.752 |
| vision_encoder | 855/855/513/513 | 0/0/0/0 | 1204.542/1204.542/647.011/667.661 |

Selected native GGML M×N×K shapes; parenthesized values are graph-node observations per request:

| Phase / output | A | B | C | D |
|---|---:|---:|---:|---:|
| `vision_encoder` / `node_3` | 1120×1152×588 (5) | 1120×1152×588 (5) | 960×1152×588 (1); 1024×1152×588 (2) | 1024×1152×588 (2); 1056×1152×588 (1) |
| `vision_encoder` / `ffn_up-0` | 4304×1120×1152 (5) | 4304×1120×1152 (5) | 4304×960×1152 (1); 4304×1024×1152 (2) | 4304×1024×1152 (2); 4304×1056×1152 (1) |
| `image_embedding_prefill` / `ffn_up-0` | 3584×70×1024 (5) | 3584×70×1024 (5) | 3584×60×1024 (1); 3584×64×1024 (2) | 3584×64×1024 (2); 3584×66×1024 (1) |
| `token_decode` / `ffn_up-0` | 3584×1×1024 (1) | 3584×1×1024 (13) | 3584×1×1024 (2) | 3584×1×1024 (1) |

The related allocator comparison infers vision/image-prefill graph-window totals of [15, 15, 9, 9]/[15, 15, 9, 9] across A–D. C and D have the same window counts, yet their selected vision and image-prefill `N` dimensions differ. This identifies a shape variable for future tile and buffer feasibility work; it does not establish a faster plan.

The callback observes graph nodes, including zero-extent `MUL_MAT` results in text prefill. A zero-extent node contributes zero nominal MAC pairs and is kept in the inventory; graph-node observations are not isolated executed kernel calls. Nominal MAC pairs are products of the recorded M, N, K and output batch dimensions. They are an arithmetic-work proxy, not measured CPU time, accelerator throughput, memory traffic or an achievable speedup. Exact tensor names, dtypes, dimensions, strides and occurrence counts are in the JSON inventory. No tensor payloads or absolute host addresses are included.

Source evidence is the three `op_trace.jsonl` captures and `run.json` for each fixed development request; their SHA-256 values and the analysis-script hash are recorded in the JSON. The related range-peak comparison is `experiments/derived/textvqa_allocator_metadata_four_request_comparison_audited4_fullpeaks.json`. Host CPU observations do not establish KV260, PL, DDR or end-to-end request benefits.
