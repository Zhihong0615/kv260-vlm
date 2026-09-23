# B04 static per-op key coverage handoff

## Frozen inputs and integrity

- Worker branch: `agent/B04-static-key-coverage`; worker base and required commit parent: `4d7ce5e5fa5e750833cb5a05b8b3a15364861134` (clean at start).
- B04 task brief: coordinator commit `4d640226786c875a5713a7d16399c49ac7aa2f35`, SHA-256 `c751ab00c8ba3ff698785426b73d9e8d4db816ad87e2652836c2cdd2385c8201`.
- B04 source manifest: same coordinator commit, SHA-256 `a7c610bc01361a20510c2c84d9f45ea6312f0bb521caeabdc1403c9d654e2ef6`. All eight entries passed both before and after analysis.
- Activation gate: R02 PASS `8aa54cbb28bde5a28f33a343b7db071f6afe474a`, integrated at coordinator merge `3e57050f4992ce20b452e43bd4c9bee33cf26436`; canonical B04 activation record at coordinator commit `8eabcb6dc657dca18f1e868a2336ba762cb3ee19`.

| Frozen source artifact | SHA-256 |
|---|---|
| `experiments/raw/textvqa_selected_optrace_B03/run.json` (hash verified; not parsed) | `17101b734bbefb125015fac1d5cfb59798feac289b22269247eaceed06b66209` |
| `experiments/raw/textvqa_selected_optrace_B03/qid_34609_op_trace.jsonl.gz` | `32cb519e717268dd6de4165fd584b084e1259d00811f9ab553fb40d2309377d9` |
| `experiments/raw/textvqa_selected_optrace_B03/qid_35005_op_trace.jsonl.gz` | `9396e8a90238e4ba1288cf90705ab14e7ced7a609c5c2708f5c0a733d59fbec6` |
| `experiments/raw/textvqa_selected_optrace_B03/qid_35419_op_trace.jsonl.gz` | `5e369bf5cfb529e06db69b1c0e54b9638d28ee0b77df37a88f061a04c4a20035` |
| `experiments/raw/textvqa_selected_optrace_B03/qid_35950_op_trace.jsonl.gz` | `3ed0f0352ce0ae0b9ca1fe247e6e5fab44e8b3aab8f9fc0f08085fa5a8082026` |
| `experiments/derived/selected_qid_optrace_B03_group_shapes.json` | `40efebec27671d7dd4a3534e6cdacb5b9e2606ca440893a9f3031ca452eeb36c` |
| `experiments/derived/selected_qid_optrace_B03_summary.json` (hash verified) | `17101b734bbefb125015fac1d5cfb59798feac289b22269247eaceed06b66209` |
| `experiments/derived/selected_qid_optrace_B03.md` | `7c34d4e3b73222c14b6618544bab6518a237b843ca6063778e51ea7804c8498e` |

## Deterministic result

The analyzer keyed every vision node by op plus ordered input/output `(dtype, ne, nb)`, excluding names, IDs, request/group identity, addresses, and storage metadata. All 21,936 of 21,936 vision-node records contain metadata needed to construct a full key, across 24 encoded media batches; this is signature-field completeness, not dispatch or scheduling coverage. The qid node counts are 34609: 4,570; 35005: 6,398; 35419: 6,398; 35950: 4,570. Unique full keys are 66, 131, 72, and 66 respectively (267 across all four).

There are five full-key-set equivalence classes: q34609 groups 0–4 share a class with q35419 group 0; q35005 groups 1–6 share a class; q35005 group 0 is distinct; q35419 groups 1–6 share a class; q35950 groups 0–4 share a class. Sixty-six full keys recur across requests: 65 signatures are shared only by q34609 and q35419, plus one signature shared by all four qids. Each of the other five pairwise intersections therefore contains only that single all-qid signature.

The GEMM-only `(op,M,N,K)` inventory has 44 keys and no collisions with distinct full keys. The coarser `(op,output.ne)` inventory has 233 keys; 30 merge distinct full keys. For example, `MUL_MAT` output `[1152,252,1,1]` merges three full signatures whose input-0 K values are 1152, 4304, and 17216. This is metadata coalescing only.

## Interpretation and recommendation

The full static per-op key represents all observed node type, shape, and stride variation in these traces. Group-set transitions are distinguishable from node metadata without adding group ordinal to the key. Group ordinals denote encoded media-batch calls, not crop identities. The graph callback ran after backend splitting; the traces cannot establish `supports_op` eligibility, final K26 placement, latency, bandwidth, resource pressure, or any accelerator advantage.

Recommendation: reject the narrow question of whether media-group ordinal adds operator-signature information beyond the full static key for these four traces. Retain the full per-op key as the null control. If useful, weaken a future question to whether media-batch sequencing changes measured submission/wait cost; that requires a separate controlled measurement and is not answered here. No novelty or performance claim follows.

## Tool and output hashes

| Artifact | SHA-256 |
|---|---|
| `scripts/analyze_static_key_coverage_B04.py` | `149b6551240734fc85478c4ffd8aaf84e0e6f61d67926dc6836d5c880ae88132` |
| `experiments/derived/static_key_coverage_B04.json` | `12d4649e334f6c48e946b70eb13d2b62bb4bb095b6c4d0354a4f19cf43d24368` |
| `experiments/derived/static_key_coverage_B04.md` | `926ff3988da115c31c5e100de03f355333ac322958167a175f4ad0c1d3133bb2` |
