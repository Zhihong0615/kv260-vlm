# B05 ordered media-group trace audit

Evidence level: **offline graph metadata only**. Scope is the vision-encoder node records and `media_batch` boundaries in the four frozen B03 traces. No prompt, image, model, answer, annotation, or run-manifest case contents were inspected.

The full key exactly matches B04: op plus ordered input/output `(dtype, ne, nb)`. Names, IDs, addresses, request/group identity, and storage metadata are excluded. Node order is preserved within each media group.

| Qid | Groups | Vision node records | B04 set fingerprints matched |
|---:|---:|---:|---|
| 34609 | 5 | 4570 | yes |
| 35005 | 7 | 6398 | yes |
| 35419 | 7 | 6398 | yes |
| 35950 | 5 | 4570 | yes |

Across 24 groups, there are 5 key-set classes, 5 multiplicity-preserving unordered classes, 5 ordered-sequence classes, and 5 adjacent-transition-profile classes.

Full-key-set, multiplicity-preserving multiset, ordered-sequence, and adjacent-transition partitions are identical: yes. Classes: 35005:0; 35950:0, 35950:1, 35950:2, 35950:3, 35950:4; 34609:0, 34609:1, 34609:2, 34609:3, 34609:4, 35419:0; 35005:1, 35005:2, 35005:3, 35005:4, 35005:5, 35005:6; 35419:1, 35419:2, 35419:3, 35419:4, 35419:5, 35419:6.

## Per-group fingerprints and boundaries

| Group | Boundary (chunk index; added/total) | Nodes | Unique keys | Set SHA-256 (prefix) | Multiset SHA-256 (prefix) | Ordered sequence SHA-256 (prefix) | Adjacent transitions (distinct/total) |
|---|---:|---:|---:|---|---|---|---:|
| 34609:0 | 1; 1/11 | 914 | 66 | `0b6372fa22ce` | `8ec7a1f91f70` | `9b075c530bbc` | 92/913 |
| 34609:1 | 3; 1/11 | 914 | 66 | `0b6372fa22ce` | `8ec7a1f91f70` | `9b075c530bbc` | 92/913 |
| 34609:2 | 5; 1/11 | 914 | 66 | `0b6372fa22ce` | `8ec7a1f91f70` | `9b075c530bbc` | 92/913 |
| 34609:3 | 7; 1/11 | 914 | 66 | `0b6372fa22ce` | `8ec7a1f91f70` | `9b075c530bbc` | 92/913 |
| 34609:4 | 9; 1/11 | 914 | 66 | `0b6372fa22ce` | `8ec7a1f91f70` | `9b075c530bbc` | 92/913 |
| 35005:0 | 1; 1/15 | 914 | 66 | `1d034382b44b` | `9c3c290e5d34` | `6b2d5bdf3dd0` | 92/913 |
| 35005:1 | 3; 1/15 | 914 | 66 | `04d3072cf49a` | `56ef054c6df5` | `8515922790ef` | 92/913 |
| 35005:2 | 5; 1/15 | 914 | 66 | `04d3072cf49a` | `56ef054c6df5` | `8515922790ef` | 92/913 |
| 35005:3 | 7; 1/15 | 914 | 66 | `04d3072cf49a` | `56ef054c6df5` | `8515922790ef` | 92/913 |
| 35005:4 | 9; 1/15 | 914 | 66 | `04d3072cf49a` | `56ef054c6df5` | `8515922790ef` | 92/913 |
| 35005:5 | 11; 1/15 | 914 | 66 | `04d3072cf49a` | `56ef054c6df5` | `8515922790ef` | 92/913 |
| 35005:6 | 13; 1/15 | 914 | 66 | `04d3072cf49a` | `56ef054c6df5` | `8515922790ef` | 92/913 |
| 35419:0 | 1; 1/15 | 914 | 66 | `0b6372fa22ce` | `8ec7a1f91f70` | `9b075c530bbc` | 92/913 |
| 35419:1 | 3; 1/15 | 914 | 66 | `2f3fc903dfe7` | `9856ba343aa7` | `a82ca6cecd80` | 92/913 |
| 35419:2 | 5; 1/15 | 914 | 66 | `2f3fc903dfe7` | `9856ba343aa7` | `a82ca6cecd80` | 92/913 |
| 35419:3 | 7; 1/15 | 914 | 66 | `2f3fc903dfe7` | `9856ba343aa7` | `a82ca6cecd80` | 92/913 |
| 35419:4 | 9; 1/15 | 914 | 66 | `2f3fc903dfe7` | `9856ba343aa7` | `a82ca6cecd80` | 92/913 |
| 35419:5 | 11; 1/15 | 914 | 66 | `2f3fc903dfe7` | `9856ba343aa7` | `a82ca6cecd80` | 92/913 |
| 35419:6 | 13; 1/15 | 914 | 66 | `2f3fc903dfe7` | `9856ba343aa7` | `a82ca6cecd80` | 92/913 |
| 35950:0 | 1; 1/11 | 914 | 66 | `953b205a18ab` | `f164dde20022` | `71c335edd2e0` | 92/913 |
| 35950:1 | 3; 1/11 | 914 | 66 | `953b205a18ab` | `f164dde20022` | `71c335edd2e0` | 92/913 |
| 35950:2 | 5; 1/11 | 914 | 66 | `953b205a18ab` | `f164dde20022` | `71c335edd2e0` | 92/913 |
| 35950:3 | 7; 1/11 | 914 | 66 | `953b205a18ab` | `f164dde20022` | `71c335edd2e0` | 92/913 |
| 35950:4 | 9; 1/11 | 914 | 66 | `953b205a18ab` | `f164dde20022` | `71c335edd2e0` | 92/913 |

## Same-set, different-sequence pairs

None. No pair of groups has the same full-key set and a different ordered sequence in these four traces.

## Sequence distinctions removed by canonicalization

None: no distinct ordered sequences share an identical multiplicity-preserving full-key multiset.

## Static null and recommendation

Every reconstructed full-key set matches its B04 group fingerprint. Any group distinction visible in the set is already encoded by node metadata. The ordered-sequence and adjacent-transition fingerprints further summarize order; these finite traces do not show that a dynamic group-ordinal selector is necessary. A per-op full-key dispatch plus a static ordered-sequence/replay table is the strongest static null supported here. Media-group ordinals remain encoded-call boundaries, not crop identities.

**Recommendation: stop** pursuing a group-aware dynamic selector from these traces. If measured submission/wait cost becomes a separate question, it needs a separately gated timing experiment against the static sequence/replay table; this audit makes no cost or performance claim.

## Integrity and limits

All 11 frozen manifest entries passed the pre-analysis SHA-256 check; the handoff records the required post-analysis verification. B04 group-set comparison: 24/24 exact matches. The source traces are immutable inputs.

This is a finite audit of four selected development requests. It does not establish crop identity, dynamic selector visibility, backend placement, cost, resource pressure, allocation/liveness, traffic, novelty, or performance. P3 `NO_GO_NOW` remains unchanged.

Source manifest SHA-256: `5a78596606d65b14f5e5d8c4ece10ee79d1cf7454a441209804f36506117bb53`. B04 result SHA-256: `12d4649e334f6c48e946b70eb13d2b62bb4bb095b6c4d0354a4f19cf43d24368`. Analyzer SHA-256: `f4bc5f6b89fb7e1585cf77728fcf695b865520f79ce8d0b6d428e73cb4f59adb`.
