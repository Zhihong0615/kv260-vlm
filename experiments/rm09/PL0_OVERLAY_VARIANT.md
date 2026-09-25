# RM09 PL0 clock overlay variant

This variant reuses the RM07 routed bitstream unchanged and adds a new
`xlnx,fclk` device to the RM07 overlay. Its `assigned-clocks` entry selects
ZynqMP clock ID 71 (PL0_REF), and `assigned-clock-rates` requests the RM07
XCI's actual PL0 rate, 187,498,123 Hz. The current RM08 overlay has neither
this clock device nor an assigned rate; its HLS/APM nodes only reference
`<&zynqmp_clk 71>`.

Build the DTBO with `experiments/rm09/build_pl0_187m5_dtbo.sh`. The package
contains a DTBO and the unchanged `shell.json`; use the already staged RM07
`.bit.bin` when preparing the test app. No Vivado route or HLS run is needed.
The generated file has not been loaded on the board.

The new `clocking0` child is intentional: a DT overlay that only updates
properties on the platform's existing `/fclk0` node may not rerun platform
probe, so its clock defaults may not be applied. Adding a new compatible node
under the already used `&amba` bus causes Linux's overlay platform notifier to
create a device, and the generic platform probe applies assigned clock defaults
before the `xlnx,fclk` driver runs.

## Rollback for the board owner

Keep the existing RM09 clock-sweep watchdog armed before staging or loading the
variant. On any mismatch or run failure, unload the RM07 app, set the existing
`/sys/bus/platform/devices/fclk0/set_rate` back to `100000000`, load
`k26-starter-kits`, then verify the starter-kit is active, FPGA manager is
`operating`, and RM07 UIO devices are absent. Leave the watchdog armed unless
all restore checks pass. Do not use this variant without the same protected
load/restore path already used for the clock sweep.
