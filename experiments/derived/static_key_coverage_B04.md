# B04 static per-op key coverage

This offline analysis covers vision-encoder graph-node metadata in four frozen B03 traces. It does not read prompt, image, model, answer, or annotation artifacts.

| Qid | Vision node records | Distinct full keys | Signature fields complete | Groups: full-key uniques | GEMM M/N/K keys | Op/output-shape keys |
|---:|---:|---:|---:|---|---:|---:|
| 34609 | 4570 | 66 | 100% | 0:66, 1:66, 2:66, 3:66, 4:66 | 11 | 58 |
| 35005 | 6398 | 131 | 100% | 0:66, 1:66, 2:66, 3:66, 4:66, 5:66, 6:66 | 22 | 115 |
| 35419 | 6398 | 72 | 100% | 0:66, 1:66, 2:66, 3:66, 4:66, 5:66, 6:66 | 11 | 62 |
| 35950 | 4570 | 66 | 100% | 0:66, 1:66, 2:66, 3:66, 4:66 | 11 | 58 |

All 21,936 vision records contain metadata needed to construct a full key; there are 267 distinct full keys. Full-key-set equivalence classes: 5. 66 full keys recur across requests.

Group-set classes: 35005:1, 35005:2, 35005:3, 35005:4, 35005:5, 35005:6; 34609:0, 34609:1, 34609:2, 34609:3, 34609:4, 35419:0; 35005:0; 35419:1, 35419:2, 35419:3, 35419:4, 35419:5, 35419:6; 35950:0, 35950:1, 35950:2, 35950:3, 35950:4.

Coarser GEMM M/N/K keys: 44 keys, 0 merge multiple full keys. Op/output-shape keys: 233 keys, 30 merge multiple full keys. The JSON lists each collision and the full-key digests it merges.

Example: `MUL_MAT` output `[1152,252,1,1]` has three full keys with input-0 K values [1152, 4304, 17216]; output-shape-only merges them, while M/N/K separates them.

The full static key represents all observed per-node shape/type/stride variation in these traces. Group ordinal is not needed to distinguish a node signature; different group key sets are distinguished by their node metadata. Treat media groups as encoded media-batch calls, not crop identities.

## Evidence boundary

The recorded graph callback runs after backend splitting. This analysis cannot validate `supports_op` eligibility, backend placement, or final K26 behavior. Coarse-key collisions are metadata collisions only; they do not imply cost, placement failure, bandwidth, pressure, or performance. No latency or hardware claim follows.

Source group-summary SHA-256: `40efebec27671d7dd4a3534e6cdacb5b9e2606ca440893a9f3031ca452eeb36c`. Analyzer SHA-256: `149b6551240734fc85478c4ffd8aaf84e0e6f61d67926dc6836d5c880ae88132`.
