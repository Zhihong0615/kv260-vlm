# KV260 MT7612U driver diagnosis

Date: 2026-09-23 (Asia/Shanghai). Status: **resolved with official firmware; native driver PASS**.

The board already has a signed, in-tree `mt76x2u` module for its
`5.15.0-1027-xilinx-zynqmp` kernel. `lsmod` shows it loaded and `modinfo`
contains the exact `0e8d:7612` USB alias. No third-party DKMS driver or kernel
replacement is warranted.

The board kernel recorded:

```text
mt76x2u 1-1.3:1.0: ASIC revision: 76120044
mt76x2u 1-1.3:1.0: Direct firmware load for mt7662_rom_patch.bin failed with error -2
mt76x2u: probe of 1-1.3:1.0 failed with error -2
```

Before remediation, neither `/lib/firmware/mt7662_rom_patch.bin` nor
`/lib/firmware/mt7662.bin` existed on the board; the full `linux-firmware`
package was not installed there. The [Ubuntu 22.04 updates package file list](https://packages.ubuntu.com/jammy-updates/all/linux-firmware/filelist)
includes both files at these exact paths. The selected official package is
`linux-firmware_20220329.git681281e4-0ubuntu3.42_all.deb`; its
[Ubuntu package page](https://packages.ubuntu.com/jammy-updates/all/linux-firmware/download)
publishes SHA256 `ca7b1966610574959c044476f905761fb37a2cf2c0ea87778286a6f921afdcf1`.

## Resolution and verification

The official package digest matched the published SHA256 exactly. Only the
two files required by `modinfo` were extracted. The board staged copies and
installed `/lib/firmware/` copies all matched these hashes:

| File | SHA256 |
|---|---|
| `mt7662.bin` | `f7e52492f58088cae50e51a54cca68e4abc5b74f7d0b6b731dbb4c04465a94b6` |
| `mt7662_rom_patch.bin` | `6f0e871268f6e4d99196d90d89bcc09fe493d010366260a2cfcaa5dd66095f8c` |

The user entered board sudo interactively in their own terminal to install
the files with owner `root:root`, mode `0644`, then reload `mt76x2u`. The
kernel reported successful ROM patch and firmware loading, `lsusb -t` now
reports `Driver=mt76x2u`, `ethtool -i` identifies that driver and firmware,
and NetworkManager successfully scanned 2.4 and 5 GHz APs. This is a real
native-driver PASS; no DKMS, kernel, boot or image changes were made.
