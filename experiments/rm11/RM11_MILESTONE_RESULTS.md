# RM11 milestone: unified Vision FFN and bottleneck migration

Decision: **`NO_NEW_METHOD`**. Freeze the RM10 recurrence-decoupled FFN-down
engine as the strongest demonstrated MiniCPM-V/KV260 system. The RM11 shared
engine is numerically correct and routed, but its measured FFN-up calls are
slower than A53. No full-request FFN-up integration was run after that negative
standalone gate. This does not invalidate the measured RM10 FFN-down gain.

## Board evidence

QID 37804 uses four Cortex-A53 threads and five media groups. RM05 measured
the CPU family times with selected-node callbacks. The RM11 numbers below are
three **real captured tensor single calls** on KV260 at measured 99.999 MHz,
not a 135-call replay. The 135-call figure is a representative-call projection
using the observed 35 early and 100 later FFN-up calls.

| FFN-up layer | K/M/N | CPU per call, RM05 | RM11 PL kernel | RM11 total PL call | Pack / unpack | Max abs / RMSE |
|---|---|---:|---:|---:|---:|---:|
| 0 | 1152/4304/1120 | 1.431124 s | 1.344704 s | 1.664147 s | 206.249 / 101.193 ms | 3.815e-6 / 1.749e-7 |
| 13 | 1152/4304/280 | 0.356086 s | 0.337764 s | 0.420664 s | 54.135 / 25.618 ms | 1.907e-6 / 2.032e-7 |
| 26 | 1152/4304/280 | 0.355858 s | 0.338348 s | 0.420911 s | 53.541 / 25.767 ms | 6.104e-5 / 1.891e-6 |

All three outputs passed the frozen max-abs `<=1e-3`, RMSE `<=1e-4`, cosine
`>=0.999` gate against A53-captured CPU Y. The shared bitstream supports both
up and down orientations, with F16 weights, F32 activations and F32 output.
Vivado implementation passed at 100 MHz: WNS `+3.158 ns`, WHS `+0.010 ns`,
329 DSP, 43,940 LUT, 55,731 FF, 18.5 BRAM tiles, 40 URAM, and 8,853/14,640
CLB sites. The new bitstream was loaded for the three calls and the board
restored `k26-starter-kits`; runner exit status was zero. Its exact `.bit.bin`
SHA-256 was `53894991503d8d2882dfddb1222f564994222902e03592a19ad23c7d027d7bc6`.

The measured FFN-up kernel throughput was 4.10–4.13 GMAC/s, but the total-call
throughput was 3.30–3.34 GMAC/s. APM payload rate was about 0.28 GB/s, far
below DDR saturation. For up-0, packing took 206.249 ms and unpacking
101.193 ms; XRT sync plus control submit totaled 9.818 ms. Thus the negative
system result cannot be assigned to submit/sync or saturated DDR alone.

The weighted estimate is
`35*1.664147 + 50*0.420664 + 50*0.420911 = 100.323895 s` for PL total calls,
of which `80.870240 s` is measured-call kernel time extrapolated to the family.
The remaining projection is 12.603 s packing, 6.111 s unpacking, 0.253 s
sync-to, 0.193 s sync-from, 0.161 s submit, and 0.134 s residual. It treats
the measured middle and late N=280 calls as equally weighted representatives
of the 100 later calls; it is not an observed full-family replay.
The BOARD_MEASURED CPU FFN-up family took `86.440139 s`. The fixed shared
mapping is therefore projected to be **16.1% slower** for FFN-up at the call
boundary (`CPU/PL = 0.8616x`), despite passing the numeric gate. A full RM11
VLM request would be a speculative test of a losing component; it was not run.

## Coverage, controls, and complete requests

The 27 transformer FFN-up and 27 transformer FFN-down layers make 135 calls
per family on QID 37804. Each family has 333.192 GMAC, or 27.66% of the
1,204.54 GMAC vision graph arithmetic proxy from RM05. The shared bitstream
can execute both families (55.32% of that **MAC denominator**), but only
FFN-down has a demonstrated beneficial full-call offload (27.66% of that
denominator). The merger is outside this shape contract. CPU time coverage is
different: RM05 CPU selected-node FFN-up/down totals are 86.440/250.124 s,
respectively; these are not a current RM10 exclusive wall decomposition.

