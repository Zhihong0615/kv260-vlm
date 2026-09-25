# RM09 static extent flat-app package

This package is generated from the RM09 static-extent routed bitstream for the
KV260 starter-kits `XRT_FLAT` app manager. Its PS PL0 configuration is 100 MHz,
matching the board rate observed in RM09. The DT overlay registers the same
AXI-Lite HLS control and APM UIO nodes as RM07 and does not attempt to change
the board clock.

Build the Vivado system with `scripts/rm09/run_static_extent_system.sh`, then
run `scripts/rm09/package_static_extent.sh` with `RM09_SYSTEM_ROOT` set to that
build's output directory. Both `.bit` and Bootgen `.bit.bin` hashes are
recorded in the static-board evidence note; the package `SHA256SUMS` covers
the `.bit.bin`, DTBO, DTSI, and `shell.json` files.

The runtime dispatch whitelist is in
`experiments/rm09_static_extent/runtime_dispatch.patch`; apply it after the
RM08 runtime patch and rebuild the host runtime before an eventual load test.
The HLS top retains the RM07 F16-W × F32-X → F32 accumulation and reduction
order, 32-row activation tile, four-row compute granularity, and bounded W/X/Y
staging.

No board load or rollback has been performed for this package. A future load
must first confirm an independent recovery path and board-owner authorization.
With SSH retained, the planned restore sequence is:

```sh
sudo xmutil unloadapp
sudo xmutil loadapp k26-starter-kits
```

After an authorized load, validate the app slot, FPGA manager state, both UIO
names and mapped register windows, PL0 near 100 MHz, an invalid-task safe
return before DMA, then the frozen real-tensor checks for N=1120/280 and new
N=1008/252 calls. These are future checks, not results claimed by this build.
