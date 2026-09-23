# R02 independent review — B03 selected op traces

**Verdict: FAIL for the activated exact-base acceptance predicate.** The frozen inputs, trace artifacts, request/image identities, group counts, and bounded interpretation claims pass independent review. One P2 provenance finding remains: the B03 commit is based on a different parent than the activation's frozen worker base. P0: 0 · P1: 0 · P2: 1.

## Review binding

- `review_mode: independent_static_artifact_review`
- `reviewer_role: independent reviewer`
- Reviewed B03 commit: `4d7ce5e5fa5e750833cb5a05b8b3a15364861134`.
- B03 direct parent: `2f31453557cdbb1501cdda33c52c32e0a3ef7cf2`.
- Reviewer branch/worktree: `agent/R02-B03-review`, created at the exact B03 commit above. The review deliverables are the only additions planned on this branch; no B03 source or experiment artifact is changed.
- Frozen activation record: `orchestration/activations/B03.md`, which names `1909bef4aa0558fed04c00fead7b6f68180e4684` as the worker base (lines 3–4) and requires a clean worker based exactly on that base (line 10).
- Evidence boundary: this review uses only the frozen B03 snapshot and files committed in the reviewed B03 tree. No primary-checkout files, raw runs outside the frozen snapshot, network, or chat history were used. No tests, dry plans, syntax checks, benchmarks, SSH, board commands, or inference were run.

## Source and artifact integrity

The complete 39-entry manifest `orchestration/evidence_snapshots/B03_selected_qid_optraces/SOURCE.sha256` passed SHA-256 verification. The manifest's own SHA-256 is `3dfd1d0e05f7c9db0d2aca90c0c0006a59834877a3b747f792a48b4616536c44`. The assigned scope in `orchestration/task_briefs/TASK_B03.md:18–22` limits reads to the four frozen command records and verified images, discards CLI stdout/stderr, hashes prompt text without recording it, and records media-batch identity as distinct from crop identity.

The committed builder, runner, analyzer, and derived artifacts match the handoff hashes in `orchestration/handoffs/B03_selected_qid_optrace_handoff.md:8`:

| Artifact | SHA-256 |
|---|---|
| `scripts/build_optrace_cli_B03.py` | `e60f9634bccf55447d78b21027016c7df864873536da4e28c1b2b4480293d61e` |
| `scripts/run_selected_optrace_B03.py` | `a8032756358a305b50ca136cb94cb84eed41c4185db08cb5fbd4942b09e7047d` |
| `scripts/analyze_selected_optrace_B03.py` | `917aa781e8db64b3a417e55947f50dd3fa05e814654e6adfdb25a06e53abe15b` |
| `experiments/raw/textvqa_selected_optrace_B03/run.json` and `experiments/derived/selected_qid_optrace_B03_summary.json` | `17101b734bbefb125015fac1d5cfb59798feac289b22269247eaceed06b66209` |
| `experiments/derived/selected_qid_optrace_B03_group_shapes.json` | `40efebec27671d7dd4a3534e6cdacb5b9e2606ca440893a9f3031ca452eeb36c` |
| `experiments/derived/selected_qid_optrace_B03.md` | `7c34d4e3b73222c14b6618544bab6518a237b843ca6063778e51ea7804c8498e` |

I independently decompressed each committed trace, recomputed its compressed and uncompressed hashes, parsed each JSONL row, and checked every row's `request_id` and `image_sha256` against the matching run record. Record/node counts and hashes are:

| Qid | JSONL records / graph nodes | Compressed SHA-256 | Decompressed SHA-256 |
|---:|---:|---|---|
| 34609 | 24,329 / 24,324 | `32cb519e717268dd6de4165fd584b084e1259d00811f9ab553fb40d2309377d9` | `bc7d1bdef36ee86867eb548810c67f410c44c59bb1319255d6d0bbb10109a7c7` |
| 35005 | 33,214 / 33,207 | `9396e8a90238e4ba1288cf90705ab14e7ced7a609c5c2708f5c0a733d59fbec6` | `489c95ae5851e85416a6cac6352b9694f23eff399c391a085aec22666bc03c7e` |
| 35419 | 33,214 / 33,207 | `5e369bf5cfb529e06db69b1c0e54b9638d28ee0b77df37a88f061a04c4a20035` | `054b5518e23eb2cdfc6b056b2afccdbbf261d99df5b3d4b046ab3ce45cf051f2` |
| 35950 | 22,918 / 22,913 | `3ed0f0352ce0ae0b9ca1fe247e6e5fab44e8b3aab8f9fc0f08085fa5a8082026` | `02a0b1ccec00bf24732f47ea1d3b34c97104a737068f637ca63e5929a2b964a3` |

The four selected command-record hashes and image hashes in `run.json` correspond to the fixed request map in `scripts/run_selected_optrace_B03.py:26–54`; the runner reads only those four `command.json` records (`:175–193`) and verifies model, mmproj, and image identity (`:186–204`). Prompt text is reduced to SHA-256 (`:241`); stdout/stderr are sent to `DEVNULL` (`:206–210`). The committed raw output directory contains only `run.json` and the four compressed traces. The committed summaries and trace rows contain no CLI output, prompt text, generated answer, or answer/annotation fields. No CLI output was opened during this review.

