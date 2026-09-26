# RM11 Worker B — Post-RM10 workload profile

## QID37804 post-RM10 Pareto

Reference run: RM10 ten-bank image, frozen RM09 CPU library/runtime, 100 MHz PL, four A53 threads, five media groups, answer G; process wall **504.24 s**. Raw source is [q37804-time-v.txt](../rm10_boardprep/evidence/rm10-a-ra-q37804-20260926T084944Z/q37804-time-v.txt), [q37804-pl-trace.txt](../rm10_boardprep/evidence/rm10-a-ra-q37804-20260926T084944Z/q37804-pl-trace.txt), [q37804-stderr.log](../rm10_boardprep/evidence/rm10-a-ra-q37804-20260926T084944Z/q37804-stderr.log), and [RESULTS.md](../rm10_boardprep/evidence/rm10-a-ra-q37804-20260926T084944Z/RESULTS.md).

The 428.750 s mtmd batch encoding and 49.290 s image decoded spans are sequential, adjacent phases in the RM10 stderr; they do not overlap. The latter is image-embedding prefill (mtmd_helper_decode_image_chunk in the prior instrumented source), not JPEG/pixel decompression. The encoder span covers vision plus projector; its subfamilies are not independent wall spans. CLI prompt evaluation (489.524 s) contains image work and is an aggregate, so these values must not be added together.

| Component | Time | % of 504.24 s | Status / scope |
|---|---:|---:|---|
| Vision + projector batch encode (mtmd batch encoding) | 428.750 s | 85.03% | Direct RM10 wall timer; CPU path except numbered FFN-down PL. Includes the prior selected-node rows below. |
| Numbered FFN-down family | 83.082 s | 16.48% | Direct RM10 PL-call wall, nested in encode. 135 calls, all PL. Kernel 69.855 s (13.85% request), host packing 11.807 s (2.34%), sync/submit/unpack 1.383 s. |
| Attention Q/K/V/output projections | 136.958 s | 27.16% proxy | Prior QID37804 BOARD_MEASURED selected-node CPU timings reused from RM05; current RM10 remains CPU. Nested in encode. Attention body/softmax time is UNKNOWN. |
| Merger FFN-up + FFN-down | 108.745 s | 21.57% proxy | Prior RM05 selected-node CPU timings reused: 84.616 + 24.129 s. Current RM10 leaves them on CPU. Nested in encode. Do not infer compute time from the tiny fallback-dispatch wall_ms in the PL trace. |
| Numbered FFN-up | 86.440 s | 17.14% proxy | Prior RM05 selected-node CPU timing reused: 50.163 + 36.277 s. Current RM10 leaves it on CPU. Nested in encode. |
| Image-embedding prefill (image decoded) | 49.290 s | 9.78% | Direct RM10 wall timer, five sequential image-token batches, after encode. |
| Patch embedding | 1.516 s | 0.30% proxy | Prior RM05 selected-node CPU timing reused; nested in encode. |
| Text token decode | 0.293 s | 0.06% | Direct RM10 CLI perf counter; one generated token. |
| JPEG/pixel decode | UNKNOWN | — | No separate board timer. |
| Projector alone | UNKNOWN | — | Included in vision+projector encode timer; no isolated projector timing. |
| Text-only prompt prefill | UNKNOWN | — | CLI prompt-eval total is 489.524 s and overlaps image processing; subtracting phase timers yields no reliable text-only time. |
| Major faults / file input | Not a wall-time component | — | /usr/bin/time -v gives counts, not page-in bytes. See fault A/B below. |

RM05 prior timings are selected MUL_MAT callback intervals from one QID37804 board request, not fresh RM10 subfamily timings or mutually exclusive wall intervals. Their artifact is [RM05_RESULTS.md](../rm05/RM05_RESULTS.md), with per-family details in [q37804_vision_family_cpu_timing.csv](../rm05/results/q37804_vision_family_timing/q37804_vision_family_cpu_timing.csv). The approximate percentages in those rows only give scale against the RM10 request wall; they must not be summed. They exclude unselected attention/non-MUL_MAT operations, and no independent RM10 timings exist for them.

### Three largest remaining measured candidates after FFN-down

Ranked from the reused selected-node CPU timings: **attention projections (136.958 s)**, **merger FFN-up/down (108.745 s)**, and **numbered FFN-up (86.440 s)**. These are the next profile candidates; only the down family has direct RM10 PL-vs-CPU family timing. The image-embedding prefill is a distinct 49.290 s fourth measured span. The actual attention body, projector subcost, and text-only prefill stay UNKNOWN, so this ranking is among measured categories and may not represent unmeasured costs.

## Major-fault / I/O A/B

Completed QID37804 runs only; preserve run order because the RM10 trials were sequential and cache state was not balanced. “File system inputs” is the /usr/bin/time -v input count, **not bytes**. No actual page-in-byte counter was captured.

