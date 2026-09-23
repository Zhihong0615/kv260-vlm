# KV260 USB Wi-Fi adapter inventory

Date: 2026-09-23 (Asia/Shanghai). Status: **native driver and scan PASS**.

| Field | Observed value |
|---|---|
| USB VID:PID | `0e8d:7612` |
| USB manufacturer | MediaTek Inc. |
| USB product | `802.11ac WLAN`; `lsusb` identifies MT7612U |
| USB topology | bus 001, device 004, port `1-1.3`, high-speed 480 Mb/s |
| Board kernel | `5.15.0-1027-xilinx-zynqmp` (aarch64) |
| In-kernel module | `mt76x2u.ko`; its `modinfo` alias explicitly includes `usb:v0E8Dp7612` |
| Module state | loaded and bound to USB interface `1-1.3:1.0` after firmware installation |
| Required firmware | `mt7662_rom_patch.bin`, `mt7662.bin` per `modinfo` |
| Current wireless interface | `wlx90de80defd0b` (connected to 5 GHz `ZJUWLAN`; Ethernet retained) |
| Current bound USB driver | `mt76x2u` (`lsusb -t`) |
| `ethtool -i` | driver `mt76x2u`, version `5.15.0-1027-xilinx-zynqmp`, firmware `0.0.00-b1`, bus `1-1.3:1.0` |
| `iw` | official Ubuntu 22.04 arm64 `iw` 5.16 executable staged under `/home/ubuntu/.local/bin/iw`, without system installation |
| Native-driver verdict | **PASS**: 2.4 and 5 GHz AP scan succeeds; no DKMS driver installed |

This identification is from the actual VID:PID and kernel module, not the
“AC1300” retail description. The mainline Linux
[`mt76x2u` USB device table](https://github.com/torvalds/linux/blob/master/drivers/net/wireless/mediatek/mt76/mt76x2/usb.c)
also includes `0x0e8d:0x7612`.

After the two Ubuntu firmware blobs were installed and the existing module
reloaded, the kernel reported the ROM patch and firmware build; the interface
appeared. `nmcli` detected 117 nearby AP entries, including open `ZJUWLAN`
on both 2.4 and 5 GHz. Examples: 2437 MHz at 95% and 5200 MHz at 90% signal.
The distinct `ZJUWLAN-Secure` is broadcast as WPA2 802.1X. The user's
approximate `ZJU-WLAN` spelling did not appear; the actual SSID is `ZJUWLAN`.
The project-local `iw dev` detects the interface and reports power saving
`off`; no global power-management setting was changed.
