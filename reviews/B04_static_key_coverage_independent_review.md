# R03 independent review — B04 static-key coverage

**Verdict: PASS.** B04 is bound to the activated exact target, all frozen inputs and activation-named outputs pass their hash checks, and independent trace-only recomputation matches the reported key counts, classes, intersections, and collision totals. The interpretation correctly limits the results to offline graph metadata. P0: 0 · P1: 0 · P2: 0.

## Review binding

- `review_mode: independent_trace_recomputation`
- `reviewer_role: independent reviewer`
- Reviewed B04 target: `966fbf5372a0e1f47f11da999a9298625233870a`.
- Exact target parent: B03 `4d7ce5e5fa5e750833cb5a05b8b3a15364861134`.
- Reviewer branch/worktree: `agent/R03-B04-review`, clean at the exact B04 target before review.
- R03 activation: `/home/zhiro/research/kv260-vlm-orchestration/orchestration/review_activations/R03.md`, SHA-256 `03569ce789f19b4d974cd4acb5116fb1b99515d9666e7dc0d12941c1e3f88d41`.
- Frozen B04 input manifest: coordinator commit `4d640226786c875a5713a7d16399c49ac7aa2f35`, `orchestration/evidence_snapshots/B04_static_key_coverage/SOURCE.sha256`, SHA-256 `a7c610bc01361a20510c2c84d9f45ea6312f0bb521caeabdc1403c9d654e2ef6`. All eight entries pass against the reviewed target tree.
- Activity boundary: no inference, prompt/image/model/answer/annotation artifacts, tests, benchmarks, source edits, board actions, GitHub activity, or changes to global go/no-go were made. The run metadata and B03 summaries listed below were hash-verified only; the independent counts were computed from the four compressed traces.

## Frozen input and output integrity

All eight manifest entries passed SHA-256 verification:

| Frozen input | SHA-256 | Review use |
|---|---|---|
| `experiments/raw/textvqa_selected_optrace_B03/run.json` | `17101b734bbefb125015fac1d5cfb59798feac289b22269247eaceed06b66209` | Hash only |
| `experiments/raw/textvqa_selected_optrace_B03/qid_34609_op_trace.jsonl.gz` | `32cb519e717268dd6de4165fd584b084e1259d00811f9ab553fb40d2309377d9` | Parsed for independent counts |
| `experiments/raw/textvqa_selected_optrace_B03/qid_35005_op_trace.jsonl.gz` | `9396e8a90238e4ba1288cf90705ab14e7ced7a609c5c2708f5c0a733d59fbec6` | Parsed for independent counts |
| `experiments/raw/textvqa_selected_optrace_B03/qid_35419_op_trace.jsonl.gz` | `5e369bf5cfb529e06db69b1c0e54b9638d28ee0b77df37a88f061a04c4a20035` | Parsed for independent counts |
| `experiments/raw/textvqa_selected_optrace_B03/qid_35950_op_trace.jsonl.gz` | `3ed0f0352ce0ae0b9ca1fe247e6e5fab44e8b3aab8f9fc0f08085fa5a8082026` | Parsed for independent counts |
| `experiments/derived/selected_qid_optrace_B03_group_shapes.json` | `40efebec27671d7dd4a3534e6cdacb5b9e2606ca440893a9f3031ca452eeb36c` | Hash only |
| `experiments/derived/selected_qid_optrace_B03_summary.json` | `17101b734bbefb125015fac1d5cfb59798feac289b22269247eaceed06b66209` | Hash only |
| `experiments/derived/selected_qid_optrace_B03.md` | `7c34d4e3b73222c14b6618544bab6518a237b843ca6063778e51ea7804c8498e` | Hash only |

The four output hashes named in the R03 activation also match the reviewed B04 tree:

| Output | SHA-256 |
|---|---|
| `scripts/analyze_static_key_coverage_B04.py` | `149b6551240734fc85478c4ffd8aaf84e0e6f61d67926dc6836d5c880ae88132` |
| `experiments/derived/static_key_coverage_B04.json` | `12d4649e334f6c48e946b70eb13d2b62bb4bb095b6c4d0354a4f19cf43d24368` |
| `experiments/derived/static_key_coverage_B04.md` | `926ff3988da115c31c5e100de03f355333ac322958167a175f4ad0c1d3133bb2` |
| `orchestration/handoffs/B04_static_key_coverage_handoff.md` | `c0e6ed34815db7a96eb9b86a91fce570e20c1bd5596a2b5f706e49cb9e37f8f0` |

## Independent recomputation from the four traces

I streamed the four compressed JSONL traces directly. Each contained only node and media-batch records; request IDs matched the corresponding filename, group ordinals were contiguous, and every vision-node row had the fields needed to form a full key. No B03 run or summary JSON was parsed to derive these metrics.

