# RM11 FFN-up standalone board measurement

Run ID: `rm11-ffn-up-20260926T111621Z`, board start `2026-09-26T11:16:21Z`, end/restore `2026-09-26T11:16:28Z`. This run executed **three calls total**: one each for early `ffn_up-0`, middle `ffn_up-13`, and late `ffn_up-26`. The 135-call family number below is a representative-call weighted projection, not 135 calls executed on the board.

## Exact image and inputs

- `.bit.bin` SHA-256: `53894991503d8d2882dfddb1222f564994222902e03592a19ad23c7d027d7bc6`
- `.bit` SHA-256: `72dfe46fbd27cc6a3dccf1defeaceef2e2939b9d7d4f679789ceae19a3657b81`
- DTBO SHA-256: `11390e7257225582ed3c9788d03ba302327cc4927eb7b63b5a5900c8fc7fce24`
- Standalone benchmark SHA-256: `b5932b15be19873ca6e7d5571e7111a7f0500d93aee2e8850393e8947060ee5e`
- Identity probe SHA-256: `eaec93be87723d59f19d4d8d2e4cb3bcb94a9f44af87c695ac63ef17e06eaf5a`
- Board tensor manifest SHA-256: `07e2bddab0daa54ec33d5872114b9ff81b3bfe67b256db9ed9ece20e9b436095`
- Capture model/mmproj/image hashes are recorded in `driver.log`; all three W/X/Y outputs passed the A53 CPU numeric comparison and the same probe passed again against PL output.

The measured target shapes are up-0 `K/M/N=1152/4304/1120`, up-13 and up-26 `1152/4304/280`. The wrapper observed 35 stage/1190 compute commands for N=1120 and 9/306 for N=280. The complete source tensor hashes and layout provenance are in `../../board_capture/q37804-cpu/results/tensors.sha256` and `../../board_capture/q37804-cpu/results/numeric/summary.csv`.

## One-call results

CPU comparison values are the RM05 board-measured five-call means for these same nodes. PL values are the one call measured here. Times are milliseconds except GMAC/s.

| Node | CPU call mean | PL kernel wait | Pack | XRT sync-to | XRT sync-from | Control submit | Output unpack | PL total-call wall | Kernel / system GMAC/s | Numeric max abs / RMSE / cosine |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| up-0, N=1120 | 1431.124 | 1344.704 | 206.249 | 4.110 | 3.063 | 2.645 | 101.193 | 1664.147 | 4.130 / 3.337 | 3.81469727e-6 / 1.74861737e-7 / 0.999999999999570 |
| up-13, N=280 | 356.086 | 337.764 | 54.135 | 1.071 | 0.827 | 0.683 | 25.618 | 420.664 | 4.110 / 3.300 | 1.90734863e-6 / 2.03178285e-7 / 0.999999999999756 |
| up-26, N=280 | 355.858 | 338.348 | 53.541 | 1.107 | 0.881 | 0.684 | 25.767 | 420.911 | 4.103 / 3.298 | 6.10351562e-5 / 1.89108670e-6 / 0.999999999999780 |

All three PL numeric gates passed: max absolute error `<=1e-3`, RMSE `<=1e-4`, cosine `>=0.999`.

| Node | APM W read (B) | APM X read (B) | APM Y write (B) | CMA minimum (kB) |
|---|---:|---:|---:|---:|
| up-0 | 350,945,280 | 5,160,960 | 19,496,960 | 239,612 |
| up-13 | 90,243,072 | 1,290,240 | 4,874,240 | 256,596 |
| up-26 | 90,243,072 | 1,290,240 | 4,874,240 | 255,016 |

The run entered with 262,628 kB CMA free; minimum observed was 239,612 kB. The standalone pool was 458,752 bytes for these K=1152 shapes, below the runner's 1,671,168-byte admission bound plus 8 MiB margin. After restore the snapshot reported 265,352 kB free.

## Family comparison (projection)

Weight the measured up-0 call by 35 N=1120 calls and the mean of the two measured N=280 calls by 100. This represents the RM05 QID 37804 transformer FFN-up population (333.1915776 GMAC, 35+100 calls):

| Metric | Board CPU reference | Weighted PL estimate | Difference |
|---|---:|---:|---:|
| FFN-up family wall | 86.440139 s | 100.323895 s | PL is 13.883756 s slower (+16.06% time) |
| Kernel wait only | — | 80.870240 s | Excludes host packing, XRT sync, output unpack, and call overhead |
| Effective throughput | 3.854 GMAC/s CPU | 3.321 GMAC/s PL total-call; 4.120 GMAC/s kernel | Total-call ratio 0.8616x CPU |

The weighted PL estimate components are 12.602515 s pack, 0.252750 s sync-to, 0.192605 s sync-from, 0.160925 s control submission, 6.111005 s output unpack, 80.870240 s HLS wait, and 0.133855 s remaining call-loop overhead. The benchmark's `output_bytes` field is logical valid payload. Each compute command syncs the fixed 16 KiB Y BO; APM separately records W/X reads and Y writes. Per-call APM W/X/Y bytes are tabulated above and retained in each raw layer log.

Because total-call wall is slower than the already-measured CPU family, **do not integrate FFN-up into a full VLM run with this mapping and do not start a second bitstream**. Kernel-only speed is not a system win: packing and unpacking dominate the available margin. This is a projection from one sample per representative layer, but its 13.9 s deficit is far beyond the roughly 3.4 s hoped-for margin and gives a decisive no-go for the current unified mapping.

## Restore and board state

The runner logged a 4200-second rollback timer before unloading the starter kit, verified HLS UIO identity and invalid-task ABI (`-4`), and completed all three numeric gates. Explicit restore completed at `11:16:28Z` with `starter_kit_restore=PASS`, `run_exit_status=0`, FPGA manager `operating`, and FCLK0 `99,999,999 Hz`. Package cleanup passed and the rollback timer was stopped. `restore.log` contains the starter-kit load result; `driver.log` contains timestamps, pre/post snapshots, timer identity, CMA and APM data, command counts, and raw numeric metrics.
