# RM03 QID 37804 CPU thread sweep

## Result

The same frozen TextVQA request completed successfully on KV260 at 1, 2, and 4 Cortex-A53 threads. The 2-thread point reuses the RM02 run; it was not repeated. All three board outputs were `G`, exactly matching the existing host CPU output `G` (TextVQA soft accuracy 1.0). No answer/reference text is copied here.

| Threads | Run ID | CLI wall (s) | Prompt eval (s / tokens) | Vision encode batches (s; total) | Image decode events (s; total) | Peak RSS (KiB) | Output / host |
|---:|---|---:|---|---|---|---:|---|
| 1 | `kv260_cpu_p2_tvqa_q37804_rm03_t1_r02` | 2,290.97 | 2,278.023 / 403 | 413.191, 412.010, 412.128, 410.613, 413.716; **2,061.658** | 36.859, 36.886, 37.172, 37.454, 37.729; **186.100** | 1,864,564 | `G` / exact match |
| 2 | `kv260_cpu_p2_tvqa_q37804_r03` (RM02) | 1,233.11 | 1,220.595 / 403 | 217.640, 231.763, 219.805, 218.432, 218.433; **1,106.073** | 18.480, 22.689, 18.966, 19.008, 19.327; **98.470** | 1,862,748 | `G` / exact match |
| 4 | `kv260_cpu_p2_tvqa_q37804_rm03_t4_r01` | 659.28 | 646.935 / 403 | 117.712, 117.642, 119.911, 117.552, 117.531; **590.348** | 9.549, 9.607, 9.701, 9.781, 9.882; **48.520** | 1,864,408 | `G` / exact match |

The one-thread to four-thread wall-time speedup is **3.48×** (87% of ideal 4× scaling); the 1→2 and 2→4 speedups are 1.86× and 1.87×. The runtime-reported encoding, decode, and prompt-evaluation fields overlap and must not be summed as independent durations. The CLI's `resource.txt` wall time is used for the thread comparison; host orchestration time includes setup and evidence-copy overhead.

## Fixed inputs and conditions

- QID `37804`, image ID `58d543df7eab2bfc`, image SHA-256 `3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f`.
- Model SHA-256 `8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773`; mmproj SHA-256 `ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293`.
- llama.cpp runtime commit `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`; board CLI SHA-256 `84bfa2f5f91f13503b5a1349e05594cda30c01613227187cfb9e48e7b805f1d7`.
- Same CPU-only invocation and request parameters at each point (`--device none -ngl 0`, context 4096, 48-token cap, seed 42, temperature 0, top-p 1); `-t` and `-tb` were set to 1, 2, or 4 together.
- Each request exited 0, completed raw-copy verification, and verified remote process cleanup. CPU frequency was 1,333,333 kHz on all four cores before/after. Temperature is **UNKNOWN** (`thermal_c` was empty).
- MemAvailable (pre→post) and CmaFree (pre→post), KiB: t1 `3,312,064→3,298,948`, `587,328→579,672`; t2 `3,307,232→3,308,908`, `506,088→557,440`; t4 `3,305,788→3,306,260`, `579,672→588,804`. Swap remained 0. The completed t4 postflight reports only a `LOAD` advisory after inference; the request, output, cleanup, and copied evidence all completed successfully.
- Host reference output `G`, 8.17 s at 8 threads, as recorded in [RM02_A_CPU_BOARD_BASELINE.md](RM02_A_CPU_BOARD_BASELINE.md). It is an output comparison, not a matched-thread timing baseline.

## Interpretation and limits

This single-request sweep shows that the measured request benefits strongly from A53 parallelism: vision encoding and prompt evaluation both fall by about 3.5× from one to four threads, while peak RSS stays near 1.78 GiB. It supports a CPU-side parallelizable compute bottleneck for this request; it does **not** establish general VLM scaling, run-to-run variance, or the PL speedup opportunity. One input and one run per thread count were measured, so confirm with repeats before treating small differences as stable. The t4 load advisory was recorded, not used to invalidate a completed request.

## Evidence paths

Raw records remain in the worktree and are hash-verifiable per each run's `completion.json`:

- `experiments/raw/kv260_cpu_p2_tvqa_q37804_rm03_t1_r02/`
- `experiments/raw/kv260_cpu_p2_tvqa_q37804_r03/` (reused RM02 2-thread point)
- `experiments/raw/kv260_cpu_p2_tvqa_q37804_rm03_t4_r01/`
- One-off launch wrapper: `experiments/raw/rm03_q37804_thread_sweep.py`

The initial t1 wrapper invocation `kv260_cpu_p2_tvqa_q37804_rm03_t1/` is retained as a non-start attempt; it failed validation before inference when the q37804-only thread override was initially applied to the prior-case check. The successful t1 retry has a distinct `r02` ID. No board request was run after the completed t4 point.
