# RM02-A: KV260 CPU-only MiniCPM-V baseline

**Result: BOARD_MEASURED.** Three distinct frozen TextVQA requests completed end to end on the KV260 CPU path. The first QID 38299 attempt was recovered after a worker-finalization bug, then repeated successfully with normal receipts. No PL bitstream was loaded.

## Board and pinned runtime

- Board: KV260, AArch64, four Cortex-A53 CPUs at 1,333,333 kHz; kernel `5.15.0-1027-xilinx-zynqmp`; swap 0; reboot-required marker absent. XRT reported device ready. Jupyter remained active; apt-daily services were inactive and PackageKit reported `ao 0` (no transactions).
- Runtime: MiniCPM-V 4.6, `MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf` SHA-256 `8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773`; `mmproj-MiniCPM-V-4.6-f16.gguf` SHA-256 `ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293`; llama.cpp commit `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`; board CLI SHA-256 `84bfa2f5f91f13503b5a1349e05594cda30c01613227187cfb9e48e7b805f1d7`.
- Every VLM request used 2 CPU threads, `--device none -ngl 0`, and the pinned image/request manifest. The recorded owner-window source was the user's RM02 authorization; no external reservation was created.
- Temperature is `UNKNOWN` because no readable thermal zones were exposed. TTFT is `UNKNOWN`; the CLI did not provide a reliable board-side first-visible-token boundary. Stage values below are copied from runtime log messages and are not independent or additive phase timers.

## Completed requests

| QID / run | Image SHA-256 | Board wall | Peak RSS | Board output | Host comparison | TextVQA soft score |
|---|---|---:|---:|---|---|---:|
| 38299 / r01 initial smoke | `4365f84b5d2cbc5c740bafde088b1aeaf5c7b8326c8b9b5bfe2a529f9bc7a256` | 670.99 s | 1,854,160 KiB | `3` | Host output `3`; exact match. Host wall 5.1073 s at 8 threads; board was about 131.4× slower. Both board and host scored 0.0. | 0.0 |
| 38299 / r02 frozen-set repeat | same | 669.89 s | 1,854,276 KiB | `3` | Exact match with the host output `3`; host baseline as above. | 0.0 |
| 37804 / r03 | `3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f` | 1,233.09 s | 1,862,748 KiB | `G` | Host output `G`; exact match. Host wall 8.17 s at 8 threads. The existing host trace also reports 7,194.450 ms online input-to-done and 7,172.008 ms to first visible token, with model/context initialization outside that interval; these are not whole-request wall times. | 1.0 |
| 35419 / r03 | `f703a5ce6bbf7c1aa1dd11fda26a7a30323913d404d771d51deba387c840c5f6` | 1,485.64 s (24:45.64) | 1,860,348 KiB | `SUPREME SHERIFF'S` | Host output `SHERIFF'S`; mismatch. Host wall 11.33 s at 8 threads, about 131.2× faster than this 2-thread board run. | 0.0 |

The frozen set covered 3, 5, and 7 runtime-observed image-encoding batches for QIDs 38299, 37804, and 35419 respectively. The extra 38299 r01 smoke is not counted as another distinct request. The r02 non-start records for QIDs 37804 and 35419 (`PRIOR_CASE_STOP_RULE`) are preserved; successful runs use fresh r03 IDs.

## Runtime-reported phase entries

These are the exact categories and intervals printed by the pinned CLI. Treat them as runtime-reported measurements: they overlap with other work and must not be summed to infer wall time.

| QID / run | `mtmd batch encoding done` | `image decoded` | Prompt eval | Decode eval |
|---|---:|---:|---:|---:|
| 38299 / r01 | 204.273, 193.881, 194.440 s (592.594 s total) | 17.499, 16.868, 16.946 s (51.313 s total) | 657.945 s / 240 tokens | 0.509 s / 1 run |
| 38299 / r02 | 203.417, 194.151, 194.708 s (592.276 s total) | 17.477, 16.854, 17.086 s (51.417 s total) | 657.422 s / 240 tokens | 0.510 s / 1 run |
| 37804 / r03 | 217.640, 231.763, 219.805, 218.432, 218.433 s (1,106.073 s total) | 18.480, 22.689, 18.966, 19.008, 19.327 s (98.470 s total) | 1,220.595 s / 403 tokens | 0.523 s / 1 run |
| 35419 / r03 | 190.234, 190.511, 189.677, 190.445, 191.637, 190.946, 190.994 s (1,334.444 s total) | 16.596, 16.596, 16.738, 17.037, 17.103, 17.187, 17.636 s (118.893 s total) | 1,469.041 s / 493 tokens | 4.156 s / 8 runs |

## Memory, frequency, and completion

| QID / run | MemAvailable before → after | CmaFree before → after | Swap | CPU frequency | Peak RSS |
|---|---:|---:|---:|---|---:|
| 38299 / r01 | 3,306,784 → 3,308,668 KiB | 473,212 → 493,584 KiB | 0 | 1,333,333 kHz × 4 | 1,854,160 KiB |
| 38299 / r02 | 3,309,304 → 3,309,940 KiB | 493,584 → 506,088 KiB | 0 | 1,333,333 kHz × 4 | 1,854,276 KiB |
| 37804 / r03 | 3,307,232 → 3,308,908 KiB | 506,088 → 557,440 KiB | 0 | 1,333,333 kHz × 4 | 1,862,748 KiB |
| 35419 / r03 | 3,304,540 → 3,310,696 KiB | 557,440 → 587,328 KiB | 0 | 1,333,333 kHz × 4 | 1,860,348 KiB |

The frozen QIDs completed with CLI exit 0, raw-copy hashes verified, and image-processing events present on the successful r02/r03 records. QID 37804 and 35419 r03 had no postflight gate reasons. QID 38299 r02 had only a `LOAD` advisory after completion; its CLI result, cleanup, and copy receipts all passed. The q38299 r01 CLI also exited 0 and produced a recoverable output, but the remote worker then failed while finalizing because of an unbound `TERMINATION_UNPROVEN` variable; that attempt has no normal completion/copy receipts and is retained only as recovery evidence. The one-line worker fix was applied before r02.

For r02, postflight reported only a load advisory after completion. A direct check found no active VLM, XRT build, apt/dpkg, or competing inference process and ample memory; PackageKit had no transactions. For r03 requests, the one-off host wrapper recorded load as an advisory at 4.0 while retaining memory, swap, service, forbidden-process, and stable busy-process gates. The fresh preflight and postflight snapshots are retained. This does not relax or alter the board runner/parser sources for this measurement.

Synthetic ALPHA wiring proof also passed before TextVQA: 249.515 s including model load, 1,844,552 KiB peak RSS, expected token match, CPU-only. The board experiment therefore demonstrates that a complete 4 GB-class KV260 request is feasible for the three tested shapes, while exposing a large latency gap to host CPU runs and one host/output disagreement. It does not establish a production service rate or PL speedup.

## Raw evidence

Answer-bearing raw CLI logs stay under `experiments/raw/` and are not duplicated in this summary. Their SHA-256 inventory, including request stdout/stderr, resource logs, pre/post snapshots, completion/result records where present, and the synthetic ALPHA proof, is in [`rm02_a_raw_evidence_hashes.json`](rm02_a_raw_evidence_hashes.json). The report's output strings are the only predictions copied into this tracked RM02-A summary; human reference answer strings are not included.
