# RM09: strong static compute baseline

## Board result

The KV260 ran MiniCPM-V 4.6 Q4_K_M with the F16 mmproj and four Cortex-A53
threads. Process wall comes from `/usr/bin/time -v`. The two RM09 CPU controls
used the **same CLI and CPU-library binaries** as their PS+PL runs. The earlier
RM08 QID37804 pair is retained as an independent five-media-group result.

| QID | Media groups | CPU-only wall | PS+PL wall | Request speedup | Transformer FFN-down PL calls | Explicit merger CPU fallbacks | Answer |
|---:|---:|---:|---:|---:|---:|---:|---|
| 38299 | 3 | 368.51 s | 299.14 s | 1.232× | 81 | 6 | `3` |
| 37804 (RM08) | 5 | 668.35 s | 522.34 s | 1.280× | 135 | 10 | `G` |
| 35419 | 7 | 822.35 s | 652.32 s | 1.261× | 189 | 14 | `SHERIFF'S` |

The RM09 static extent image used the same K16, F16-weight × F32-activation →
F32 accumulation datapath as RM07; it widened the runtime shape contract.
QID38299 used N1024/1056/256/264; QID35419 used N1008/252. All numbered
FFN-down calls matched PL, while the out-of-scope merger calls fell back to
CPU. Three previously captured real tensors at N1120/280 passed against the
CPU reference; new extents have C-sim goldens and matching final VLM answers,
but **no elementwise real-tensor reference capture**. Each request was run
once, so the speedups are first-pass measurements rather than a variance
estimate.

| QID | FFN-down dispatch wall | PL kernel | Host packing | Kernel throughput |
|---:|---:|---:|---:|---:|
| 38299 | 55.250 s | 47.980 s | 6.451 s | 3.849 GMAC/s |
| 35419 | 125.625 s | 109.115 s | 14.718 s | 3.848 GMAC/s |

Throughput is derived from the exact traced K/M/N and accumulated kernel time;
it is not a separate hardware counter. The close rates across token extents
show no measured PE-throughput collapse within these FFN-down shapes. Submit
and sync each contribute well below 1 s per request. The bounded DMA pool was
1,671,168 bytes. `CmaFree` at the logged pre-load checkpoint was 492,512 kB;
the true in-request minimum was not sampled continuously. All requests exited
successfully, and the starter-kit image and 99,999,999 Hz FCLK0 were restored.

Primary evidence: [RM09 PL run](../rm09_static_extent/evidence/board/rm09-pl-q38299-q35419-20260925T122922Z/RESULTS.md), [matched CPU controls](../rm09_static_extent/evidence/board/rm09-cpu-same-runtime-20260925T130058Z/RESULTS.md), and [RM08 result](../rm08/RM08_RESULTS.md).

## Compute and numerical gates

- Board FCLK0 remained 99,999,999 Hz after a 150 MHz sysfs request, a
  187.5 MHz overlay assignment, and one exact 187,498,123 Hz sysfs request.
  The guarded overlay and exact-rate attempts restored starter-kit before
  benchmarking.
  There is **no measured higher-clock scaling result**; 187.512 MHz is an
  earlier routed constraint, not a board frequency.
- The extent version's one full-system Vivado implementation closed its
  100 MHz constraint: WNS +1.264 ns, router WHS +0.010 ns, 183 DSP,
  66,769 LUT, 67,564 FF, 18.5 BRAM tiles, 40 URAM, and 12,563/14,640 CLB
  sites. The HLS compute loop retains II=5 and 52 mapped FP32 multipliers.
  The slack-implied 114.47 MHz is a one-run estimate, not board Fmax.
- The 100 MHz mapped roof is about 5.2 GMAC/s from 52 multipliers; the
  measured kernel rate is about 74% of that roof. FP32 accumulator recurrence
  sets II=5; FP32 adders, mux/control, and routing consume fabric while DSP
  occupancy remains low. Doubling arithmetic cannot be justified by the DSP
  percentage alone. See the [compute roof](RM09_COMPUTE_ROOF.md).
- P1 (F16 activation, F32 accumulation) failed the frozen layer-26 local
  tensor gate: max abs 0.052887, RMSE 0.001264 versus limits 0.001/0.0001.
  P2 (BF16 W/X) and P3 (F16 product/interleaved F16 accumulator) also failed
  this local gate. Their model-level quality remains **UNKNOWN** and no
  reduced-precision candidate was synthesized. See the [precision result](../rm09_precision/RM09_RESULTS.md).
- FFN-up achieved 3.875 CPU GMAC/s versus FFN-down 1.332 CPU GMAC/s in the
  targeted QID37804 profile, but there is no board PL FFN-up measurement.
  The [orientation comparison](RM09_COMPUTE_ROOF.md) does not establish an
  orientation-adaptive architecture advantage.

## Research decision

**`NO_NOVELTY_YET`.** This milestone establishes a stronger static FPGA
baseline and confirms three complete VLM requests improve on CPU-only at the
measured board clock. The newly supported extents were a low-cost correction
to an existing shape guard, not a new datapath. The precision candidates did
not pass the current local numeric gate, and neither higher-clock operation
nor a structural orientation/fusion advantage was measured. Do not present
the static engine or its coverage extension as a paper method.
