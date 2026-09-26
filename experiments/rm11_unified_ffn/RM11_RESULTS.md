# RM11 Worker A checkpoint: shared Vision FFN

Status: **A53 tensor capture, board numeric gate, one shared-top route, and authorized standalone FFN-up board measurement are complete. The board restored to the starter kit; the total-call family projection is slower than CPU, so no full VLM integration is planned for this mapping.**

## A53 real tensor capture

The pinned AArch64 CPU runtime captured the first QID 37804 `ffn_up-0`, `ffn_up-13`, and `ffn_up-26` nodes. All three are contiguous rank-2 tensors with this exact signature:

| Layer | K/M/N | W | X | Y |
|---|---|---|---|---|
| up-0 | 1152/4304/1120 | F16 `[1152,4304]`, strides `[2,2304]`, 9,916,416 B | F32 `[1152,1120]`, strides `[4,4608]`, 5,160,960 B | F32 `[4304,1120]`, strides `[4,17216]`, 19,281,920 B |
| up-13 | 1152/4304/280 | F16 `[1152,4304]`, strides `[2,2304]`, 9,916,416 B | F32 `[1152,280]`, strides `[4,4608]`, 1,290,240 B | F32 `[4304,280]`, strides `[4,17216]`, 4,820,480 B |
| up-26 | 1152/4304/280 | F16 `[1152,4304]`, strides `[2,2304]`, 9,916,416 B | F32 `[1152,280]`, strides `[4,4608]`, 1,290,240 B | F32 `[4304,280]`, strides `[4,17216]`, 4,820,480 B |

All 9 payload SHA-256 values, input hashes, generated source/build hashes, board binary identity, logs, and stop provenance are retained in `evidence/board_capture/q37804-cpu/`. The pushed tree keeps the tensor SHA manifest at `evidence/board_capture/q37804-cpu/results/tensors.sha256`; the large W/X/Y payloads remain in the local evidence directory and the board's `/tmp/rm11-ffn-up-capture/results/tensors/`. Board up-0 hashes match the archived RM04 capture: W `c9987b77…7942f0b7`, X `67694f91…3d08b41b`, Y `611eed12…d43a5548`. QID capture ran CPU-only (`--device none -ngl 0`) against model SHA `8795741e…8279773`, mmproj SHA `ede8c227…e5c293`, and image SHA `3b62a66c…4cdf861f`.

The runner was stopped after all three requested callbacks, so its 4:05 process wall is not a full-request latency and no answer is attributed to it. A frozen full QID 37804 CPU correctness run already exists in RM05/RM10 evidence. The RM05 board-measured CPU call timings for these layers are:

| Layer | CPU call timing in RM05 five-call run | Shape |
|---|---:|---|
| up-0 | mean 1.431124 s; calls 1.440780, 1.431230, 1.425552, 1.425994, 1.432066 s | N=1120 |
| up-13 | mean 0.356086 s; calls 0.360797, 0.354601, 0.354763, 0.355412, 0.354856 s | N=280 |
| up-26 | mean 0.355858 s; calls 0.360559, 0.354950, 0.354606, 0.354584, 0.354589 s | N=280 |

The entire up family is 333.1915776 GMAC and 86.440139110 s CPU across 35 N=1120 and 100 N=280 calls (RM05). Applying RM10 down's ~83 s total-call family time gives only ~3.4 s potential up-family savings before orientation/packing/output movement. RM10's largest up boundary difference is output: 19.28 MB per N=1120 output versus 5.16 MB for down; the standalone harness measures output sync, payload bytes, and unpack separately.

## Numeric gate

The exact RM10 issue-4, ten-bank, fixed-tree FP32 numerical probe was run over every captured output against board-captured A53 Y. All passed max absolute error `<=1e-3`, RMSE `<=1e-4`, cosine `>=0.999`:

| Layer | Max absolute error | RMSE | Cosine | Gate |
|---|---:|---:|---:|---|
| up-0 | 3.81469727e-6 | 1.74861737e-7 | 0.999999999999570 | PASS |
| up-13 | 1.90734863e-6 | 2.03178285e-7 | 0.999999999999756 | PASS |
| up-26 | 6.10351562e-5 | 1.89108670e-6 | 0.999999999999780 | PASS |

The earlier x86-host comparison failed those thresholds. It is recorded separately and is not used as a board correctness result.

## Shared HLS top

The single configuration keeps the RM10 arithmetic (4x4 output PEs, issue-4 products, ten temporal FP32 banks, pairwise four-product reduction, same fixed tree, F16×F32 inputs, F32 outputs) and parameterizes active K and M. Max K/M storage remains 4304; K stride/group counts become runtime active-K values. The up last 128-output batch computes 80 valid channels and 48 zero-padded channels.

HLS C-simulation passed both cases: down `K/M=4304/1152` with the final full batch and up `1152/4304` with the final 80-valid/48-padded batch. Synthesis achieved II=1 at the K-group loop, reports 3.857 ns estimated versus the unchanged 5 ns HLS constraint, and estimates 329 DSP, 40 URAM, 54 BRAM18, 50,819 FF, 47,878 LUT. These are HLS estimates, not Vivado route results.

At the measured board PL clock of 100 MHz, the ideal loop-product lower bound is 86,768,640 K-group cycles (0.868 s) for N=1120 and 21,692,160 cycles (0.217 s) for N=280 for either orientation. These counts multiply the exact PE tile and issue-4 K-group loops; HLS's variable-bound latency column itself is unknown. They are cycle-count projections, not measured kernel times.

## Route and board gate

