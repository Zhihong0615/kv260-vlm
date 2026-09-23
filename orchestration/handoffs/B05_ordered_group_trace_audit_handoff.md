# B05 ordered media-group trace audit handoff

## Scope and conclusion

Offline analysis of only `vision_encoder` node records and `media_batch` boundaries in the four frozen B03 compressed traces. The reconstructed full key is exactly B04's key: op plus ordered input/output `(dtype, ne, nb)`, excluding names, IDs, addresses, group/request identity, and storage metadata.

All 24 groups match B04's full-key-set fingerprint. Their five full-key-set classes, five multiplicity-preserving multiset classes, five ordered-sequence classes, and five adjacent-transition-profile classes have identical membership. There are **no** same-set/different-sequence pairs and no distinct sequences that collapse to the same sorted full-key multiset. Each group has 914 vision node records and 913 adjacent transitions; every group has 92 distinct adjacent transitions.

**Recommendation: stop** pursuing a group-aware dynamic selector based on these records. The strongest static null is per-op full-key dispatch plus a static ordered-sequence/replay table. A measured submission/wait-cost question would require a separately gated timing experiment; this audit makes no cost or performance claim.

## Frozen start and target SHAs

- Worker branch: `agent/B05-ordered-group-trace-audit`.
- Worker start/base SHA: `f7ad31d98ba96846c2a7522f114f6e310f63b19b` (clean at start).
- Frozen analysis target/base SHA: `f7ad31d98ba96846c2a7522f114f6e310f63b19b`; it remains unchanged as the direct parent.
- Final target is the containing single commit on this branch. Its exact SHA is recorded by Git/review activation and in the task completion message; the handoff cannot embed its own containing commit SHA.

## Frozen input integrity

Source manifest: `orchestration/evidence_snapshots/B05_ordered_group_trace_audit/SOURCE.sha256`, SHA-256 `5a78596606d65b14f5e5d8c4ece10ee79d1cf7454a441209804f36506117bb53`. All eleven listed artifacts passed `sha256sum -c` both before and after analysis.

| Frozen source artifact | SHA-256 |
|---|---|
| `experiments/raw/textvqa_selected_optrace_B03/qid_34609_op_trace.jsonl.gz` | `32cb519e717268dd6de4165fd584b084e1259d00811f9ab553fb40d2309377d9` |
| `experiments/raw/textvqa_selected_optrace_B03/qid_35005_op_trace.jsonl.gz` | `9396e8a90238e4ba1288cf90705ab14e7ced7a609c5c2708f5c0a733d59fbec6` |
| `experiments/raw/textvqa_selected_optrace_B03/qid_35419_op_trace.jsonl.gz` | `5e369bf5cfb529e06db69b1c0e54b9638d28ee0b77df37a88f061a04c4a20035` |
| `experiments/raw/textvqa_selected_optrace_B03/qid_35950_op_trace.jsonl.gz` | `3ed0f0352ce0ae0b9ca1fe247e6e5fab44e8b3aab8f9fc0f08085fa5a8082026` |
| `experiments/derived/selected_qid_optrace_B03_group_shapes.json` | `40efebec27671d7dd4a3534e6cdacb5b9e2606ca440893a9f3031ca452eeb36c` |
| `experiments/derived/selected_qid_optrace_B03_summary.json` | `17101b734bbefb125015fac1d5cfb59798feac289b22269247eaceed06b66209` |
| `experiments/derived/static_key_coverage_B04.json` | `12d4649e334f6c48e946b70eb13d2b62bb4bb095b6c4d0354a4f19cf43d24368` |
| `experiments/derived/static_key_coverage_B04.md` | `926ff3988da115c31c5e100de03f355333ac322958167a175f4ad0c1d3133bb2` |
| `scripts/analyze_static_key_coverage_B04.py` | `149b6551240734fc85478c4ffd8aaf84e0e6f61d67926dc6836d5c880ae88132` |
| `orchestration/handoffs/B03_selected_qid_optrace_handoff.md` | `b912cf55582a4df05bb4c45ce300e235675b14171efa728db7d37abdf7fdd5ec` |
| `orchestration/handoffs/B04_static_key_coverage_handoff.md` | `c0e6ed34815db7a96eb9b86a91fce570e20c1bd5596a2b5f706e49cb9e37f8f0` |

## Deliverables and hashes

| Output | SHA-256 |
|---|---|
| `scripts/analyze_ordered_group_trace_B05.py` | `f4bc5f6b89fb7e1585cf77728fcf695b865520f79ce8d0b6d428e73cb4f59adb` |
| `experiments/derived/ordered_group_trace_audit_B05.json` | `82bd9f9bcb565513cc4da69caef69768a065788fb41224e4c335323b21870299` |
| `experiments/derived/ordered_group_trace_audit_B05.md` | `17081eb3e8c31fdab649617a0157191102e36c68c1338b721a2417d11794cb37` |

This handoff is part of the containing commit and is identified by that commit's Git SHA.

## Reproduction and checks

From the worker root, reproduce the deterministic analysis with:

```sh
python3 scripts/analyze_ordered_group_trace_B05.py
```

The analyzer reads the four compressed traces in order, considers only `media_batch` boundaries and `vision_encoder` nodes, reconstructs B04's exact full key, and compares full-key sets, multiplicity-preserving multisets, ordered sequences, and adjacent-key transition counts. It checks reconstructed key-set fingerprints against frozen B04 output before writing deterministic JSON and Markdown reports.

Checks performed: required branch/start SHA and clean status; all eleven frozen source hashes before and after the analysis; 24/24 reconstructed group-set fingerprints matched B04; final commit direct parent and clean status. No tests, syntax checks, inference, board/SSH action, runtime/source edit, answer/annotation inspection, or GitHub activity occurred. P3 `NO_GO_NOW` is unchanged.

## Limits

These are four selected development requests and 24 encoded media-batch calls. Group ordinals are not crop identities. Identical graph metadata does not establish equal cost, backend placement, runtime selector visibility, allocation/liveness, traffic, resource pressure, novelty, or performance. No dynamic-selector or hardware-cost claim follows.
