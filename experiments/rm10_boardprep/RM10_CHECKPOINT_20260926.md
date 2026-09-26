# RM10 checkpoint — paused 2026-09-26

The user requested a checkpoint and pause after the already-running paired
control completed. Both board experiments finished, and both restored
`k26-starter-kits` at 100 MHz. Do not start another board experiment until
the user resumes the work.

## What is established

- The original five-bank A revision is **invalid and was never loaded**. Its
  HLS pragma omitted `inter true`; the generated schedule read an accumulator
  at stage 26 and wrote it at stage 35, but reused its bank five iterations
  later. The original bitstream and route reports are retained as invalid
  evidence.
- The corrected ten-bank A revision explicitly declares `inter true
  distance=10`. Its schedule reads at stage 25 and writes at stage 34; same-bank
  reuse is ten iterations apart. C-sim and full-top C/RTL co-sim passed 4,096
  checked outputs across the 1,076-group reduction. Real tensors from
  `ffn_down-0`, `-13`, and `-26` passed the frozen max-absolute-error,
  RMSE, and cosine gates. The arithmetic remains F16 weights × F32
  activations → F32 accumulation/output.
- HLS mapped 64 FP32 multipliers, K-loop II=1, and projected 115,209,745
  cycles for N=1120 and 28,957,507 for N=280. Full-system Vivado route
  closed at 100 MHz: WNS +3.564 ns, WHS +0.010 ns; 323 DSP, 41,431 LUT,
  55,317 FF, 18.5 BRAM tiles, 40 URAM, and 8,347/14,640 CLB sites.
  Corrected `.bit.bin` SHA-256:
  `722387cc80b345f0b7b29bdffe61911707cf12c5c25e42867d339b4a0c6fb5d7`.
- Standalone real-tensor board calls passed: N=1120 kernel 1.161 s,
  total 1.380 s, 4.781 kernel GMAC/s; N=280 kernel 0.292 s,
  total 0.348 s, 4.756 kernel GMAC/s. Both used the bounded 1,671,168-byte
  DMA pool and a measured 99.999 MHz PL clock.

## Paired QID 37804 comparison

Both requests used the same RM09 CLI/CPU library, model, mmproj, image,
prompt, 4 A53 threads, and 100 MHz PL clock. Both produced `G`, used
135 FFN-down PL calls (35 N=1120 and 100 N=280), had 10 expected merger
fallbacks, and completed starter-kit restore.

| Measure | RM09 static control | RM10 ten-bank A | RM10 minus static |
|---|---:|---:|---:|
| Full request wall | 519.39 s | 524.42 s | +5.03 s |
| FFN-down family wall | 99.630538 s | 82.946846 s | -16.683692 s |
| PL kernel wait | 86.545451 s | 69.855115 s | -16.690336 s |
| Packing | 11.670977 s | 11.629916 s | -0.041061 s |
| Major page faults | 4,068 | 21,695 | +17,627 |
| Filesystem input blocks | 76,840 | 845,952 | +769,112 |

The RM10 request ran **first**; the static control ran second. The page-fault
and I/O difference is consistent with a cold/warm cache confound. Paired
static-family substitution predicts 502.706 s for RM10 if all other request
time were fixed; actual wall was 524.42 s, leaving a +21.714 s non-family
residual. This residual must not be labeled PS–PL overhead: packing,
sync, and submit did not rise, and the non-offloaded work and file-cache
conditions differed. The one paired sequence proves a real kernel/family
speedup but **does not settle end-to-end latency**.

## Decision and resume point

`GO_RECURRENCE_ARCHITECTURE` is not yet justified because a whole-request
improvement over the strong static baseline was not demonstrated.
`STATIC_BASELINE_NEAR_RESOURCE_WALL` is also unsupported: corrected A routes
at 57.0% CLB occupancy versus 85.8% for the static baseline.
Do not force `STOP_THIS_ARCHITECTURE` from the cache-confounded whole-request
pair. The RM10 architecture decision remains **INCONCLUSIVE at pause**;
generic accumulator interleaving is established prior art and is not a
novelty claim.

If the user resumes, first inspect the paired raw logs and control for cache
state (for example, a balanced warm-order comparison) before any new
hardware design. No further precision, clock, shape, or dynamic-scheduling
work is queued.

Candidate evidence: `evidence/rm10-a-ra-q37804-20260926T022237Z/`.
Static-control evidence: `evidence/rm10-rm09-static-q37804-20260926T024229Z/`.
Corrected route report: `../rm10_route/RM10_CORRECTED_ROUTE_RESULTS.md`.
The project state is on branch `codex/rm10-integration`.