The one full-system route uses the RM10 PS/AXI/HP0/APM board design and 100 MHz PL0 with the unified IP. The runner measures up-0/up-13/up-26 with `35/1190`, `9/306`, and `9/306` stage/compute command counts, respectively (each stage command covers one N tile, each compute command one N-tile/M-batch pair). It compares the full output against board CPU Y and reports kernel time, full-call wall, GMAC/s, pack, XRT sync, unpack, APM DDR bytes, and restored starter-kit state. The exact-hash first load was authorized and completed for this bounded standalone measurement only.

## Routed image and bounded board procedure

Vivado 2024.2 completed full implementation, DRC, bitgen, XSA export, and platform validation. HLS synthesis retained its 5 ns target; the routed full-system design uses PL0 at 100 MHz (10 ns period). Routed setup WNS is `+3.158 ns`, TNS `0`, and all user constraints pass. Routed hold WHS is `+0.010 ns`, with zero failing endpoints. DRC reports zero errors; route status has 102,844 fully routed nets and zero routing errors. The hold margin is small but positive. Placed resources: 329 DSP48E2, 43,940 LUT, 55,731 registers, 18.5 BRAM tiles, 40 URAM, and 8,853/14,640 CLB sites (60.47%). Full timing, utilization, DRC, methodology, route, and congestion reports are in `evidence/full_system/`.

The exported HLS component SHA-256 is `210112b2e0836ca5a1f333df2291fbd3536a1c86b38964d2342ef352916e39c8`. Routed `.bit` SHA-256 is `72dfe46fbd27cc6a3dccf1defeaceef2e2939b9d7d4f679789ceae19a3657b81`; Bootgen `.bit.bin` is `53894991503d8d2882dfddb1222f564994222902e03592a19ad23c7d027d7bc6`; DTBO is `11390e7257225582ed3c9788d03ba302327cc4927eb7b63b5a5900c8fc7fce24`; and XSA is `1ae32941cea7307b6169915591218c0003d8df96e39f98298fbce9d8364fe9ef`. The complete package manifest is `package/kv260-rm11-unified-ffn/SHA256SUMS`.

The board has the package plus these pinned scripts staged under `/tmp/rm11-ffn-up-capture/`: standalone runner SHA-256 `d020e8e179057d621e42145efada5997e7609446e38c507c232d94f7afce7c5c`, restore helper SHA-256 `8820113c2bab844ab9ba9f27f92eb502b1f1dc58a7f7c2ec919d1161c26b66e2`. The preflight checks the board capture manifest, benchmark and identity binaries, starter-kit state, FCLK0 at 99,999,999 Hz, CMA headroom, and active processes. It arms a 4,200-second systemd rollback to `k26-starter-kits` before unloading the current app, probes the UIO/AXI-Lite identity, runs only the three standalone tensors, gates all outputs numerically, and explicitly restores the starter-kit. The image is not loaded until the parent Scheduler receives authorization for this exact `.bit.bin` SHA. Authorized invocation: `sudo env RM11_FIRST_LOAD_AUTHORIZED_SHA=53894991503d8d2882dfddb1222f564994222902e03592a19ad23c7d027d7bc6 bash /tmp/rm11-ffn-up-capture/run_up_standalone.sh`.

In the benchmark's `output_bytes` field, bytes count valid output payload after excluding padded channels/rows. Each compute command still XRT-syncs the fixed 16 KiB Y BO; at these shapes that is 19,496,960 bytes for N=1120 and 5,013,504 bytes for N=280. The reported XRT sync-from duration and APM Y-write counter capture that movement; APM W/X read and Y write counters are retained per call.

## Authorized standalone FFN-up result

The one authorized board run executed three calls total, one per captured layer. All three full output tensors passed the numeric gate. The raw per-call, APM, `time -v`, identity, and restore records plus SHA manifest are in `evidence/board_measurement/rm11-ffn-up-20260926T111621Z/`; its `SUMMARY.md` distinguishes actual calls from the weighted family projection.

| Layer | CPU mean (RM05) | PL kernel wait | PL total-call wall | Pack | Sync to/from | Unpack | Numeric |
|---|---:|---:|---:|---:|---:|---:|---|
| up-0 N=1120 | 1.431124 s | 1.344704 s | 1.664147 s | 206.249 ms | 4.110 / 3.063 ms | 101.193 ms | PASS |
| up-13 N=280 | 0.356086 s | 0.337764 s | 0.420664 s | 54.135 ms | 1.071 / 0.827 ms | 25.618 ms | PASS |
| up-26 N=280 | 0.355858 s | 0.338348 s | 0.420911 s | 53.541 ms | 1.107 / 0.881 ms | 25.767 ms | PASS |

Weighting the measured representative calls by RM05's 35×N1120 and 100×N280 request distribution gives an **estimated** FFN-up family PL kernel wait of 80.870240 s and **estimated total-call wall of 100.323895 s**, versus board-measured CPU family time of 86.440139 s. That is 13.883756 s slower (+16.06% time), with 0.8616× CPU-to-PL throughput ratio; estimated total-call throughput is 3.321 GMAC/s versus 3.855 GMAC/s CPU. The weighted boundary cost is about 12.60 s packing and 6.11 s output unpacking. This is a projection from one PL sample per layer, not an execution of the 135-call family.

The kernel alone is faster than CPU for this family, but the measured total-call estimate is not. **Stop before full VLM integration and do not build a second image for up** under the current mapping. The exact loadable `.bit.bin` hash used was `53894991503d8d2882dfddb1222f564994222902e03592a19ad23c7d027d7bc6`; the runner logged the exact-hash authorization and explicit restore passed at `11:16:28Z` with `run_exit_status=0`, manager `operating`, FCLK0 `99,999,999 Hz`, package cleanup PASS, and rollback timer stopped.

If total-call PL time does not beat the 86.44 s family CPU time by a material margin, stop before full VLM integration.
