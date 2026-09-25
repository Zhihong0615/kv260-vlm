# RM09 PS PL0 clock reconciliation

## Findings

RM07 is not a 100 MHz Vivado design. `experiments/rm07/system/add_bounded_k16_bd.tcl`
sets `CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ` to `200.000` on
`zynq_ultra_ps_e_0`, and directly connects that PS `pl_clk0` to the HLS IP,
SmartConnect, APM, and PS AXI bridge clocks. The generated ZynqMP PS XCI
records `FREQMHZ=200.000`, `ACT_FREQMHZ=187.498123`, `SRCSEL=IOPLL`,
`DIVISOR0=8`, and `DIVISOR1=1`. The generated `psu_init.c`/`.tcl` also contains
the PL0 register programming for that configuration. The route timing report
constrains `clk_pl_0` at 5.333 ns / 187.512 MHz, and separately lists
`clk_pl_1` at 10 ns / 100 MHz. Thus 187.512 MHz is the rounded timing-report
rate for the RM07 PL0 route; it is not a request for a 100 MHz PL0 clock.

RM08's XRT flat app does not carry the RM07 XSA or run its generated
`psu_init` code. `experiments/rm08/source/build_flat_app.sh` converts only the
RM07 `.bit` to a PL-targeted Bootgen payload, compiles the custom overlay, and
packages `shell.json`. The overlay references `zynqmp_clk` clock 71 (PL0) for
the APM and HLS IPs but has no `assigned-clocks`, `assigned-clock-rates`, or
`xlnx,fclk` clock node. In this Linux-on-KV260 flat-app flow, the board's
existing PS setup therefore remains responsible for the PL0 clock when the
RM07 overlay is loaded. RM08's APM calibration measured 99.999 MHz, consistent
with the board's active starter-kit PS setup, not the XSA's RM07 PS setup.

The 150 MHz sysfs write is not proof that the clock changed to 150 MHz.
Xilinx's `xlnx,fclk` driver does `clk_round_rate()` before `clk_set_rate()` and
returns the write count when the rounded rate is successfully applied. A
successful write with readback still 99.999 MHz means the runtime clock path
accepted the rounded result; the host evidence does not identify whether the
rounding limit came from the active PS clock tree or PM firmware. The missing
RM07 overlay clock assignment explains why loading the flat app left PL0 at
the platform rate, but the 150 MHz rounding result still needs guarded runtime
validation.

## Minimal overlay variant

The built variant is in
`experiments/rm09/package/kv260-rm07-bounded-k16-pl0-187m5/`. It adds a new
`clocking0` child under the overlay's existing `&amba` target with:

```dts
compatible = "xlnx,fclk";
clocks = <&zynqmp_clk 71>;
assigned-clocks = <&zynqmp_clk 71>;
assigned-clock-rates = <187498123>;
```

It uses the XCI's actual PL0 output, 187.498123 MHz, which is 13,877 Hz below
the routed timing limit of 187.512 MHz. The Xilinx SDT generator's ZynqMP
pattern creates an enabled `clocking0` xlnx,fclk node, associates clock ID
71 with PL0, and emits the assigned rate from the PS XSA's
`PL0_REF_CTRL__ACT_FREQMHZ`. Linux applies clock defaults during generic
platform probe; an overlay-added child on the already populated `&amba` bus
gets a platform device and probe when the overlay is applied. Using a new node
avoids relying on updated properties being re-applied to the board's existing
boot-time `/fclk0` node.

The DTBO uses the same `firmware-name` (`kv260-rm07-bounded-k16.bit.bin`) and
unchanged `shell.json`. It does not modify the `.bit.bin`, XSA, PS boot image,
or any boot firmware. No HLS or Vivado route was run for this variant. It has
not been staged or loaded on the board.

## Guarded board validation and rollback

When the board owner schedules validation, stage the DTBO as the RM07 app's
overlay while reusing its existing RM07 `.bit.bin`. Arm the established RM09
clock-sweep watchdog before any app unload/load. Accept the clock check only
if both `fclk0/set_rate` readback and APM clock calibration are within 1 MHz
of 187.498123 MHz, and verify the clock persists through app load. If the
assignment fails, readback differs, or benchmark fails: unload RM07, write
100000000 to `/sys/bus/platform/devices/fclk0/set_rate`, load
`k26-starter-kits`, then verify the starter app active, FPGA manager
`operating`, and RM07 UIO nodes absent. Leave the watchdog armed unless all
restore checks pass.

## Primary sources

- AMD PG201 documents that generated `psu_init.tcl` and `psu_init.c` contain
  PS initialization settings, including clocks and PLLs:
  [Output Generation](https://docs.amd.com/r/en-US/pg201-zynq-ultrascale-plus-processing-system/Output-Generation).
- The official Xilinx SDT generator emits the ZynqMP `clocking${index}` node,
  maps index 0 to clock ID 71, and writes `assigned-clock-rates` from
  `CONFIG.PSU__CRL_APB__PL${index}_REF_CTRL__ACT_FREQMHZ`:
  [system-device-tree-xlnx, 2024.2 source](https://github.com/Xilinx/system-device-tree-xlnx/blob/xlnx_rel_v2024.2/device_tree/data/device_tree.tcl#L3448-L3476).
- The device-tree clock binding says `assigned-clock-rates` is in Hz and
  corresponds to `assigned-clocks`:
  [Device Tree clock schema](https://github.com/devicetree-org/dt-schema/blob/main/dtschema/schemas/clock/clock.yaml).
- The Xilinx 2022.2 kernel's overlay notifier creates a platform device for a
  newly added child of a populated bus, and generic platform probe calls
  `of_clk_set_defaults()` before the driver's probe:
  [overlay notifier](https://github.com/Xilinx/linux-xlnx/blob/xlnx_rebase_v5.15_LTS_2022.2/drivers/of/platform.c#L677-L689),
  [platform probe](https://github.com/Xilinx/linux-xlnx/blob/xlnx_rebase_v5.15_LTS_2022.2/drivers/base/platform.c#L1397-L1410).
- Xilinx's FCLK driver binds `compatible = "xlnx,fclk"` and its sysfs store
  rounds the request, applies the rounded rate, then reports write success:
  [Xilinx `xilinx_fclk.c`, 2022.2 kernel line](https://github.com/Xilinx/linux-xlnx/blob/xlnx_rebase_v5.15_LTS_2022.2/drivers/staging/fclk/xilinx_fclk.c#L475-L499).
