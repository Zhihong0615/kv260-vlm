# KV260 campus Wi-Fi status

Date: 2026-09-23 (Asia/Shanghai). Overall: **PASS — association, portal,
HTTPS, Wi-Fi SSH, transfer, 10-minute stability, dual-band scan, real reboot
auto-connection, detached-Ethernet Wi-Fi operation and independent review**.

| Check | Status |
|---|---|
| Adapter VID:PID | `0e8d:7612` |
| Chipset | MediaTek MT7612U (actual USB identification and in-tree driver alias) |
| Driver / kernel | `mt76x2u` / `5.15.0-1027-xilinx-zynqmp` |
| Firmware | two official Ubuntu 22.04 `mt7662` blobs, installed and hash-verified |
| Wireless interface | `wlx90de80defd0b` |
| Driver / fresh 2.4 GHz scan / live 5 GHz link | PASS / PASS (2437 MHz, four BSS, last seen 44–52 ms) / PASS (5200 MHz) |
| Target SSID | `ZJUWLAN` (live scan; user's approximate `ZJU-WLAN` spelling) |
| Authentication | Open association + web portal, per ZJU official instructions and live scan |
| Campus account password | `REDACTED` — never requested in chat or saved to project |
| Association / Wi-Fi IP | PASS, 5 GHz 5200 MHz / `10.192.176.217/16` |
| Portal / campus HTTPS / external HTTPS | PASS / PASS / PASS |
| SSH over Wi-Fi / SCP / rsync | PASS / PASS / PASS; physical Ethernet detach PASS (5/5 fresh SSH, HTTPS) |
| 100 MiB host-to-board transfer | PASS, `104857600` bytes over Wi-Fi SSH in 17.686 s (~5.65 MiB/s) |
| Ten independent Wi-Fi SSH reconnects | PASS, 10/10 |
| 10-minute HTTPS/SSH stability / saved auto-connect / reboot reconnect | PASS (604 s, 47/47) / PASS (`yes`) / PASS (new boot ID, live Wi-Fi/HTTPS/SSH) |
| 10-minute Wi-Fi-path ping | PASS, 61/61 responses, 0% loss, 3.035/14.007/49.797 ms min/avg/max |
| 10-minute radio signal/bitrate sampling | PASS, 56/56 connected; -61 to -43 dBm |
| Tailscale | NOT REQUESTED, NOT INSTALLED |
| Ethernet recovery | Profile preserved; when attached after reboot, `eth0` used `192.168.77.2/24`; cable now intentionally unplugged |
| USB-UART recovery | PASS — Xilinx carrier serial channel `/dev/ttyUSB1` returned the KV260 shell prompt at 115200 baud |
| Independent Wi-Fi review | PASS — read-only live recheck with Ethernet cable detached |

The existing Ethernet configuration and USB-UART recovery path are untouched.
The host still enumerates the Xilinx ML Carrier Card's four USB serial ports;
after a temporary host ACL, channel `/dev/ttyUSB1` returned the board's shell
prompt at 115200 baud. The monitor then observed a real U-Boot and Linux
restart; the boot ID changed, and Wi-Fi reconnected automatically.
The user initially created a 5 GHz, non-autoconnect NetworkManager profile using board
sudo interactively. The browser portal reported success for the board's Wi-Fi
IP, and direct board-side HTTPS returned HTTP 200 from `www.zju.edu.cn`,
`www.baidu.com` and `www.cloudflare.com`. Direct `github.com` HTTPS timed out;
that single-site failure does not negate the other verified access. SSH to
the Wi-Fi IP succeeded with the known host key pinned. A 100 MiB stream reached
the board byte-for-byte over Wi-Fi SSH, all 10 independent reconnects worked,
and a small file made a hash-matching `scp` upload and `rsync` download through
the Wi-Fi IP. Their temporary files were removed after comparison. Reboot and
reconnection were tested successfully. The user enabled `connection.autoconnect`
through interactive board sudo; a separate read-back shows `yes`.
NetworkManager is enabled and active, the Wi-Fi keyfile exists under
`/etc/NetworkManager/system-connections/` with owner `root:root` and mode
`0600`, and both firmware blobs persist under `/lib/firmware/`. No campus
credentials are stored here. With the Ethernet cable physically detached,
the wired alias became unreachable and `eth0` had no IPv4 address, while five
independent Wi-Fi SSH sessions and interface-bound campus/external HTTPS all
worked. `KV260_WIFI_IP=10.192.176.217 ./scripts/check_wifi.sh` also passed
in that state. The user chose to continue over wireless SSH, so the cable
remains unplugged; the wired profile is preserved for future recovery. The
task-local Wi-Fi download/extraction cache and board staging copies were
removed after installed firmware hashes were verified again. The installed
firmware and local `iw` executable remain.
