# KV260 network stack and campus Wi-Fi configuration

Date: 2026-09-23 (Asia/Shanghai).

NetworkManager is active and owns both network connections. The existing
`Wired connection 1` on `eth0` uses `192.168.77.2/24` when its cable is
attached; SSH alias `kria` is the wired recovery route. `systemd-networkd` and the legacy
`networking` service are inactive. `wpa_supplicant` is active; there is no
hand-written conflicting Wi-Fi configuration.

After installing the two required firmware blobs, the user entered board sudo
in their own terminal to create and activate the NetworkManager profile
`kv260-zjuwlan-5g` on `wlx90de80defd0b`. It is pinned to band `a` (5 GHz),
SSID `ZJUWLAN`, initially with `connection.autoconnect no`, IPv4 DHCP and requested
route metric 600. The current AP is `7c:1e:06:87:21:70` at 5200 MHz, signal
about -46 dBm. DHCP assigned `10.192.176.217/16`, gateway `10.192.0.1`,
DNS `10.10.0.21` and `10.10.2.21`. The Wi-Fi default route initially showed
metric 20600 while portal authentication was pending; after authentication it
shows the configured metric 600. When attached, the wired local route uses
metric 100.
The link was reachable over SSH from the host by its Wi-Fi IP with the existing
wired host key pinned.
After the initial link, the user used interactive board sudo to change
`connection.autoconnect` to `yes`. A read-back confirms that setting is saved
in the root-owned NetworkManager keyfile (mode `0600`). NetworkManager itself
is enabled for boot.

The user performed a real reboot on 2026-09-23: the board boot ID changed
from `1ba23886-d993-4fb9-aed2-91d6cca33f58` to
`44a20202-8e22-426e-9b2f-bfd84d663aea`. NetworkManager reactivated both
profiles without another command, and Wi-Fi-bound campus/external HTTPS plus
direct Wi-Fi SSH passed. The user later physically unplugged Ethernet for a
separate recovery-path test: the wired alias became unreachable and `eth0`
had no IPv4 address, but direct Wi-Fi SSH (5/5 fresh sessions) and
Wi-Fi-bound campus/external HTTPS still worked. `scripts/check_wifi.sh` can
be run in that condition with `KV260_WIFI_IP=10.192.176.217` to target the
known Wi-Fi IP while pinning the previously known host key; the default mode
still starts through `kria`. The user elected to continue with wireless SSH
and leave the Ethernet cable unplugged; its NetworkManager profile is retained
for future recovery. The equivalent direct SSH command from the host is:

```bash
ssh -o HostName=10.192.176.217 -o HostKeyAlias=192.168.77.2 kria
```

Because the Wi-Fi address is assigned by DHCP, it may change in the future;
verify the live address and update the command before reusing it after such a
change. The command reuses the existing `kria` identity and pins the known
board host key. `avahi-daemon` is active and enabled on the board, but
`getent hosts kria.local` did not resolve on this host across the campus
network; mDNS is therefore not treated as a proven stable alternative.

Target SSID provided by user: `ZJU-WLAN` (approximate spelling). Zhejiang
University's [current network service page](https://its.zju.edu.cn/90690/list.htm)
describes `ZJUWLAN` (without a hyphen) as an open Wi-Fi with web-portal
authentication, valid for 14 days; `ZJUWLAN-Secure` is a distinct 802.1X
network. The live scan confirms open `ZJUWLAN` on 2.4/5 GHz and separate WPA2
802.1X `ZJUWLAN-Secure`; no SSID with a hyphen appeared. Association to
`ZJUWLAN` needs no WPA password. Before portal login, plain HTTP was
intercepted with an instruction to visit `https://net2.zju.edu.cn/index_69.html`,
while DNS and external HTTPS timed out. A browser reached that HTTPS portal
through a loopback-only SSH tunnel terminating at the board; the page later
reported successful connection for the board's Wi-Fi IP. Board-side DNS and
HTTPS to `www.zju.edu.cn` and external `www.baidu.com`/`www.cloudflare.com`
then succeeded. No campus account credentials are stored in this project.

For link diagnostics, the official Ubuntu 22.04 arm64 `iw` 5.16 package was
hash-checked against its [Ubuntu download page](https://packages.ubuntu.com/jammy/arm64/iw/download)
(`4846d9df96435185ce4a18f937d52d91892ec57994167b97b0a70007ca62128c`).
Only the `iw` executable was copied to `/home/ubuntu/.local/bin/iw`; board
system packages and network services were not changed. Its executable SHA256
on the board is `9cf373cadad501d5c5e81fbae3d96c54a3ab354156b523e3ee083c5c6d950c9e`.
