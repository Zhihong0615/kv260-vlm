# RM08 KV260 recovery card

## Before the first PL load

- Connect to the board using SSH alias `kria` (`ubuntu@10.192.176.217`).
- Confirm `xmutil listapps` shows `k26-starter-kits`, XRT_FLAT, slot 0.
- Confirm `/sys/class/fpga_manager/fpga0/state` is `operating`.
- The captured boot ID is `2a931c48-99ad-4a3f-b3e1-f42634597098`; root is the
  writable SD root (`/dev/mmcblk1p2`). The exact A/B boot-firmware slot is
  UNKNOWN because `xmutil bootfw_status` requires interactive sudo.
- Latest direct-SSH snapshot (2026-09-25 02:37:49 UTC):
  `MemAvailable=3,295,496 kB`, `CmaTotal=1,024,000 kB`,
  `CmaFree=534,768 kB`. FPGA manager is `operating`; no RM07 UIO entry is
  present. The RM07 app files are installed under `/lib/firmware/xilinx/`.
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
RM07 UIO entries are gone. The path becomes verified only after one full
script execution is captured in `/tmp/rm08-first-load-smoke.log` and copied to
the repository evidence directory.

The prepared direct-SSH command is:

```bash
ssh -tt kria 'sudo bash /tmp/rm08-deploy/ssh_entrypoint.sh'
```

The app package files are installed on the writable root filesystem; tensors,
benchmark binary, and the latest diagnostic smoke script are staged under
`/tmp`. This command needs the board user's interactive sudo password. The
last run passed package hashes but did not leave an RM07 UIO device. The
timer self-test appears to have timed out at its old 5-second limit; its wait
is now 30 seconds and the script logs the failure point. Rerun the command.

If the kernel/board itself stops responding, SSH and the timer cannot recover
it; use a physical power cycle, which should return to the unchanged starter
kit boot image. This fallback has not been physically exercised.
