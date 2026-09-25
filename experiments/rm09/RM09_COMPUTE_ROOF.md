# RM09 compute and resource roof

Scope: RM07's bounded K16 `ffn_down` reports and the successful RM08 board run, with RM05's QID 37804 CPU profiles and corrected `ffn_up` route result. No HLS sweep or board operation was performed for this analysis. GMAC/s below counts one multiply-accumulate as one MAC.

## K16 roof and current schedule

The source unrolls `PE_M × PE_N × K_LANES = 4 × 4 × 16 = 256` FP32 multiply-accumulates per K group. An ideal II=1 implementation would peak at 48.003 GMAC/s at the RM07 routed clock (187.512 MHz), or 25.600 GMAC/s at the board's measured 99.999 MHz. That is a source-level ceiling, not the current implementation.

The reports show 52 mapped FP32 multiplier operators in the reduction pipeline, each costing 3 DSP, and an achieved K-loop II of 5 (269 iterations). The dependence report attributes II=5 to the distance-one update of each FP32 partial accumulator. Thus the current loop schedule is 256/5 = 51.2 MAC/cycle: 9.601 GMAC/s at 187.512 MHz or 5.120 GMAC/s at 99.999 MHz, before weight loads, staging, result reduction, and command overhead. The 52 multiplier instances provide a close mapped roof of 9.751 / 5.200 GMAC/s at those clocks.

RM08 measured 3.857 GMAC/s kernel rate for N=1120 and 3.840 for N=280. Those are 74.2% and 73.9% of the 52-multiplier roof at 99.999 MHz, and about 75.3% / 75.0% of the II-limited source roof. Board HLS-wait cycles are also within 0.7% of RM07's full-operation no-stall schedule at both shapes. The measured PL clock was 99.999 MHz, 53.3% of the 187.512 MHz full-system routed clock; the board run must be compared at its actual clock, not the route clock.

| Evidence level | Shape | Cycles or clock | GMAC/s | Meaning |
|---|---|---:|---:|---|
| Ideal source roof | K16, any full PE group | 256 MAC/cycle × 187.512 MHz | 48.003 | Assumes II=1 and all source operations in parallel |
| Current source schedule | K16, any full PE group | II=5 × 187.512 MHz | 9.601 | Excludes non-compute work |
| RM07 HLS full-op schedule | Down 4304/1152/1120 | 142,990,645 cycles at 187.512 MHz | 7.282 projected | No-stall schedule; includes operation schedule, not a board measurement |
| RM07 HLS full-op schedule | Down 4304/1152/280 | 35,902,735 cycles at 187.512 MHz | 7.251 projected | No-stall schedule; includes operation schedule, not a board measurement |
| RM08 board kernel | Down 4304/1152/1120 | 99.999 MHz; 1.440 s/operator | 3.857 measured | HLS wait across 35 activation and 315 compute commands |
| RM08 board kernel | Down 4304/1152/280 | 99.999 MHz; 0.362 s/operator | 3.840 measured | HLS wait across 9 activation and 81 compute commands |

The board's 1.440 s and 0.362 s kernel waits correspond to 143.98M and 36.15M cycles, respectively, against the RM07 scheduled 142.99M and 35.90M cycles. Schedule-cycle ratios are 99.31% for both shapes. This is schedule efficiency, separate from utilization against the 52-multiplier roof: RM07's complete operation schedule includes non-MAC work and therefore has a lower rate than the raw compute-loop ceiling.

## Operator and memory costs

| Component | Report evidence | Resource attribution |
|---|---|---|
| FP32 multiply | K-loop HLS report names 52 `fmul_32ns_32ns_32_5_max_dsp` instances | 3 DSP, 151 FF, 145 LUT each: 156 DSP, 7,852 FF, 7,540 LUT |
| FP32 partial accumulation | Same K-loop report names 52 `fadd_32ns_32ns_32_6_no_dsp` instances | 0 DSP, 278 FF, 411 LUT each: 14,456 FF, 21,372 LUT; this is the distance-one recurrence |
| Final FP32 reduction | Compute-module report names 12 `fadd_32ns_32ns_32_8_full_dsp` instances | 2 DSP each: 24 DSP, 3,552 FF, 2,868 LUT |
| Indexing / activation-stage arithmetic | Weight-load loop has one named `mac_muladd` on address arithmetic; HLS assigns 3 DSP total to activation staging | The compute module's 181 DSP = 156 K-loop + 24 final-reduction + 1 weight-load DSP; the separate stage module is 3 DSP |
| F16-to-F32 weight conversion | Source `half_to_float` builds IEEE-754 bits with shifts, masks, exponent cases, and subnormal normalization; it is inlined | No separate conversion IP or conversion-only resource subtotal is reported. Its bit logic is included in the loop's aggregate expression / select / mux resources; do not assign those totals exclusively to conversion. |
| Mux and expression/control | K-loop HLS summary reports 11,099 LUT under Multiplexer, 20,492 under Expression, 28,097 FF under Register, plus 64 named 14-LUT `sparsemux` instances | These categories mix conversion branches, lane/index selection, loop control, and scheduling logic; the report does not split them by source operation. |
| On-chip caches | Top HLS memory detail: four activation-cache banks, 8 URAM each; compute-module memory detail: four weight-cache banks, 2 URAM each | 32 + 8 = 40 URAM. Compute-module output tile storage uses 16 BRAM18K; top includes 54 BRAM18K estimated including interfaces. |