| Qid | JSONL records | All graph nodes | Vision nodes | Media groups | Vision nodes per group | Unique full keys per group | Request full keys | GEMM M/N/K keys | Op/output-shape keys |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 34609 | 24,329 | 24,324 | 4,570 | 5 | 914 | 66 each | 66 | 11 | 58 |
| 35005 | 33,214 | 33,207 | 6,398 | 7 | 914 | 66 each | 131 | 22 | 115 |
| 35419 | 33,214 | 33,207 | 6,398 | 7 | 914 | 66 each | 72 | 11 | 62 |
| 35950 | 22,918 | 22,913 | 4,570 | 5 | 914 | 66 each | 66 | 11 | 58 |
| **Total** | **103,675** | **103,651** | **21,936** | **24** | **914 each** | **66 each** | — | — | — |

The traces contain 24 media groups (5 + 7 + 7 + 5). Every group has 914 vision nodes and 66 distinct full keys. All 21,936 vision records have complete key fields.

### Exact group-set equivalence classes

I compared each group's set of complete full-key digests, not just the number of keys. The 24 groups form these five classes:

1. `34609:0–4` and `35419:0`.
2. `35005:0` alone.
3. `35005:1–6`.
4. `35419:1–6`.
5. `35950:0–4`.

Thus equal per-group cardinalities (66) do not imply equal full-key sets. The two qid 35005 shape regimes and the two qid 35419 orientation regimes remain distinct by their full node signatures; group ordinals themselves were not included in those signatures.

### Cross-request full-key intersections

| Qid pair | Shared unique full keys |
|---|---:|
| 34609 / 35005 | 1 |
| 34609 / 35419 | 66 |
| 34609 / 35950 | 1 |
| 35005 / 35419 | 1 |
| 35005 / 35950 | 1 |
| 35419 / 35950 | 1 |

The intersection common to all four requests contains exactly one key. Across the union of 267 full keys, 65 occur only in qids 34609 and 35419, one occurs in all four, and the other 201 occur in a single request (130 qid-35005-only, 6 qid-35419-only, 65 qid-35950-only). These counts reproduce the handoff's stated 66 recurring full keys and pairwise pattern.

### Coarse-key collisions

| Coarse key | Unique keys | Coarse keys mapping to multiple distinct full keys | Collision detail |
|---|---:|---:|---|
| `MUL_MAT` `(M,N,K)` | 44 | 0 | Every observed M/N/K key maps to one full signature. |
| `(op, output.ne)` | 233 | 30 | 8 `ADD`, 4 `CPY`, 4 `FLASH_ATTN_EXT`, 4 `GET_ROWS`, 8 `MUL_MAT`, and 2 `RESHAPE` coarse keys merge multiple full signatures. |

As a checked example, `MUL_MAT` with output shape `[1152,252,1,1]` maps to three full signatures with input-0 K values `1152`, `4304`, and `17216`. The output-shape key merges those signatures; the M/N/K key distinguishes them. “Collision” here means only that the coarse metadata key maps to multiple complete signatures.

## Key semantics and limits

The canonical full key in `scripts/analyze_static_key_coverage_B04.py:40–54` is the op plus ordered input and output dtype, `ne`, and `nb` vectors. It excludes names, pointer IDs, request/group identity, addresses, flags, and storage metadata. The GEMM key is limited to `MUL_MAT` and uses `M=output.ne[0]`, `N=output.ne[1]`, `K=input[0].ne[0]` (`:105–123`, `:264–269`). The shape-only key is op plus output `ne` and intentionally drops input signatures, dtype, and strides (`:105–107`, `:264–269`). Collision counts use the number of distinct full-key digests mapped by each coarse key (`:244–255`).

The analyzer also reads the hash-verified B03 group-shape summary to obtain the expected qid set, compressed trace hashes, and group counts (`scripts/analyze_static_key_coverage_B04.py:61–67,148–159`). Its per-node keys and key-set statistics are formed from trace rows. This independent recomputation used only the four compressed traces for the reported record, key, intersection, and collision values.

The output accurately calls 100% “signature-field completeness,” not dispatch coverage (`experiments/derived/static_key_coverage_B04.md:5–12`). Its limitations state that media-group ordinals identify encoded media-batch calls rather than crops, and that the graph callback runs after backend splitting; these traces cannot validate `supports_op` eligibility, final K26 placement, performance, bandwidth, or resource pressure (`experiments/derived/static_key_coverage_B04.md:20–24`; `scripts/analyze_static_key_coverage_B04.py:291–295`). The recommendation is appropriately narrow: keep the full per-op key as the static null, reject an ordinal-only signature-information claim for these four traces, and make no novelty or performance claim.

## Findings and gate result

No P0, P1, or P2 issue was found. The exact target/parent requirement, eight-input hash check, four activation output hashes, independent trace metrics, canonical-key semantics, and evidence-limit claims all pass. **R03 verdict: PASS.** This review does not integrate B04, change the P3 `NO_GO_NOW` gate, or authorize additional experiments.
