# KV260 Wi-Fi verification evidence

Date: 2026-09-23 (Asia/Shanghai). This record contains no campus account
credentials. Commands were run from the Ubuntu host unless noted. During the
tests before the alias fix, `kria` targeted wired `192.168.77.2`; commands
with `HostName=10.192.176.217` tested the board's Wi-Fi path. The local
`kria` alias now targets Wi-Fi, and `kria-eth` preserves the wired address.

## Radio, network and portal

The USB device is `0e8d:7612` and the active driver is the board kernel's
`mt76x2u`. `iw dev wlx90de80defd0b link` reported SSID `ZJUWLAN`, BSSID
`7c:1e:06:87:21:70`, 5200 MHz and a signal near -46 dBm. DHCP assigned
`10.192.176.217/16`; the existing `eth0` recovery IP remained
`192.168.77.2/24`.

A board-side, user-authorized targeted scan of 2437 MHz provided fresh
2.4 GHz evidence for the same SSID. Four `ZJUWLAN` BSS entries on 2437 MHz
had signals of -49, -40, -56 and -68 dBm, each last seen 44–52 ms before
the scan output. The associated BSS at 5200 MHz also appeared in the output,
but its `last seen` value was 434036 ms: it is **not** counted as a fresh
2437 MHz result. The separately observed live `iw link` connection remained
at 5200 MHz. BSS identifiers are omitted here because their exact values
are not needed to establish dual-band availability.

Before authentication, HTTP to `1.1.1.1` returned a 271-byte captive page
pointing at `https://net2.zju.edu.cn/index_69.html`, while DNS and HTTPS to
external sites failed. The user-facing portal was opened through a
loopback-only SSH tunnel, so the HTTPS request originated at the board. The
portal then identified the board's Wi-Fi IP as connected. Afterwards,
board-side DNS resolved names, and interface-bound, certificate-validated
HTTPS returned HTTP 200 from `www.zju.edu.cn` (campus), `www.baidu.com`
(external) and `www.cloudflare.com` (external). `github.com` timed out on this
campus path and is not used as the sole internet oracle.

The dedicated SSH tunnel and temporary Chrome profiles, including any portal
cookies, browser `Login Data`, and the temporary screenshot, were removed
after connectivity was verified. No password was entered into a project file,
shell command line, chat or logged checker output.

## Wi-Fi SSH, transfer and recovery

The host's route to `10.192.176.217` used its campus Wi-Fi interface
`wlp0s20f3`, source `10.193.75.62`. SSH to the board's Wi-Fi IP pinned the
already-known wired host key using `HostKeyAlias=192.168.77.2` and succeeded.
Ten separate connections with `ControlMaster=no` and `ControlPath=none`
each exited 0 (10/10), so they were not multiplexed through one session.

```text
Wi-Fi SSH reconnect 01 PASS
Wi-Fi SSH reconnect 02 PASS
Wi-Fi SSH reconnect 03 PASS
Wi-Fi SSH reconnect 04 PASS
Wi-Fi SSH reconnect 05 PASS
Wi-Fi SSH reconnect 06 PASS
Wi-Fi SSH reconnect 07 PASS
Wi-Fi SSH reconnect 08 PASS
Wi-Fi SSH reconnect 09 PASS
Wi-Fi SSH reconnect 10 PASS
```

An uncompressed SSH stream of 100 MiB from the host to the board returned
`104857600` bytes from board-side `wc -c`, exit 0, in 17.686 seconds
(approximately 5.65 MiB/s). A small `scp` upload and `rsync` download over
the same Wi-Fi IP matched byte-for-byte. The SHA256 on both ends was
`264d4348d81e7c785b0ed94f8a06b8a7aaa2843e727b67927591ca165452cc2a`;
both test copies and their temporary directories were removed.

```text
104857600
real 0m17.686s
264d4348d81e7c785b0ed94f8a06b8a7aaa2843e727b67927591ca165452cc2a  source
264d4348d81e7c785b0ed94f8a06b8a7aaa2843e727b67927591ca165452cc2a  rsync-returned-copy
SCP_RSYNC_WIFI=PASS (round-trip byte-for-byte)
TEMP_TRANSFER_FILES=REMOVED
```

Four host-to-board Wi-Fi pings returned 4/4, 0% loss, with
min/avg/max 4.253/4.949/5.707 ms. Board-side Wi-Fi pings to the host returned
4/4, 0% loss, 3.952/5.294/7.868 ms; to the Wi-Fi gateway, 4/4, 0% loss,
1.421/1.806/2.205 ms; and to `1.1.1.1`, 4/4, 0% loss,
85.186/95.157/108.955 ms. A separate 604-second periodic test completed
47/47 successful checks, each requiring the native driver, target SSID,
campus HTTPS, external HTTPS and direct Wi-Fi SSH. It reported:

```text
STABILITY_SUMMARY elapsed=604 checks=47 failures=0
```

