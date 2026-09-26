# RM10 corrected A board run

Run directory on `kria`: `/home/ubuntu/kv260-vlm-p2-cpu/runs/rm10-a-ra-q37804-20260926T022237Z`.

## Result

The three real-tensor standalone checks and integrated QID 37804 all passed. The request returned `G`, exited 0, and the RM09 starter app was restored. `/usr/bin/time -v` reports **524.42 s** (`8:44.42`) wall time. The runtime's performance summary reports 517.421 s model load time and 517.737 s total model time.

| Standalone tensor | N | Calls | HLS cycles | Kernel GMAC/s | Total-call GMAC/s | Wall | max abs / RMSE / cosine |
|---|---:|---:|---:|---:|---:|---:|---|
| `ffn_down-0` | 1120 | 35 stage / 315 compute | 116,160,207 | 4.781 | 4.024 | 1,379.958 ms | `9.53674316e-06 / 1.75370962e-07 / 0.999999999999850` |
| `ffn_down-13` | 280 | 9 / 81 | 29,196,263 | 4.756 | 3.984 | 348.430 ms | `2.1904707e-06 / 1.07185809e-07 / 0.999999999999801` |
| `ffn_down-26` | 280 | 9 / 81 | 29,195,683 | 4.756 | 3.985 | 348.404 ms | `0.000305175781 / 5.29015367e-06 / 0.999999999999963` |

All three pass the frozen gate: max absolute error ≤ `1e-3`, RMSE ≤ `1e-4`, cosine ≥ `0.999`.

The integrated trace passed its frozen checks: 145 total operations, comprising 135 PL calls (35 at N=1120 and 100 at N=280) and 10 expected CPU fallbacks (five ViT merger and five MM-down). All 27 numbered layers had five PL calls and zero numbered-layer CPU fallback.

| Integrated FFN-down measure | RM10 result |
|---|---:|
| Family call wall | 82.946846 s |
| Kernel time | 69.855115 s |
| Host packing / output unpack | 11.629916 / 1.169185 s |
| XRT sync to / from | 0.093951 / 0.080059 s |
| AXI submit | 0.041247 s |
| MACs / kernel rate / total-call rate | 333.1915776 GMAC / 4.76975 / 4.01693 GMAC/s |
| Input + output payload | 22.2292992 + 0.3096576 GB |

Five multimodal batch-encoding intervals sum to **429.287 s**; five image-decode intervals sum to **50.055 s**. No runtime or XRT buffer-allocation failures appear in the captured logs.

## Comparison and Amdahl estimate

The frozen QID 37804 PS+PL result carried in RM09 is the earlier RM08 run: 522.34 s, 135 PL calls, and answer `G`. Its CLI/library hashes (`73e4c882…` / `7351973a…`) differ from this run's RM09 CLI/library (`6a45ea36…` / `b44c7714…`), so that historical comparison is cross-build. Against the earlier 668.35 s CPU-only request, this is 1.274× / 21.535% lower wall time, also cross-build. A paired same-runtime RM09 static control later measured 519.39 s; see the sibling [paired-control results](../rm10-rm09-static-q37804-20260926T024229Z/RESULTS.md). Candidate ran cold and the paired control ran warm, so paired end-to-end evidence is `END_TO_END_INCONCLUSIVE`.

The RM10 integrated family wall is 16.719701 s (16.776%) below the historical RM08 family wall of 99.666547 s; kernel time is 16.691078 s (19.286%) below its 86.546193 s. The historical multimodal encoding total was 451.963 s, versus 429.287 s here.

Using the frozen RM08 CPU-only request/family values and RM10's measured family wall gives an Amdahl estimate of:

```text
668.35 s CPU-only − 250.124 s CPU FFN-down + 82.946846 s RM10 PL family
= 501.172846 s predicted
524.42 s measured − 501.172846 s predicted = +23.247154 s residual
```

The cross-build residual is not a same-binary architectural comparison. The observed family acceleration did not translate into lower full-request wall time versus the historical 522.34 s run.

## CMA, clocks, and restore

The bounded XRT pool was 1,671,168 bytes. Pre-request `CmaFree` was 214,100 KiB, above the 9,824 KiB admission floor. Read-only samples during inference observed as low as 3,444 KiB (the parent separately sampled 3,492 KiB); this is not continuous instrumentation. The existing BO pool was already allocated and no allocation errors occurred. The driver's post-request and post-restore snapshots show 515,008 and 491,140 KiB free, respectively.

FCLK0 read back 99,999,999 Hz and the FPGA manager remained `operating`. The 4,200-second rollback timer was active before app change. Explicit restoration completed at 02:31:31Z with `starter_kit_restore=PASS`; `run_exit_status=0`, and the timer was inactive at the end.

## Frozen identities and evidence

- Corrected route source commit: `3602eafa7de5cee187b79f8e28c186a19f6f6133`; source SHA `31a7b26f9bf28c0ad57892184ed30b42126162111fe4c4bda82aa7847754319a`.
- IP export ZIP SHA `b54c4ac0a15dc4501c3d1d470eeb2664fe9e2e60cf0d9ba7a0cfd9fdcca82e6b`; routed bitstream SHA `18ba853551f85ce1814332eacd370264696a93423fbf5a408e028b307c18ac23`; loaded `.bit.bin` SHA `722387cc80b345f0b7b29bdffe61911707cf12c5c25e42867d339b4a0c6fb5d7`.
- Runtime: RM09 CLI SHA `6a45ea3647b1db19d06408441729681d19966af569040e4577b1410b803d7254`; CPU library SHA `b44c771488d7fa63e73d1ddf0f15427f1943000fc969d4fe4cd42102e1c777b7`.

Raw board files were retrieved read-only. `REMOTE_SHA256SUMS.txt` contains checksums produced on the board and verified against the copies. `SHA256SUMS` covers the complete local evidence handoff.
