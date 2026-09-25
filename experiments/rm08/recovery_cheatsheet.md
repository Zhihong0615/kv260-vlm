# RM08 KV260 recovery card

## Latest board state after first PL smoke and benchmark

- Connect to the board using SSH alias `kria` (`ubuntu@10.192.176.217`).
- Confirm `xmutil listapps` shows `k26-starter-kits`, XRT_FLAT, slot 0.
- Confirm `/sys/class/fpga_manager/fpga0/state` is `operating`.
- The captured boot ID is `2a931c48-99ad-4a3f-b3e1-f42634597098`; root is the
  writable SD root (`/dev/mmcblk1p2`). The exact A/B boot-firmware slot is
  UNKNOWN because `xmutil bootfw_status` requires interactive sudo.
- Latest direct-SSH snapshot (2026-09-25 02:45:58 UTC):
  `MemAvailable=3,289,892 kB`, `CmaTotal=1,024,000 kB`,
  `CmaFree=528,768 kB`. FPGA manager is `operating`; no RM07 UIO entry is
  present after the logged starter-kit restore. The RM07 app files remain
  installed under `/lib/firmware/xilinx/`.
  Non-root `xmutil` cannot access the DFX manager socket.
- USB-UART is not connected. User selected direct SSH. RM08 does not modify
  boot firmware, QSPI, SD image, or boot files.

## First-load rollback

The root-only smoke script first proves a transient systemd timer fires, then
arms a 180-second local restore before unloading the starter-kit app. Its
self-test now allows 30 seconds for timer scheduling and logs command failures.
It loads
the RM08 flat app, checks the UIO/HLS compatible string and AXI-Lite response,
then unloads RM08 and restores the starter kit. If SSH disappears while the
board OS remains alive, the timer runs:

```bash
xmutil unloadapp
xmutil loadapp k26-starter-kits
```

Manual restore over SSH is the same two commands with `sudo`. Expected final
state: FPGA manager `operating`; `xmutil listapps` shows `k26-starter-kits`;
RM07 UIO entries are gone. The first full load, AXI-Lite smoke, and restore
cycle passed; see the captured log in the repository evidence directory. A
physical recovery/power-cycle path still has not been exercised.

The prepared direct-SSH command is:

```bash
ssh -tt kria 'sudo bash /tmp/rm08-deploy/ssh_entrypoint.sh'
```

The app package files are installed on the writable root filesystem; tensors,
benchmark binary, and diagnostic scripts are staged under `/tmp`. The user
must enter the board user's sudo password in their local terminal. The first
RM07 load, AXI-Lite probe, starter-kit restore, and standalone benchmark have
now passed. The benchmark's `starter_kit_restore=PASS` is the latest software
rollback evidence.

If the kernel/board itself stops responding, SSH and the timer cannot recover
it; use a physical power cycle, which should return to the unchanged starter
kit boot image. This fallback has not been physically exercised.
