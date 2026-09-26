# RM12 performance budget (before new hardware)

This is a decision screen, not a new VLM measurement. The request rows use the
same-runtime, four-A53 CPU and RM10 PL results for the same frozen input and
online request boundary. QID 37804's earlier CPU-only build is excluded from
the matched request targets. FFN-up CPU timing comes from RM05's earlier
instrumented board build, while RM11 PL is one real call per representative
layer. Thus the FFN-up family arithmetic is explicitly a **cross-run budgeting
estimate**, not a paired speedup or 135-call execution.

## Operator call-time gate

| Candidate / goal | Board CPU reference | Current PL total | Maximum profitable PL total | Further total reduction needed | Kernel limit if RM11's 19.454 s family boundary stays fixed |
|---|---:|---:|---:|---:|---:|
| FFN-up N=1120, one call | 1.431 s | 1.664 s | <1.431 s | >0.233 s | Depends on its measured per-call boundary |
| FFN-up N=280, one call | ~0.356 s | ~0.421 s | <0.356 s | >0.065 s | Depends on its measured per-call boundary |
| FFN-up, 135-call break-even estimate | 86.440 s | 100.324 s | <86.440 s | >13.884 s | <66.986 s, or >1.207x faster than current 80.870 s kernel |
| FFN-up, 1.5x family screen | 86.440 s | 100.324 s | <=57.627 s | >=42.697 s | <=38.173 s, or >=2.119x faster kernel |
| FFN-down, preserve strongest baseline | 250.124 s prior CPU trace | 83.082 s RM10 PL family | <=83.082 s for no regression | New design may spend no extra family wall | Keep same-runtime RM10 control |

For any new operator family, rank the opportunity by
`CPU_time - PL_total_time`, with `PL_total = kernel + packing + movement +
sync/submit + output handling`. Functional MAC coverage alone is not a
benefit. Even zero FFN-up boundary would leave 80.870 s kernel versus
86.440 s CPU, only `1.069x` headroom; eliminating packing/submit alone is
not a strong FFN-up accelerator.

## Whole-request targets relative to same-runtime CPU-only

The next table asks what **additional** reduction is needed after the already
measured RM10 down offload. A 5x or 10x column assumes that fraction of the
*remaining RM10 wall* is offloaded at exactly that operator-level speedup,
with no added boundary; it is an optimistic effective-compute ceiling. The
lower bound with infinitely fast hardware is the extra-save fraction.

| QID / media groups | CPU-only / RM10 wall | Target vs CPU | Target request wall | Extra time to save from RM10 | Min remaining-wall coverage at infinite / 5x / 10x effective operator speed |
|---|---:|---:|---:|---:|---:|
| 38299 / 3 | 368.51 / 285.53 s | 2x | 184.255 s | 101.275 s | 35.5% / 44.3% / 39.4% |
| 38299 / 3 | 368.51 / 285.53 s | 4x | 92.128 s | 193.403 s | 67.7% / 84.7% / 75.3% |
| 38299 / 3 | 368.51 / 285.53 s | 5x | 73.702 s | 211.828 s | 74.2% / 92.7% / 82.4% |
| 35419 / 7 | 822.35 / 619.70 s | 2x | 411.175 s | 208.525 s | 33.6% / 42.1% / 37.4% |
| 35419 / 7 | 822.35 / 619.70 s | 4x | 205.588 s | 414.113 s | 66.8% / 83.5% / 74.2% |
| 35419 / 7 | 822.35 / 619.70 s | 5x | 164.470 s | 455.230 s | 73.5% / 91.8% / 81.6% |

For a remaining-wall fraction `p` sped up by effective factor `s`, the
saved fraction is `p(1-1/s)`. The operator-level `s` must include the complete
call boundary. A 2x request target already requires eliminating roughly one
third of RM10's remaining wall even with an ideal zero-time engine; 4x/5x
requires much broader profitable coverage than FFN-up alone. These figures
are performance budgets, not projected outcomes for the proposed microkernel.

Source evidence: [RM11 milestone](../rm11/RM11_MILESTONE_RESULTS.md),
[RM11 FFN-up board report](../rm11_unified_ffn/RM11_RESULTS.md), and
[additional matched RM10 requests](../rm11_post_rm10_profile/RM11_POST_RM10_PROFILE.md).