## Independent group and signature audit

The 914 count is **per media-batch group**, not per request. I independently counted `vision_encoder` node records by group; the counts are 914 for every group. Request totals are therefore 4,570 for each five-group trace (34609 and 35950) and 6,398 for each seven-group trace (35005 and 35419), matching the run records. The derived table also gives 914 in each `vision_node_count` field (`experiments/derived/selected_qid_optrace_B03_group_shapes.json`, e.g. lines 36, 77, 265, and 576). The B02 token-batch list lengths match the media-batch counts: 5, 7, 7, and 5 respectively.

| Qid | Media groups | Per-group `inp_raw` width × height |
|---:|---:|---|
| 34609 | 5 | 504×392 for all groups |
| 35005 | 7 | 448×448 for group 0; 560×392 for groups 1–6 |
| 35419 | 7 | 504×392 for group 0; 392×504 for groups 1–6 |
| 35950 | 5 | 560×336 for all groups |

For qid 35419 I recomputed per-group complete vision signatures from trace rows using operation, output dtype/`ne`/`nb`, and each input dtype/`ne`/`nb`. Each orientation has 66 unique signatures: group 0 versus group 1 shares 60 and differs by six (one `CONT`, one `IM2COL`, one `PERMUTE`, three `RESHAPE` signatures); groups 1–6 have identical full signature sets. The 11-signature `MUL_MAT`-only set is identical across all seven groups; its SHA-256 in the group-shape summary is `180c7b50e9802686f70c0dc4c82500e69c31c6c99f60ef564a659198c31065f6`. Thus the note's distinction between shared dense-matrix inventory and orientation-sensitive full op signatures is correct (`experiments/derived/selected_qid_optrace_B03.md:14,18`). A static lookup over full op/dtype/dimensions/strides is a credible strong null; a lookup over `MUL_MAT` signatures alone would not distinguish these orientations.

## Tracer semantics and claim limits

- The local patch increments `pm_next_vision_group` immediately before each `mtmd_batch_encode` and writes the group ordinal, chunk index, and chunk counts (`scripts/build_optrace_cli_B03.py:152–157`). It identifies encode-call/media-batch order, not individual crops or patches; the task brief and note correctly preserve this limit (`orchestration/task_briefs/TASK_B03.md:21`, `experiments/derived/selected_qid_optrace_B03.md:25`).
- The callback records node and tensor metadata only (`scripts/build_optrace_cli_B03.py:84–107`). The selected CPU runs enable the vision and text eval callbacks (`:142–144`, `:166`), while timing/allocator/debug environment switches are removed and stdout/stderr discarded (`scripts/run_selected_optrace_B03.py:199–210`).
- The frozen task brief states the callback is reached during scheduled graph computation after backend splitting, not during `supports_op` eligibility or as final placement evidence (`orchestration/task_briefs/TASK_B03.md:24–29`). The handoff, run metadata, and interpretation note retain these limits (`orchestration/handoffs/B03_selected_qid_optrace_handoff.md:11–13`, `experiments/derived/selected_qid_optrace_B03.md:27–31`). The CPU traces establish no K26 placement, latency, physical traffic, resource occupancy, board feasibility, or method advantage.
- The static-shape/stride control is appropriately framed as the strongest null, but remains a proposed control rather than a measured backend dispatch comparison. The artifact supports that it can separate the observed qid 35419 orientation groups using the full signature, not that it improves execution.

## Finding

| Priority | Finding | Exact condition, consequence, and bounded fix |
|---|---|---|
| P2 | **Activation/base provenance mismatch** | `orchestration/activations/B03.md:3–4,10` freezes `1909bef4aa0558fed04c00fead7b6f68180e4684` as the exact worker base. The reviewed B03 commit's actual parent is `2f31453557cdbb1501cdda33c52c32e0a3ef7cf2`, and the handoff names that parent (`orchestration/handoffs/B03_selected_qid_optrace_handoff.md:3`). Between those commits, `orchestration/task_briefs/TASK_B03.md:19` was changed to require reading only the four frozen `command.json` records and not parsing the full run manifest. The resulting trace provenance is auditable and the later instruction is narrower, so this does not undermine trace identity or metadata claims. It does mean the activated requirement “based exactly on the frozen base” is not met as recorded. For a future run, refresh the activation to name the actual worker-start SHA after task-brief changes, then branch exactly there; preserve this run's trace artifacts and record the lineage correction in orchestration metadata. |

## Gate disposition

Source-manifest, selected-input, trace-hash, JSONL identity, redaction, group-count, and bounded-claim checks pass. **The current activated gate is not fully satisfied** because its exact-base acceptance predicate fails as documented above. This review does not change global go/no-go status or authorize any experiment or board activity.
