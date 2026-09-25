# RM09 static extent board baseline

## Build and status

The single RM09 extent variant was built as a full KV260 PS + PL system with
Vivado 2024.2, targeting `xck26-sfvc784-2LV-c`. The PS PL0 setting and routed
clock constraint are 100.000 MHz / 10.000 ns, matching the board rate observed
in the RM09 clock audit. HLS `csynth` was not rerun: the previously synthesized
extent design was exported as catalog IP and used in this route. Its F16-W ×
F32-X → F32 arithmetic/reduction order and bounded W/X/Y staging are unchanged.

Vivado completed top-level synthesis, placement, route, bitgen, report
generation, XSA creation, and `validate_hw_platform`. Route status reports all
126,660 routable nets fully routed and zero routing errors. The routed DRC
found zero errors; it lists DSP pipelining and slice-pair warnings/advisories.
The timing report states that all user timing constraints are met. It also
notes 564 internal endpoints exempted from max-delay analysis because their
clock is constant.

The post-route `clk_pl_0` report gives 10.000 ns / 100.000 MHz, WNS +1.264 ns,
TNS 0, and zero failing setup endpoints. The final router estimate gives hold
WHS +0.010 ns and THS 0. The setup critical path is:

```text
HLS compute_weight_batch / VITIS_LOOP_97_9 / ap_enable_reg_pp0_iter3_reg/C
  -> HLS compute_weight_batch / VITIS_LOOP_97_9 / empty_398_fu_1662_reg[8]/D
```

Its routed data-path delay is 8.357 ns: 0.314 ns logic and 8.043 ns routing.
From this one run, `10.000 ns - 1.264 ns = 8.736 ns` implies about 114.47 MHz.
This is a slack-derived bound from one implementation, not a frequency sweep.
The previous RM07 route used a different 5.333 ns / 187.512 MHz constraint and
reported WNS +0.425 ns (about 203.75 MHz by the same calculation); those runs
are not an apples-to-apples Fmax comparison. The new image is proven to meet
100 MHz, not to preserve RM07's higher-clock headroom.

## Post-route resources

| Resource | RM07 route | RM09 static extent | RM09 utilization |
|---|---:|---:|---:|
| CLB LUTs | 66,603 | 66,769 | 66,769 / 117,120 (57.01%) |
| CLB registers | 67,541 | 67,564 | 67,564 / 234,240 (28.84%) |
| CLB sites | 12,936 | 12,563 | 12,563 / 14,640 (85.81%) |
| DSP48E2 | 184 | 183 | 183 / 1,248 (14.66%) |
| Block RAM | 10 RAMB36 + 17 RAMB18 | 10 RAMB36 + 17 RAMB18 | 18.5 / 144 tiles (12.85%) |
| URAM | 40 | 40 | 40 / 64 (62.50%) |

The bounded static correction adds 166 routed LUTs and 23 registers relative to
the archived RM07 system route; DSP, BRAM, and URAM use stay effectively the
same. Placement used fewer CLB sites in this run. The routed clock differs, so
placement occupancy and the timing comparison should be read with the clock
constraints above.

## Bitstream and package

Vivado generated a 6.5 MiB `.bit` and a 3.8 MiB fixed XSA. Bootgen converted the
`.bit` into the KV260 flat-app `.bit.bin`; DTC generated the overlay. The
package checksum check passed for all four runtime files.

| Artifact | SHA-256 |
|---|---|
| Vivado `.bit` | `9c657dacff87acaa62a447031d311b7dab804b2706ce0933a063e5dbd5367d81` |
| Fixed XSA | `c951b40554040eb0fa7e05a3a9703cf194bee0e913499fcec991319d3e68508a` |
| Bootgen `.bit.bin` | `819b088199ac4346c1eb9b7bb65ade42afe8f95eaeec02cca4bc6bdd2bb0d87b` |
| DTBO | `85fd0a2e2186886d8d52178c0934ba51585c37c28e5dd54a1c5536f2e506521e` |

The flat-app id is `kv260-rm09-static-extent`; its firmware filename is
`kv260-rm09-static-extent.bit.bin`. Package files are under
`experiments/rm09_static_extent/package/kv260-rm09-static-extent/`. The `.bit`
and `.bit.bin` files are generated artifacts ignored by Git; their hashes are
recorded in the tracked package `SHA256SUMS` and this note. The routed XSA and
full reports remain in the build root below.

This HLS IP has no dedicated immutable IP-ID register. The future load check
must identify it with UIO name `vision_ffn_down_tile_0`, compatible
`xlnx,vision-ffn-down-tile-1.0`, control window `0xa0010000–0xa001ffff`, and
the safe invalid-task `-4` return before submitting any DMA pointers. The APM
window is `0xa0000000–0xa000ffff`.

## Load and rollback status

The new image has **not** been loaded on the KV260. Package/hash validation is
host-side only; app enumeration, PL0 readback with this image, UIO probing,
safe invalid-task behavior, tensor calls, and rollback remain unverified for
this package. The prior board audit did not establish an independent recovery
path, so keep the starter-kit active until that gate and the board owner's load
authorization are in place.

The planned restore commands, if SSH survives an authorized future load, are:

```sh
sudo xmutil unloadapp
sudo xmutil loadapp k26-starter-kits
```

They have not been executed for RM09. Apply
`runtime_dispatch.patch` after RM08 and rebuild the host runtime before a
future PL test. The package supports the audited wide/narrow extent pairs for
token groups 60, 63, 64, 66, and 70; this build itself is not a QID38299 or
QID35419 board-inference result.

## Reproduction inputs and evidence

- System build root: `/tmp/rm09-static-board-system-20260925T112858Z-129110`
- Vivado log: `vivado.log` under that root
- Candidate HLS/export root: `/tmp/rm09-static-extent-20260925T095753Z-105433`
- Starter-kit checkout reused read-only from the RM07 workspace at revision
  `a722daa4536784a888693299eed46fb2ac0841a3`
- Rebuild system: `scripts/rm09/run_static_extent_system.sh`, setting
  `RM09_STATIC_EXTENT_HLS_ROOT` to the HLS root above
- Rebuild app files: `scripts/rm09/package_static_extent.sh`, setting
  `RM09_SYSTEM_ROOT` to the system root above
- Timing/utilization/route/DRC summary copies and hashes:
  `experiments/rm09_static_extent/evidence/full_system_20260925/`
