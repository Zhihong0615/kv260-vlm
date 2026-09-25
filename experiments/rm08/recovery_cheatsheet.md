# RM08 KV260 recovery card

## Before the first PL load

- Connect to the board using SSH alias `kria` (`ubuntu@10.192.176.217`).
- Confirm `xmutil listapps` shows `k26-starter-kits`, XRT_FLAT, slot 0.
- Confirm `/sys/class/fpga_manager/fpga0/state` is `operating`.
- The captured boot ID is `2a931c48-99ad-4a3f-b3e1-f42634597098`; root is the
  writable SD root (`/dev/mmcblk1p2`). The exact A/B boot-firmware slot is
  UNKNOWN because `xmutil bootfw_status` requires interactive sudo.
- Latest direct-SSH snapshot (2026-09-25 02:22:05 UTC):
  `MemAvailable=3,300,264 kB`, `CmaTotal=1,024,000 kB`,
  `CmaFree=546,572 kB`. Starter-kit remains active and manager state is
  `operating`.
- USB-UART is not connected. User selected direct SSH. RM08 does not modify
  boot firmware, QSPI, SD image, or boot files.

## First-load rollback

The root-only smoke script first proves a transient systemd timer fires, then
arms a 180-second local restore before unloading the starter-kit app. It loads
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

The app package, tensors, and benchmark binary are staged under `/tmp` only.
This command needs the board user's interactive sudo password. RM08 has not
loaded the PL image yet.

If the kernel/board itself stops responding, SSH and the timer cannot recover
it; use a physical power cycle, which should return to the unchanged starter
kit boot image. This fallback has not been physically exercised.