| Mode / run | Wall | Major faults | File-system inputs | Provenance caveat |
|---|---:|---:|---:|---|
| CPU-only baseline (RM08) | 668.35 s | 583 | 10,416 | Different runtime/build from RM09/RM10. |
| RM09 static control | 519.39 s | 4,068 | 76,840 | Same RM09 runtime as RM10; single control, run after the first RM10 attempt. |
| RM10, first completed Q37804 | 524.42 s | 21,695 | 845,952 | First in the same-run sequence; cold/warm cache differs. |
| RM10, repeat | 517.10 s | 15,617 | 563,712 | Second repeat. |
| RM10, repeat | 504.24 s | 5,838 | 165,016 | Final repeat used for the Pareto above. |

Within the three ordered RM10 repeats, faults, input counts, and wall all fall together; the one RM09 result has fewer faults than RM10 yet a longer wall than the final RM10 run. This is **warm-order association, not stable causal attribution**. Runtime version and run order also confound the CPU-only point. Do not start a memory-management line from these data. CMA gates passed in RM10; the bounded XRT BO pool was 1,671,168 bytes and the Q37804 pre-request CmaFree sample was 520,980 kB (in-run minimum was not continuously measured).

## Additional RM10 requests

Prepared board runner: [run_rm10_q38299_q35419.sh](boardprep/run_rm10_q38299_q35419.sh), source commit 83f6a33. It performs one guarded RM10 load and one restore for both exact frozen requests, with 4200 s rollback protection, PL/extent/answer checks, /usr/bin/time -v, and CMA boundary samples. Existing RM09 same-runtime baselines are in [RM09 static extent results](../rm09_static_extent/evidence/board/rm09-pl-q38299-q35419-20260925T122922Z/RESULTS.md) and [CPU controls](../rm09_static_extent/evidence/board/rm09-cpu-same-runtime-20260925T130058Z/RESULTS.md).

Both requests passed exact-answer, frozen-extent and per-layer PL checks in one loaded RM10 session. The approved image was loaded once, each request ran against the frozen RM09 runtime/model/mmproj and exact input hashes, and the runner restored starter-kit once at 09:34:15Z. Raw remote files are copied under [the RM10 evidence directory](evidence/rm10-two-qids-20260926T091903Z/); the board-produced digest manifest verifies locally. A concise run report is [RESULTS.md](evidence/rm10-two-qids-20260926T091903Z/RESULTS.md).

| Request | Media groups | RM10 process wall | RM09 static wall | Same-runtime CPU wall | RM10 vs RM09 | RM10 answer / PL coverage |
|---|---:|---:|---:|---:|---:|---|
| QID38299 | 3 | 285.53 s | 299.14 s | 368.51 s | 1.048×; 4.55% lower | `3`; 81/81 numbered calls PL; 6 merger fallbacks |
| QID35419 | 7 | 619.70 s | 652.32 s | 822.35 s | 1.053×; 5.00% lower | `SHERIFF'S`; 189/189 numbered calls PL; 14 merger fallbacks |

Same-runtime CPU reductions are 22.5% (QID38299) and 24.6% (QID35419). For QID38299, down-family dispatch wall was **45.911 s** vs **55.250 s** on RM09 (1.203×), kernel **38.728 s** vs **47.980 s**, and packing **6.397 s** vs **6.451 s**. For QID35419, dispatch wall was **104.585 s** vs **125.625 s** (1.201×), kernel **88.081 s** vs **109.115 s**, and packing **14.713 s** vs **14.718 s**. The stable ~1.20× family result and ~1.05× full-request result confirm the recurrence-decoupled gain across these requests, while showing it remains a smaller end-to-end gain. These family dispatch sums include the brief merger fallback dispatch intervals; kernel sums are PL-only.

The additional-request fault measurements reinforce the caution against a memory project: QID38299 faults were 7,144 on RM10 vs 10,526 RM09 vs 587 CPU; QID35419 was 63 vs 3,865 vs 1,368. Wall improved from CPU to RM09 to RM10 for both, while fault counts do not follow one consistent relation. Q37804's ordered repeated-RM10 measurements still show a warm-order association only. Neither set has page-in bytes; file-system input counts remain counts, not bytes. Conclusion remains **warm-order association, no stable causal attribution; no memory work**.

Request-gate `CmaFree` was 557,168 kB for QID38299 and 658,200 kB for QID35419; post-request samples were 658,092 and 645,428 kB. Runner boundary minimum was therefore 557,168 kB (not a continuous in-run minimum). Restore passed, returning `CmaFree` to 651,908 kB, `fclk0=99,999,999 Hz`, and `fpga_manager=operating`; run exit status was zero. The pinned bit.bin SHA-256 was `722387cc80b345f0b7b29bdffe61911707cf12c5c25e42867d339b4a0c6fb5d7` and the run recorded matching model, mmproj, CLI, and CPU-library hashes.
