# RM09 board results

## Clock source and safe rate path

The KV260 `fclk0` sysfs endpoint is provided by Xilinx's `xlnx,fclk` driver. Its
`set_rate` store rounds a requested rate with `clk_round_rate()` and calls
`clk_set_rate()`; the read method reports `clk_get_rate()`. A successful write
therefore needs a readback check. See the primary source:
[Xilinx linux-xlnx `xilinx_fclk.c`](https://github.com/Xilinx/linux-xlnx/blob/master/drivers/staging/fclk/xilinx_fclk.c)
(the sysfs read/write implementation is around lines 462–497).

RM07's routed `clk_pl_0` constraint is 5.333 ns (187.512 MHz), while the
generated ZynqMP PS XCI produces 187.498123 MHz for PL0. The design also has a
separate PL clock at 100 MHz. These are the configured/routed clock limits; the
board initially ran RM07 at 99,999,999 Hz. The source `.bit` SHA is
`1d537918b45bc9a53afb290beecda379918b7fd1a14374d6b5173358d8291942`; Bootgen
creates the distinct `.bit.bin` payload SHA
`b8ba3e533b96e84f8cbb23acc8808146286671ccced979c9381f9afe9ddfbc60`, which is
the file loaded by `xmutil`. They identify the same RM07 build at different
packaging stages.

The board's 150 MHz sysfs write returned success but read back as
99,999,999 Hz. The rate guard rejected that result before any 150 MHz replay.
The direct sysfs sweep stopped at 150 MHz, so it did not write 187.5 MHz. No
above-100 MHz benchmark was attempted through sysfs. The readback stayed at
99,999,999 Hz across RM07 load/unload, and rollback restored the starter-kit
app with the same readback.

The separate RM09 overlay experiment requests PL0's generated PS rate with an
`assigned-clock-rates = <187498123>` property and adds a new `xlnx,fclk`
clocking node. It retains the frozen RM07 `.bit.bin` and XRT_FLAT `shell.json`.
The DTBO SHA is
`9cbb79e53f5610dfc5bffe431fbb1ea1b8fe572190d6d907059a38112c994010`; it is
staged in a separate xmutil app package named
`kv260-rm07-bounded-k16-pl0-187m5`. The probe script verifies the original
RM07 package hashes, adds symlinks to the exact original bitstream under both
the firmware-name and app-name filenames, arms a 30-minute restore timer,
checks actual FCLK and APM rates against the 187.512 MHz routed ceiling, and
requires a passing real N1120 tensor before its 135-call replay. At this
snapshot, the variant has been staged in `/tmp` on the board, but has not been
loaded.

## 100 MHz tensor and replay measurements

The 100 MHz RM07 APM calibration read 99.999 MHz in all three cases. Direct
tensor benchmark results from the captured QID37804 tensors:

| Case | Wall | HLS wait | Numeric check |
| --- | ---: | ---: | --- |
| N1120, 1 call | 1.650881 s | 1.439642 s | max abs `1.14440918e-05`, RMSE `1.80431792e-07`, cosine `0.999999999999816` |
| N1120, 35 calls | 57.722715 s | 50.389384 s | same max abs/RMSE/cosine as 1 call |
| N280, 100 calls | 41.596902 s | 36.148131 s | max abs `1.98930502e-06`, RMSE `1.08140651e-07`, cosine `0.999999999999797` |
| 135-call replay total | 99.319617 s | 86.537515 s | PASS |

## Four-thread CPU comparison runs

Both baselines used the frozen Q4 model, F16 mmproj, exact image SHA, and
`-t 4 -tb 4 --device none -ngl 0`; PL dispatch was unset. The board stayed on
the starter-kit, FPGA manager `operating`, FCLK0 99,999,999 Hz, and no swap was
used. The resolved `libggml-cpu.so.0.24.0` SHA was
`7351973a8d004b7380f27dd0849aa4d2965e4c91b9f473d99696efb8cbf2a265`.

| QID | Media groups | Frozen answer | Wall | Peak RSS | Result |
| --- | ---: | --- | ---: | ---: | --- |
| 38299 | 3 | `3` | 6:08.19 | 1,855,764 KiB | PASS |
| 35419 | 7 | `SHERIFF'S` | 14:10.48 | 1,861,692 KiB | PASS |

These runs use the same board, four-thread settings, and exact image data as
the planned 100 MHz PS+PL requests. The PS+PL run for both QIDs is staged and
awaiting the user's sudo launch. Its request timeout is 1200 seconds each and
the systemd restore timer is 3000 seconds, covering both sequential timeouts
plus package load/restore. Before making VLM calls it verifies FCLK0 remains in
the 99–101 MHz band after loading RM07, and confirms the resolved CPU library
path and SHA.

## Board evidence

- `evidence/clock-sweep-20260925T071812Z/board.log` records the 100 MHz
  standalone and replay metrics, rejected 150 MHz readback, and clock
  persistence checks.
- `evidence/clock-sweep-20260925T071812Z/restore.log` records successful
  starter-kit restoration.
- `evidence/cpu-q38299-20260925T073450Z/` and
  `evidence/cpu-q35419-20260925T074749Z/` preserve the complete CPU request
  logs, time reports, and stdout/stderr.
- `evidence/runtime_library_resolution_20260925.txt` records the shared CPU
  library resolution and SHA used by the frozen runtime.
- `evidence/SHA256SUMS.txt` records hashes for these captured files.

Board run scripts are under `source/`; each root script checks its staged
dependencies by SHA, logs resource snapshots, arms a systemd rollback timer
before changing the active app, and restores the starter-kit at completion.
