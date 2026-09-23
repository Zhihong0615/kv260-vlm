# B03 selected-request graph metadata trace

## Result

All four frozen TextVQA host commands produced a successful, metadata-only CPU trace. The trace confirms that each request's ordered `n_tokens_batch` sequence has the same number of media encoder batches, and exposes per-batch vision graph shapes. This is descriptive host evidence. It selects no scheduling method and establishes no K26 performance claim.

## Per-request observation

| Qid | Original image | Existing ordered `n_tokens_batch` | Traced media batches | `inp_raw` shape by media batch | Unique vision `MUL_MAT` shape/stride sets |
|---:|---:|---|---:|---|---:|
| 34609 | 1024×729 | `[63,63,63,63,63]` | 5 | `504×392` in all 5 groups; patch grid `36×28` | 11, same set in every group |
| 35950 | 1024×633 | `[60,60,60,60,60]` | 5 | `560×336` in all 5 groups; patch grid `40×24` | 11, same set in every group |
| 35005 | 1024×1024 | `[64,70,70,70,70,70,70]` | 7 | group 0: `448×448`, grid `32×32`; groups 1–6: `560×392`, grid `40×28` | 11 per group; group 0 differs from groups 1–6, for 22 distinct sets in the request |
| 35419 | 1024×819 | `[63,63,63,63,63,63,63]` | 7 | group 0: `504×392`, grid `36×28`; groups 1–6: `392×504`, grid `28×36` | 11; all groups have the same `MUL_MAT` shape/stride set |

Each captured media group contains 914 vision graph-node records and 11 distinct vision `MUL_MAT` signatures. The callback recorded 22,913–33,207 graph nodes per request across vision, image-embedding prefill, text prefill, and decode. The separate media-batch rows identify group ordinals 0–4 or 0–6 and the corresponding MTMD chunk indexes (odd positions in these prompts). B02's token-batch sequence length matches the traced media-batch count in all four requests.

The shape variation is visible at different levels. Qid 35005 changes the dense matrix sizes after its first group. Qid 35419 changes spatial orientation between groups while retaining the same patch count and dense matrix shape/stride set. Qids 34609 and 35419 share the same dense matrix shape/stride set despite different ordered spatial shapes. A dispatch baseline keyed only by GEMM M/N/K would hide some spatial differences; the strongest static control should key the full op type, dtype, dimensions and strides. Existing pinned-runtime source evidence says those fields are visible to `supports_op` before compute-buffer allocation.

## What this establishes

- Selected single-image requests can expand into five or seven ordered MTMD media-encode groups.
- The group sequence contains both uniform cases and within-request shape transitions. These transitions are genuine in the pinned host preprocessing/graph path, rather than inferred from image dimensions alone.
- Exact graph metadata can support a static shape-and-stride lookup for each op. This is a strong null control for any proposed online or request-level selector.
- The group ordinals identify calls to `mtmd_batch_encode`, not individual crops or internal patches. Count/order alignment does not provide a crop-to-output identity map.

## What it does not establish

This CPU run does not record `supports_op` eligibility results or final K26 backend placement: the ggml eval callback sees graph nodes during scheduled graph computation after backend splitting. It does not measure latency, PS–PL transfer, physical DDR traffic, cache reuse, bank/BRAM/URAM occupancy, CMA behavior, or per-job command overhead. The 4 development requests are not a workload distribution. Although stdout/stderr were discarded and no answer or annotation fields were read, the traces contain graph metadata for the model's decode phase; no decode length or output was used in the analysis.

The result therefore does not rescue any novelty claim. In particular, a policy that selects work from `n_tokens_batch` or a media-group ordinal still must beat a strong static per-op shape-and-stride plan on measured K26 costs. R01's **FAIL** and P3 `NO_GO_NOW` remain unchanged.

## Reproduction and integrity

The worker script verifies all 39 frozen inputs before running. It hashes the full source run manifest as opaque bytes for provenance but does not parse its case fields; it reads each prompt only from the selected frozen `command.json`. The four image files matched the hashes in the B02 inventory. The patched CLI was built from a temporary source copy against runtime `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`; neither the primary checkout nor upstream runtime was edited. One fresh process per qid used the existing command's model, prompt, image, and inference flags with CPU-only settings (`-t 8 -tb 8 -c 4096 -n 48`, seed 42, temperature 0, `--device none`, `-ngl 0`). Generated stdout/stderr were discarded.

Uncompressed and compressed trace SHA-256 values and exact record/node counts are recorded in `experiments/raw/textvqa_selected_optrace_B03/run.json`. Each `.jsonl.gz` trace decompresses to its recorded uncompressed hash; the raw traces compress from 16.3–23.6 MB to 0.64–0.93 MB each. `selected_qid_optrace_B03_group_shapes.json` reproduces the ordered per-group shape summary from those traces.

## Next discriminator

Use the new group trace only to tighten the null model: freeze a full per-op key of op, dtype, `ne`, and `nb`, and determine whether all observed group transitions are statically distinguishable at backend eligibility. If they are, a dynamic selector has no workload-information advantage on these requests. Any remaining candidate would need a separate measured K26 bottleneck—such as group submission/wait cost or a resource/admission cliff—and an interleaved comparison against that exact static plan after the board gate is independently reopened.
