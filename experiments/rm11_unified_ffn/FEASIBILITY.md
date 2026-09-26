# RM11 unified FFN feasibility gate

Status: **real FFN-up captures, A53 and PL numeric gates, the single shared-top route, and one authorized standalone PL run are complete.** The board restored to the starter kit. The current mapping loses to CPU on projected total-call family wall, so do not integrate up into a full VLM run.

## Frozen evidence before RM11 board access

RM05 directly timed the QID 37804 vision `ffn_up` nodes on KV260 with four A53 threads. The selected transformer up family is 35 calls at `N=1120` plus 100 calls at `N=280`; the total is 333.1915776 GMAC in 86.440139110 seconds. Per-layer rows include `ffn_up-0` at `K/M/N=1152/4304/1120` and `ffn_up-13` / `ffn_up-26` at `1152/4304/280`. These are board-measured CPU callback intervals from the RM05 trace, not a new RM11 run.

RM04 captured real QID 37804 CPU tensors for `ffn_up-0`: F16 W `[1152,4304]`, F32 X `[1152,1120]`, and F32 Y `[4304,1120]`, all contiguous. RM11 captured board-real W/X/Y for `ffn_up-0/-13/-26` on the pinned A53 CPU runtime. The up-0 hashes match the archived RM04 board capture; the two new captures add real middle/late board activations and outputs. Exact shape, stride, byte-size, hashes, and capture provenance are in `evidence/board_capture/q37804-cpu/results/`. The request process was stopped after the three target callbacks to save board time, so this is tensor-capture evidence, not a full QID run or timing. Frozen full-request correctness and timing remain sourced to RM05/RM10.

The issue-4/ten-bank/tree numeric probe compared every output to the A53-captured Y and passed RM10's max-error/RMSE/cosine thresholds on all three complete tensors. The host x86 rerun failed those thresholds and is retained separately as a host/board accumulation mismatch; it is not treated as board evidence. See `evidence/board_capture/q37804-cpu/results/numeric/summary.csv` and `evidence/host_capture/numeric/summary.csv`.

RM10 measured the strong `ffn_down` static engine at about 83 seconds total-call family wall for the same 333.1915776 GMAC request population. Applying that end-to-end rate to `ffn_up` predicts about 83.1 seconds versus 86.44 seconds CPU, only about 3.4 seconds / 3.9% family improvement before any up-orientation penalty. This is a feasibility screen, not an FFN-up FPGA measurement. The user-visible request is over 500 seconds, so this ceiling would change request wall by under one percent before interaction with other stages.

## Minimum shared-datapath parameter changes

The RM10 compute core can retain its 4x4 output PE, four-product issue, ten temporal accumulator banks, F16×F32 inputs, F32 output, reduction tree, 100 MHz PL clock, bounded input/output staging, and activation reuse. A single image supporting both orientations needs these dimension changes around that unchanged datapath:

| Parameter | FFN-down | FFN-up | Shared top requirement |
|---|---:|---:|---|
| Reduction K | 4304 | 1152 | Runtime `active_K`; reserve cache/port depth for 4304 |
| Output M | 1152 | 4304 | Runtime `active_M`; reserve max 4304 |
| Tokens N | 280 or 1120 | 280 or 1120 | Existing supported extents |
| K groups at issue-4 | 1076 | 288 | Runtime loop bound; both are multiples of four |
| 128-channel output batches | 9 | 34 | Runtime ceil-div; last up batch has 80 valid channels |

The HLS arrays stay sized for the existing maximum K, while activation/weight stage strides and compute loop bounds use `active_K`. The host packs only valid K words, zero-pads the last 48 output channels of the up family, and unpacks only `active_M` channels. That tail wastes 48 of 4304 output lanes (1.12% aggregate M work). PE width and arithmetic are unchanged. These are compile-time-max/runtime-extent parameter changes, not a new dataflow or novelty claim.

## Go/no-go gates

1. **PASS:** CPU-only capture has real W/X/Y for `ffn_up-0/-13/-26`; RM05 retains full QID CPU timing and answer `G`. RM11's capture request itself was intentionally stopped after the target tensors.
2. **PASS:** HLS C-simulation exercised down/up orientations and the padded up tail. The full-tensor numeric gate against the three A53 outputs passes.
3. **PASS:** the one parameterized image routed at 100 MHz with WNS `+3.158 ns`, WHS `+0.010 ns`, zero DRC errors, and 329 DSP/8,853 CLB sites. The authorized `.bit.bin` SHA-256 was `53894991503d8d2882dfddb1222f564994222902e03592a19ad23c7d027d7bc6`.
4. **PASS, bounded standalone only:** one call each for up-0/up-13/up-26 measured kernel, total-call wall, packing, XRT sync, unpack, APM, and numeric error. All numeric gates passed. The weighted 135-call family projection is 80.870240 s kernel wait and 100.323895 s total-call wall versus CPU's 86.440139 s; the projection is 13.883756 s slower, not a measured 135-call run. Raw logs and exact breakdown are in `evidence/board_measurement/rm11-ffn-up-20260926T111621Z/`.
5. **NO-GO for current up mapping:** its kernel-only estimate beats CPU, but packing and unpacking make total-call time 16.06% slower. Stop before full VLM integration and do not load a second image for this mapping.

Board capture ran after Worker B restored the starter kit and released its slot. The routed package, benchmark, and restore scripts were staged under `/tmp/rm11-ffn-up-capture/`; hashes are pinned in `RM11_RESULTS.md`. The authorized standalone run logged `starter_kit_restore=PASS`, `run_exit_status=0`, FPGA manager `operating`, and FCLK0 at 99,999,999 Hz. No full VLM request was attempted.

## Source evidence

- `experiments/rm04_system/RM04_RESULTS.md`: real `ffn_up-0` capture hashes, exact GGML tensor signature, and RM04 timing limits.
- `experiments/rm05/RM05_RESULTS.md`: board-measured CPU family/op timings and QID 37804 workload shapes.
- `experiments/rm05/results/q37804_vision_family_timing/q37804_vision_family_cpu_timing.csv`: exact 35×1120 and 100×280 up-family CPU time/MAC values.
- `experiments/rm10_boardprep/evidence/rm10-a-ra-q37804-20260926T083001Z/RESULTS.md`: RM10 measured family wall, kernel, packing, and call rates.
- `scripts/rm11/build_ffn_up_capture_cli.py`, `scripts/rm11/compile_ffn_up_capture_on_board.py`, and `scripts/rm11/run_q37804_ffn_up_capture.sh`: prepared multi-layer capture path. The local build is x86_64; the board script compiles against the pinned AArch64 runtime after staging. No board access is authorized by these scripts.