This explains the low DSP percentage alongside high CLB use. FP32 multiply uses DSPs, but the 52 no-DSP FP32 adders alone account for 21.4k LUTs; the compute K-loop reports another 31.6k LUTs across expression and mux categories. The multiplier blocks themselves also use LUTs and registers. The routed system uses only 184/1,248 DSP (14.74%) but 66,603/117,120 CLB LUTs (56.87%), 67,541/234,240 registers (28.83%), and 12,936/14,640 CLB sites (88.36%). DSP capacity cannot substitute for the fabric logic and placement sites those operators need.

Full-system RM07 post-route resources are 184 DSP, 66,603 LUT, 67,541 FF, 18.5 BRAM tiles (10 RAMB36 + 17 RAMB18 primitives), and 40/64 URAM. The corresponding HLS estimate is 184 DSP, 73,995 LUT, 60,445 FF, 54 BRAM18K, and 40 URAM. HLS BRAM18K counts and Vivado BRAM-tile counts are different report units.

## Timing, routing, and doubling parallelism

RM07 closed the 5.333 ns `clk_pl_0` constraint at 187.512 MHz with setup WNS +0.425 ns, TNS 0, and no failing endpoints. The worst setup path starts at an activation-cache URAM output and ends at the reduction pipeline's `xbits` register: 4.572 ns data delay, split 2.834 ns logic (62.0%) and 1.738 ns routed data path (38.0%). The report shows URAM clock-to-output of 2.682 ns and a further 1.671 ns on its data net before the LUT. This is the critical timing path; it is not the cause of the II=5 schedule recurrence.

The current first throughput wall is the reported FP32 accumulator recurrence. Simply increasing the PE count leaves the same distance-one dependency and does not establish a 2× issue rate. A doubled set of the observed 52 multiply/add pairs would add about 156 DSP, 28,912 LUT, and 22,308 FF before extra muxing, buffering, or routing. That would leave DSP use at roughly 27% of the device, while the current design already occupies 88.36% of CLB sites with only 1,704 sites free. The evidence therefore points to CLB placement and routing as the first physical risk after the recurrence is redesigned, not DSP exhaustion. This resource growth is a component-cost estimate, not a doubled HLS/Vivado result. URAM is already 62.5% occupied and lies on the worst routed data path; more banking or replication could tighten the limit, but the II report does not identify an URAM port conflict.

## Exact FFN orientation comparison

CPU rates come from the RM05 request profiles. RM08 board rates use only the 135 successful, same-shape, real-tensor `ffn_down` PL calls in the completed QID 37804 trace. Kernel rate divides MACs by HLS wait; call rate also includes host pack, synchronization, submit, and unpack. Datapath utilization is kernel GMAC/s divided by `52 × actual PL clock`. Route figures are schedule projections, not board observations.

| Operation / K-M-N / dtypes | RM05 CPU calls / GMAC/s | Exact-shape FPGA evidence | Datapath utilization |
|---|---:|---|---:|
| FFN up, 1152/4304/1120, F16×F32→F32 | 35 / 3.875 | No board measurement. OOC route projection: 197,670,886 HLS cycles at WNS-derived ~220.8 MHz = 6.203 GMAC/s; 5-call core projection 4.476 s. | 54.0% of 52×220.8 MHz, projection only |
| FFN up, 1152/4304/280, F16×F32→F32 | 100 / 3.827 | No exact-shape HLS/Vivado route or board result | N/A |
| FFN down, 4304/1152/1120, F16×F32→F32 | 35 / 1.332 | RM08 board: 3.857 kernel / 3.361 call GMAC/s at 99.999 MHz. RM07 route schedule projection: 7.282 GMAC/s at 187.512 MHz. | 74.2% board kernel; 64.6% including call boundary |
| FFN down, 4304/1152/280, F16×F32→F32 | 100 / 1.332 | RM08 board: 3.840 kernel / 3.319 call GMAC/s at 99.999 MHz. RM07 route schedule projection: 7.251 GMAC/s at 187.512 MHz. | 73.9% board kernel; 63.8% including call boundary |

The up and down operators at N=1120 perform the same 5.553 GMAC per call with opposite K/M orientations. RM05's measured CPU profile is 3.875 GMAC/s for up and 1.332 for down (2.91× difference). The only FPGA evidence for up is the corrected-shape OOC route projection; it has no PS/DDR path constraints and its WNS-derived 220.8 MHz is approximate. RM08 did not offload FFN-up. The RM08 down board speedups against the RM05 CPU profile are 2.90× kernel-only and 2.52× per call at N=1120, and 2.88× / 2.49× at N=280.

## Sources and reproduction

- RM07 HLS root cause, schedule, and route summary: [`RM07_HLS_ROOT_CAUSE.md`](../rm07/RM07_HLS_ROOT_CAUSE.md), [`RM07_RESULTS.md`](../rm07/RM07_RESULTS.md), and reports under [`experiments/rm07/evidence`](../rm07/evidence/).
- RM07 source conversion and accumulator loop: [`vision_ffn_down.cpp`](../rm07/source/bounded_k16/vision_ffn_down.cpp).
- RM05 profiles and up OOC route: [`RM05_RESULTS.md`](../rm05/RM05_RESULTS.md), [`q37804_vision_family_cpu_timing.csv`](../rm05/results/q37804_vision_family_timing/q37804_vision_family_cpu_timing.csv), and [`k16_ffn_up_corrected_shape`](../rm05/results/k16_ffn_up_corrected_shape/).
- RM08 board data and clock calibration: [`RM08_RESULTS.md`](../rm08/RM08_RESULTS.md) and [`rm08_pl_trace.txt`](../rm08/evidence/rm08-vlm-q37804-20260925T063228Z/rm08_pl_trace.txt).
- Recompute exact-shape CPU and board GMAC/s with `python3 scripts/rm09/compute_roof_extract.py`.
