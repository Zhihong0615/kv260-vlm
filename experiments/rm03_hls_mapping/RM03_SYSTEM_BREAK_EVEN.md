# RM03 CPU scaling and PL break-even

> **RM04 correction / superseding measurement:** The RM03 text below used the transposed HLS shape (`K=4304, M=1152`) while labeling it `ffn_up-0`; real KV260 tensor capture establishes `ffn_up-0` as `K=1152, M=4304, N=1120`. Also, the 13.61 s family CPU time below is a MAC-proportional proxy, not a direct timing of the five target nodes. RM04 measured those exact five CPU nodes at 7.158 s and re-synthesized corrected-shape Dynamic8 at 417,605,286 cycles/op. The full-system routed clock is 187.512 MHz, giving an optimistic schedule-derived 11.135 s for five PL calls before DDR stalls or boundary costs. Thus the current Dynamic8 mapping is slower than directly measured CPU even before PS–PL overhead; see [`RM04_RESULTS.md`](../rm04_system/RM04_RESULTS.md). The remaining historical analysis below is preserved as the original RM03 checkpoint, not the current go/no-go basis.

## Measured KV260 CPU baseline

QID 37804 was run CPU-only with the same MiniCPM-V 4.6 model, mmproj, image, prompt, and runtime at 1, 2, and 4 Cortex-A53 threads. The 2-thread run is the RM02 measurement; it was not repeated. All three returned `G`, matching the host output. The image SHA-256 is `3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f`.

| Threads | Request wall | Runtime-reported image encoding (five batches) | Prompt eval (403 tokens) | Peak RSS |
|---:|---:|---:|---:|---:|
| 1 | 2,290.97 s | 2,061.658 s | 2,278.023 s | 1,864,564 KiB |
| 2 | 1,233.11 s | 1,106.073 s | 1,220.595 s | 1,862,748 KiB |
| 4 | 659.28 s | 590.348 s | 646.935 s | 1,864,408 KiB |

One-to-four-thread request speedup is 3.48×; 1→2 and 2→4 are 1.86× and 1.87×. The four-thread run used 387% CPU, so all four cores were active. CPU frequency was 1.333 GHz ×4 in all runs; t4 MemAvailable was 3,305,788→3,306,260 KiB, CMA 579,672→588,804 KiB, swap 0. Temperature and TTFT are unknown. The completed t4 postflight carried only a LOAD advisory. Encoding, prompt-evaluation, and decode timers printed by the runtime overlap and cannot be added as independent request phases. Full input, hashes, and per-run evidence are in the CPU worker commit `432519e15dd78982d3d9bcc15c0b0b6b62d62a1c`, file `experiments/RM03_Q37804_THREAD_SWEEP.md`.

## Kernel points used in the model

The operation `ffn_up-0` is `4304/1120/1152`, or 5.5532 GMAC, and occurs five times in this request. The RM03 HLS and OOC evidence is in [`RESULTS.md`](RESULTS.md).

| Mapping | HLS cycles per operation | Time at 200 MHz | Mapped FP32 multipliers | Compute II | DSP | OOC routed estimate |
|---|---:|---:|---:|---:|---:|---:|
| Same-association dynamic8 | 397,802,882 | 1.989 s | 16 | 1 | 82 | ≈225.1 MHz, WNS +0.557 ns |
| Static K16 | 164,188,802 | 0.821 s | 52 | 5 | 182 | ≈209.4 MHz, WNS +0.225 ns |

Dynamic8 retains the frozen eight-way FP32 accumulation association and is the lower-risk integration reference. K16 is the HLS speed/resource upper point, but changes FP32 summation association; its C-sim golden follows the new order, so it still needs comparison against frozen-order results on real model tensors before use. Both OOC routes are core-only: external AXI timing and PS/DDR integration were not modeled; no bitstream was loaded.

## Break-even for only the five observed operations

The workload profile estimates 1.204542 TMAC for the request's vision graph. The five `ffn_up-0` calls are 27.765965 GMAC, or 2.305% of that MAC proxy. Approximate CPU time for this family by distributing the measured four-thread encoding time in proportion to MACs:

`T_CPU,family ≈ 590.348 s × 2.305% = 13.61 s`

This is a proxy, not an isolated CPU timing of these five calls. HLS compute-only time is `5 × cycles / 200 MHz`: 9.945 s for dynamic8 and 4.105 s for K16. Therefore, under the proxy, the total boundary cost must satisfy:

- Dynamic8: `T_DMA + T_layout + T_submit/sync < 3.66 s` per request.
- K16: `T_DMA + T_layout + T_submit/sync < 9.50 s` per request.

The HLS traffic model estimates 1.7405 GB per operation, or 8.7027 GB for five calls. Traffic-only lower bounds are 1.81 s at an assumed 4.8 GB/s and 8.70 s at an assumed 1.0 GB/s. Thus at 1 GB/s the dynamic8 case already misses its modeled break-even before launch/synchronization; at 4.8 GB/s it leaves about 1.85 s for those costs. These bandwidths are assumptions, not KV260 measurements, and the traffic model does not measure actual PS–PL DMA. This narrowly targeted offload could save at most about 1.4% of the 659 s request even if the proxy holds and boundary cost is zero.

## Vision-wide upper-bound scenarios

For scale only, the single HLS mapping's schedule-derived rates are 2.792 GMAC/s (dynamic8) and 6.764 GMAC/s (K16). Applying each rate to the entire 1.204542-TMAC vision MAC proxy gives 431.4 s and 178.1 s, respectively. If the encoding timer is treated as a serial subset of the 659.28-s request, the remainder is approximately 68.93 s, yielding illustrative request times of 500.4 s (dynamic8) and 247.0 s (K16), before transfer and control overhead. These are optimistic extrapolations: the kernel supports one shape, most vision operations are not covered, schedule cycles omit real DDR stalls, and the runtime phase timers overlap. They are not predicted board results.

## Decision

**GO_MINIMAL_PL_INTEGRATION**, beginning with the PS/PL interface, traffic, layout, launch, and synchronization path for the same-association dynamic8 reference; keep K16 as an upper point pending model-tensor numerical comparison. Dynamic8 has 16 inferred multipliers, II=1, a 4.47× HLS schedule reduction over RM02, and a positive OOC route. It does not justify broad VLM offload or a novelty claim: this shape family is only 2.305% of the vision MAC proxy, and the dynamic8 break-even budget is only 3.66 s/request under the rough CPU proxy.

No research bitstream was loaded. Any first load still needs the project's separate board safety authorization.