The independent Wi-Fi-path ping used the host's campus Wi-Fi interface and
10-second intervals for 600.585 seconds. It sent and received 61/61 packets
with **0% loss**; min/avg/max/mdev round-trip time was
3.035/14.007/49.797/11.483 ms. A separate 605-second radio sampler checked
`iw dev wlx90de80defd0b link` 56 times and observed no disconnection
(`LINK_METRICS_SUMMARY elapsed=605 checks=56 failures=0`). Signal ranged from
-61 to -43 dBm, mostly around -45 dBm. Reported RX bitrate was 200 Mbit/s;
TX mostly 180–200 Mbit/s, with one idle sample at 6 Mbit/s. These are link
negotiation rates, not measured application throughput; the 100 MiB transfer
above provides the latter.

```text
61 packets transmitted, 61 received, 0% packet loss, time 600585ms
rtt min/avg/max/mdev = 3.035/14.007/49.797/11.483 ms
LINK_METRICS_SUMMARY elapsed=605 checks=56 failures=0
```

## Boot persistence and open checks

NetworkManager is enabled and active. After the user entered board sudo in
their own terminal, a read-back reported `connection.autoconnect=yes` for
`kv260-zjuwlan-5g`; its root-owned keyfile has mode `0600`. The two required
firmware blobs are present in `/lib/firmware/` with the verified hashes in
`wifi_driver_diagnosis.md`. Before the detached-Ethernet test, Ethernet was
still connected, and the host
enumerates the Xilinx carrier card's USB-UART ports,
including `/dev/ttyUSB1`. After the user temporarily granted the host account
access to this exact character device, opening it at 115200 baud and sending
one carriage return yielded the KV260 shell prompt.

The user then performed a normal `sudo reboot` through the board's SSH
terminal. The USB-UART monitor observed `reboot: Restarting system` at
10:28:43 +08:00, U-Boot at 10:28:45, `Starting kernel ...` at 10:28:58 and
the new Linux kernel starting at 10:28:59. The previous boot ID
`1ba23886-d993-4fb9-aed2-91d6cca33f58` changed to
`44a20202-8e22-426e-9b2f-bfd84d663aea`, ruling out a mere service restart.
Once SSH returned, NetworkManager was `enabled` and `active`, and both
`kv260-zjuwlan-5g` and the original wired profile were active. The Wi-Fi
profile still read `autoconnect=yes`; the native `mt76x2u` driver had loaded,
the link was associated with `ZJUWLAN` at 5200 MHz (-45 dBm), DHCP again
assigned `10.192.176.217/16`, and the Wi-Fi default route had metric 600.
The Ethernet recovery IP was still `192.168.77.2/24`. A fresh run of
`scripts/check_wifi.sh` returned exit 0 with campus HTTPS, external HTTPS,
direct Wi-Fi SSH and snapshot all PASS. This is a real post-reboot
auto-connection test, not merely inspection of a saved profile.

For the physical isolation test, the user unplugged the board's Ethernet
cable while keeping the USB-UART recovery path connected. The host's route to
the board's Wi-Fi IP used campus Wi-Fi `wlp0s20f3`, while the wired SSH endpoint
at `192.168.77.2` timed out. On the board, `eth0` had no IPv4 address. Five
fresh, non-multiplexed SSH sessions to `10.192.176.217` each succeeded and
reported the same new boot ID and Wi-Fi address. Board-side Wi-Fi-bound HTTPS
again returned HTTP 200 from `www.zju.edu.cn` and `www.baidu.com`. The
checker was extended with an optional `KV260_WIFI_IP` override so its full
snapshot could run with the cable physically detached; it returned exit 0,
`ETHERNET_IPV4=` empty, campus/external HTTPS PASS and direct Wi-Fi SSH PASS.
The default checker path uses the configured `kria` Wi-Fi alias. The override
pins the same known host key when a DHCP address must be supplied explicitly.

The user elected to keep using wireless SSH with the cable unplugged;
reattachment is therefore not a remaining acceptance gate. The wired
NetworkManager profile remains unchanged for later recovery.

After the installed board firmware hashes and post-reboot driver/link were
rechecked, the task-local, Git-ignored `work/wifi-firmware` extraction/download
cache (303 MiB) and the board staging directory
`/home/ubuntu/.cache/kv260-wifi-firmware` (224 KiB) were removed. The two
official firmware files in `/lib/firmware/` still matched their recorded
SHA256 hashes, `/home/ubuntu/.local/bin/iw` remained executable, and the
Wi-Fi link remained associated. These removed caches can be re-downloaded or
re-extracted from official packages if ever needed; no installed firmware,
project models or AMD/Xilinx toolchain content was deleted.

The reviewer-requested fresh dual-band scan, 10-minute stability, real reboot
and detached-Ethernet evidence are now recorded. The independent reviewer
subsequently ran the Wi-Fi-IP checker live with Ethernet still unplugged and
reported a final read-only **PASS**; see `wifi_review.md`.
