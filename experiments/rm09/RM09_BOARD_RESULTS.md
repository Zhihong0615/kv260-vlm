# RM09 board results

> **Earlier RM09 snapshot.** The statement below that the extra PS+PL pair was
> awaiting launch predates the static extent image. Both QID38299 and QID35419
> have since completed with real PL calls; see the [static extent board run](../rm09_static_extent/evidence/board/rm09-pl-q38299-q35419-20260925T122922Z/RESULTS.md).

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
`kv260-rm07-bounded-k16-pl0-187m5`. The corrected overlay probe loaded this
variant at 10:12Z, but FCLK0 still read 99,999,999Hz. Its guard stopped before
APM, tensor, or replay; the trap restored the starter-kit and 100MHz state.
Pre-load `clk_summary` showed `pl0_ref_mux=1,499,999,985Hz` and
`pl0_ref_div1=99,999,999Hz`. The overlay assignment was ignored by the
observed FCLK0 rate.

One guarded exact sysfs request of 187,498,123Hz was issued against the frozen
original RM07 setup on 2026-09-25. With all apps unloaded, the write returned
success but readback remained 99,999,999Hz. The guard stopped before loading
RM07, APM, tensor execution, or replay. The 30-minute watchdog was armed
before unload; the exit trap restored the starter-kit and 99,999,999Hz.
Restore PASS, frozen package hashes PASS, and watchdog timer inactive were
verified from the complete logs and a read-only board check. The clock study
is frozen at the safe 100MHz setting; no further rate was attempted. Full
evidence is under
[`evidence/rm09-sysfs-fclk-20260925T111725Z`](evidence/rm09-sysfs-fclk-20260925T111725Z).
The script used was `/tmp/rm09-sysfs-fclk-exact-probe.sh`, SHA-256
`90d7a21421bf23f6b05c78ab9293b439957fa3f95cfb2ac0dac05946155717fe`. It
follows the official Xilinx
[`xilinx_fclk.c`](https://github.com/Xilinx/linux-xlnx/blob/master/drivers/staging/fclk/xilinx_fclk.c)
sysfs path (`clk_round_rate()`, `clk_set_rate()`, and `clk_get_rate()` readback).

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
  persistence checks; `restore.log` records successful starter-kit
  restoration. The complete clock logs remain on the board under
  `/tmp/rm09-clock-sweep-20260925T071812Z/` and in the board-owner acquisition
  workspace. The compact tracked excerpts include their hashes.
- `evidence/rm09-sysfs-fclk-20260925T111725Z/driver.log` preserves the full
  exact-rate probe, its 99,999,999Hz readback, pre-benchmark rejection,
  rollback, and inactive watchdog; `restore.log` and pre-change clock
  diagnostics are included with hashes in `evidence/SHA256SUMS.txt`.
- The complete CPU `driver.log`, `stdout.log`, and `stderr.log` files remain on
  the board under the two run directories listed above and in the board-owner
  acquisition workspace. `time-v.txt` is tracked for each run; compact tracked
  raw answer/phase excerpts include hashes for all four source files per run.
- `evidence/runtime_library_resolution_20260925.txt` records the shared CPU
  library resolution and SHA used by the frozen runtime.
- `evidence/SHA256SUMS.txt` records hashes for these captured files.

Board run scripts are under `source/`; each root script checks its staged
dependencies by SHA, logs resource snapshots, arms a systemd rollback timer
before changing the active app, and restores the starter-kit at completion.