| Orientation | CPU family rate | PL kernel rate | PL total-call rate | Interpretation |
|---|---:|---:|---:|---|
| Down, K/M=4304/1152 | 1.332 GMAC/s | 4.77 GMAC/s | 4.010 GMAC/s | Measured RM10 family; profitable |
| Up, K/M=1152/4304 | 3.855 GMAC/s | 4.120 GMAC/s | 3.321 GMAC/s | Three-call representative projection; loses to CPU |

The static array's 64 FP32 multipliers at 100 MHz imply a 6.4 GMAC/s raw
operator roof. The observed kernel rates are about 74.5% of that roof for
down and 64.4% for up; this is an effective rate, not an isolated PE-active
counter. The equal-MAC orientations have very different A53 baselines, and
up's larger output adds movement. These observations motivate a future
falsification test, not a proven need for a new dataflow.

| QID / media groups | Same-runtime CPU-only | RM09 static | RM10 FFN-down | Answer / coverage |
|---|---:|---:|---:|---|
| 38299 / 3 | 368.51 s | 299.14 s | **285.53 s** | `3`; 81/81 numbered PL, 6 merger CPU fallbacks |
| 37804 / 5 | 668.35 s historical CPU baseline | 519.39 s | **504.24 s** | `G`; 135/135 numbered PL, 10 merger CPU fallbacks |
| 35419 / 7 | 822.35 s | 652.32 s | **619.70 s** | `SHERIFF'S`; 189/189 numbered PL, 14 merger CPU fallbacks |

The QID 37804 CPU-only result is an earlier runtime/build and is shown for
context; the RM09/RM10 pair uses the same runtime. RM10 FFN-down family time
for QID 37804 was `83.082 s` versus `99.631 s` on RM09 and `250.124 s` on
the prior CPU selected-node trace. A crude RM11-up substitution into the RM10
request gives `504.24 + (100.324 - 86.440) = 518.124 s`; this is a **model,
not a measured RM11 request**. The combined transformer FFN CPU proxy is
336.564 s; RM10 down PL plus CPU up is 169.522 s, whereas shared PL for both
would project to 183.406 s.

## Post-RM10 bottlenecks

QID 37804's direct RM10 wall was 504.24 s. The direct vision-plus-projector
batch encode span was 428.750 s (85.03%); image-embedding prefill was a
separate sequential 49.290 s (9.78%). Numbered down PL calls consumed
83.082 s within encoding (69.855 s kernel and 11.807 s packing). The largest
remaining *selected-node CPU timing proxies* are attention projections
136.958 s, merger FFN-up/down 108.745 s, and numbered FFN-up 86.440 s.
These prior RM05 intervals are not freshly isolated RM10 spans and cannot be
summed as exclusive wall time. Attention body, projector alone, JPEG decode,
and text-only prefill remain UNKNOWN.

The CPU/RM09/RM10 major-fault A/B does not establish a causal wall bottleneck:
faults and wall co-vary with run order in repeated RM10 requests, but the
same-runtime RM09 control has fewer faults and a longer wall than the final
RM10 run. Page-in bytes were not measured. No memory-behavior architecture
work is justified from these counts.

## Research decision

The board measurement establishes an opposed-orientation **failure zone**:
CPU computes FFN-up much faster than FFN-down for equal MAC counts, while the
fixed PL engine has similar arithmetic rates for both but loses on FFN-up
after packing, movement and output costs. It does **not** establish that a
different dataflow, or a shared multimode design, beats a strong fixed and two
separately tuned static baselines at comparable resources. The narrow primary
literature audit finds interleaved FP accumulation, split-K/reduction, shared
FFN engines, and selectable GEMM dataflow already known. Consequently RM11
does not clear `GO_ORIENTATION_ADAPTIVE_ARCHITECTURE`,
`UNIFIED_FFN_SYSTEM_PAPER`, or `GO_MEMORY_BEHAVIOR`. It selects
**`NO_NEW_METHOD`** and preserves the RM10 complete VLM result as a system
implementation result. Future architecture work requires a new measured
mechanism and strong controls; it is not an automatic RM12 HLS sweep.

Raw evidence: [RM11 unified hardware and board report](../rm11_unified_ffn/RM11_RESULTS.md),
[RM11 post-RM10 profile](../rm11_post_rm10_profile/RM11_POST_RM10_PROFILE.md),
and [narrow prior-art audit](../../literature/rm11_c_narrow_prior_art.md).
