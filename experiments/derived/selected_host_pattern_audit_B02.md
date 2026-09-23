# Selected TextVQA host pattern audit (B02)

**Result:** the four selected development requests do contain the expected ordered visual-token patterns. Their logs establish repeated host MTMD encode/decode calls and outer CLI outcomes. They do not establish a crop-to-op mapping, a selector input available before those calls, a K26 failure interval, or a PL benefit.

## Request-level evidence

All four commands used the same pinned host CPU CLI/model configuration, named one image with `--image`, and exited with return code 0. The command records and inference logs are the exact frozen files under `experiments/raw/textvqa_val_dev50_host_q4_cpu_round01/` in this snapshot. Image ID, dimensions, SHA, and ordered batch pattern below are from the frozen workload inventory; the command's image path basename matches the inventory image ID. This snapshot excludes image bytes, so this audit did not independently re-hash the images.

| Qid | Image ID; inventory size and SHA-256 | Logged `n_tokens_batch` order | Calls in raw log | Prompt-eval diagnostic; outer process wall | Evidence available for this selected qid |
|---:|---|---|---|---|---|
| 35950 | `9d85d260f22be0c8`; 1024×633; `225ff76c542d9f49474f60dfeb316e3ca31828b44b3ebaee52dcb3eeec984c30` | `[60,60,60,60,60]` | 5 serial calls; each `n_chunks=1`; `done/total` 1/11, 3/11, 5/11, 7/11, 9/11 | 350 tokens; 8.266 s | command + inference log + resource log; no graph/op or allocator trace |
| 34609 | `181f00d3ee2b2076`; 1024×729; `26401f0395f38a5c780f9d05d0eeba956876ba762159585e8ece52eafb8d1bfd` | `[63,63,63,63,63]` | 5 serial calls; each `n_chunks=1`; `done/total` 1/11 through 9/11 | 364 tokens; 8.394 s | command + inference log + resource log; no graph/op or allocator trace |
| 35419 | `004b75d1299e653c`; 1024×819; `f703a5ce6bbf7c1aa1dd11fda26a7a30323913d404d771d51deba387c840c5f6` | `[63,63,63,63,63,63,63]` | 7 serial calls; each `n_chunks=1`; `done/total` 1/15 through 13/15 | 493 tokens; 11.334 s | command + inference log + resource log, plus a separate 3-run host phase timeline; no graph/op or allocator trace |
| 35005 | `97c8c2c2c6f572f1`; 1024×1024; `2512aeae080117e96813702fc68733be80a4051fc1e871d926306c37a91abdb6` | `[64,70,70,70,70,70,70]` | 7 serial calls; each `n_chunks=1`; `done/total` 1/15 through 13/15 | 540 tokens; 12.757 s | command + inference log + resource log; no graph/op or allocator trace |

The raw log lines for the repeated calls are 227–249 (qid 35950), 227–249 (34609), 227–257 (35419), and 227–257 (35005). They report per-call host encode durations of 1.034–1.410 s, 1.114–1.300 s, 1.098–1.302 s, and 1.091–1.492 s, respectively; the corresponding `image decoded` events are 0.146–0.193 s, 0.142–0.197 s, 0.149–0.200 s, and 0.151–0.300 s. These are single-run host log counters. They are not target-board times, isolated accelerator kernel costs, or physical bytes, and should not be summed into the outer wall time as a disjoint latency decomposition.

The inventory labels prompt-eval counts as runtime diagnostics. Neither those counts nor `n_tokens_batch` are validated pre-dispatch selector fields. `n_chunks=1` is the CLI's count for each logged encode call; it does not identify a physical crop, prove one PL job, or establish cross-call weight reuse.

## Existing shape and dispatch coverage

The selected qids above are marked `already_allocator_traced: false` in the frozen inventory. The independent four-request graph-shape audit covers qids 37804, 37852, 38169, and 38299, not these four. Qid 35419 has an exclusive host phase timeline with seven encoder calls, but that trace does not add graph/op shapes or allocator ranges for qid 35419. No selected row therefore has exact per-op M/N/K, dtype/stride, graph-node count, or allocator lifetime data in this snapshot.

Separately, the pinned-runtime source audit finds graph-node dimensions visible to a backend `supports_op` callback before scheduler compute-buffer allocation. This makes a static shape-keyed lookup a strong available control for an eligible op. It does not prove that the `n_tokens_batch` log is available at that earlier point, that a project selector uses it, or that any resulting dispatch changes K26 performance. Existing arithmetic screening also leaves fixed tile T=8 as a required H1 control.

## Minimal next measurement

To test a future shape/group-dependent claim, first capture one metadata-only trace per pattern at the actual backend eligibility point, tied to the exact request and immutable image hash. Record ordered image-group/crop identity through preprocessing, each graph op's type, dtype, dimensions and strides, the selector-visible fields and decision time, and the selected backend/fallback. This would test metadata availability and shape coverage only. A hardware claim would still require, after all board gates and a separately authorized owner window, an interleaved comparison against the best static shape/tile control with PS/PL assignment, transfer and wait costs, resource high-water marks, original-image-to-first-token and completion time, errors, and quality. Freeze pass/fail thresholds before that comparison.

No new inference, tests, scripts, benchmarks, board access, or answer-label inspection were performed for this audit. These are development examples, not a representative distribution.
