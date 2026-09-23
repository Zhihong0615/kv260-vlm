# B05 ordered media-group trace audit — independent review

- **review_mode:** independent offline recomputation
- **reviewer_role:** independent reviewer
- **Verdict:** PASS
- **Findings:** P0: 0 · P1: 0 · P2: 0
- **Frozen target:** `dbaf1372342b7535b33200a49a3711269d28fa07`
- **Required direct parent:** `f7ad31d98ba96846c2a7522f114f6e310f63b19b`
- **Reviewer branch:** `agent/R05-B05-review`

## Identity and manifest verification

The B05 target worktree was clean at the frozen target, whose direct parent is the required B04 SHA. The target commit adds only the declared analyzer, JSON report, Markdown report, and B05 handoff. The independent reviewer worktree is on the exact target SHA and was clean before review.

R05 activation `orchestration/review_activations/R05.md` SHA-256: `5e36c19f66ff2c4f42356cecd0731d63036386adff6980216622bd6cf6a5a6e9`. R05 brief SHA-256: `cc5416b9eda959e0c085423c38f8ccd945814e0ab637dc690f96fca0961c9b0c`. R05 review manifest SHA-256: `7655393de3df976895319abebdb91d50fee228ea60451cab5c80d243fa7f833f`. All six entries passed from the B05 repository root. B05 activation SHA-256: `0f2abb9ffd942065f7e4041c79328afd66562d0b34b3bb1c5eb6ebd80db2879a`.

The B05 source manifest at `orchestration/evidence_snapshots/B05_ordered_group_trace_audit/SOURCE.sha256` has SHA-256 `5a78596606d65b14f5e5d8c4ece10ee79d1cf7454a441209804f36506117bb53`. All eleven entries passed verification from the B05 repository root, so the manifest’s root-relative paths were checked from the correct base.

### R05 manifest entries

| Path | SHA-256 |
|---|---|
| `scripts/analyze_ordered_group_trace_B05.py` | `f4bc5f6b89fb7e1585cf77728fcf695b865520f79ce8d0b6d428e73cb4f59adb` |
| `experiments/derived/ordered_group_trace_audit_B05.json` | `82bd9f9bcb565513cc4da69caef69768a065788fb41224e4c335323b21870299` |
| `experiments/derived/ordered_group_trace_audit_B05.md` | `17081eb3e8c31fdab649617a0157191102e36c68c1338b721a2417d11794cb37` |
| `orchestration/handoffs/B05_ordered_group_trace_audit_handoff.md` | `b9d6c588cdc197515be15bbf063222c8ecc8fdc5372a6134dcb97ea0f019e157` |
| `orchestration/task_briefs/TASK_B05.md` | `fb356d917450a69bc5014d8d08c6c5d9aae014dbded5862de04679d259ac82d3` |
| `orchestration/evidence_snapshots/B05_ordered_group_trace_audit/SOURCE.sha256` | `5a78596606d65b14f5e5d8c4ece10ee79d1cf7454a441209804f36506117bb53` |

### Eleven B05 frozen source entries

| Path | SHA-256 |
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

## Independent recomputation

I read the four frozen compressed traces and independently reconstructed keys and group partitions without running the submitted B05 analyzer. The canonical full key matches B04: op plus ordered input and output tensor signatures, each containing `dtype`, `ne`, and `nb`; names, IDs, addresses, group/request identity, and storage metadata are excluded. The definitions match in B05 `scripts/analyze_ordered_group_trace_B05.py:42-61` and frozen B04 `scripts/analyze_static_key_coverage_B04.py:40-58`. B05’s marker parsing, sequence construction, and multiset/transition calculations are at `scripts/analyze_ordered_group_trace_B05.py:90-160`.

I treated each `media_batch` record as a boundary and included only records marked `node` with `phase == vision_encoder`, assigning them by their recorded group ordinal. I recomputed the compressed and decompressed hashes, canonical key digests, per-group boundaries, node counts, unique-key sets, multiplicity-preserving multisets, ordered sequences, and adjacent-transition profiles. The results match every per-group field in the B05 JSON output.

| Qid | Nonempty trace records | Groups | Boundary markers (chunk index; added/total) | Vision nodes |
|---:|---:|---:|---|---:|
| 34609 | 24,329 | 5 | 1, 3, 5, 7, 9; each 1/11 | 4,570 |
| 35005 | 33,214 | 7 | 1, 3, 5, 7, 9, 11, 13; each 1/15 | 6,398 |
| 35419 | 33,214 | 7 | 1, 3, 5, 7, 9, 11, 13; each 1/15 | 6,398 |
| 35950 | 22,918 | 5 | 1, 3, 5, 7, 9; each 1/11 | 4,570 |

All 24 groups contain 914 vision nodes, 66 unique full keys, and 913 adjacent transitions, with 92 distinct adjacent key pairs per group. The independently recomputed compressed and decompressed SHA-256 values match the B05 result JSON:

| Qid | Compressed trace SHA-256 | Decompressed trace SHA-256 |
|---:|---|---|
| 34609 | `32cb519e717268dd6de4165fd584b084e1259d00811f9ab553fb40d2309377d9` | `bc7d1bdef36ee86867eb548810c67f410c44c59bb1319255d6d0bbb10109a7c7` |
| 35005 | `9396e8a90238e4ba1288cf90705ab14e7ced7a609c5c2708f5c0a733d59fbec6` | `489c95ae5851e85416a6cac6352b9694f23eff399c391a085aec22666bc03c7e` |
| 35419 | `5e369bf5cfb529e06db69b1c0e54b9638d28ee0b77df37a88f061a04c4a20035` | `054b5518e23eb2cdfc6b056b2afccdbbf261d99df5b3d4b046ab3ce45cf051f2` |
| 35950 | `3ed0f0352ce0ae0b9ca1fe247e6e5fab44e8b3aab8f9fc0f08085fa5a8082026` | `02a0b1ccec00bf24732f47ea1d3b34c97104a737068f637ca63e5929a2b964a3` |

All 24 reconstructed set fingerprints match frozen B04. The set, multiset, ordered-sequence, and adjacent-transition partitions are identical and each has five classes:

1. `35005:0`
2. `35950:0–4`
3. `34609:0–4` with `35419:0`
4. `35005:1–6`
5. `35419:1–6`

Both requested pairwise result sets are empty: same full-key set but different ordered sequence; same multiplicity-preserving multiset but different ordered sequence. The additional same-set/different-multiplicity set is empty as well. No sequence difference is erased by multiset canonicalization in these four traces.

## Claim-boundary assessment

The report and handoff match the recomputed results. They appropriately recommend stopping the dynamic group-aware-selector investigation on these four traces: all group distinctions in the set, multiplicity, sequence, and adjacent-transition partitions coincide. They preserve a separately gated timing experiment against the per-op full-key plus ordered-sequence/replay null if submission or wait cost becomes a question.

The media-batch ordinal represents an encoded-call boundary; the traces do not establish crop identity. The report does not infer backend placement or selection, runtime selector visibility, allocation/liveness, traffic, resource pressure, novelty, cost, or performance. This finite offline metadata audit cannot establish a method claim or change P3 `NO_GO_NOW`.

No tests, syntax checks, benchmarks, answer/annotation reads, inference, board/SSH, reboot, bitstream activity, or GitHub work occurred. The submitted B05 analyzer was inspected statically but not run. Only frozen trace, B04 summary/source, B05 analysis output/source, and handoff evidence within the verified manifests were used.
