# Independent KV260 Wi-Fi review

Date: 2026-09-23 (Asia/Shanghai). Final independent read-only verdict:
**PASS** against the Chapter 26 S/T Wi-Fi acceptance criteria. The reviewer
did not edit project files or board settings and did not inspect passwords.

The reviewer checked the actual USB VID:PID `0e8d:7612`, signed in-tree
`mt76x2u` driver and installed official firmware hashes. No unnecessary
kernel, DKMS, boot or image change was found. `ZJUWLAN` is an open SSID with
web-portal authentication, not the separate 802.1X `ZJUWLAN-Secure` network;
Enterprise certificate settings are therefore not applicable. Project files
and the checker contain no campus credentials. The temporary portal browser
profiles, tunnel and screenshot were removed after authentication.

The reviewer examined the recorded fresh 2437 MHz scan alongside the live
5200 MHz link; the 604-second HTTPS/SSH, 600-second ICMP and 605-second radio
stability tests; the 100 MiB transfer, 10 independent reconnects and
hash-matching SCP/rsync; the changed boot ID and automatic post-reboot Wi-Fi
connection; and the physical detached-Ethernet test. With the cable still
unplugged, the reviewer independently ran
`KV260_WIFI_IP=10.192.176.217 ./scripts/check_wifi.sh` and obtained exit 0:
`eth0` had no IPv4 address, `ZJUWLAN` and `autoconnect=yes` were present,
campus/external HTTPS and direct Wi-Fi SSH passed, and the host route to the
Wi-Fi IP used `wlp0s20f3`. The post-reboot boot ID remained the new value.
The Ethernet NetworkManager profile and USB-UART recovery channel are
retained, even though the user elected to leave Ethernet unplugged and use
wireless SSH routinely. The installed firmware and local `iw` hashes remained
correct after temporary package/staging cleanup.

The checker reports a point-in-time snapshot only: it does not itself prove
the 10-minute tests, physical cable state or absence of SSH multiplexing.
Those items are supported by separate evidence in `wifi_evidence.md` and by
the reviewer's live route/`eth0` checks. The board's general SSH
authentication/firewall policy was outside this Wi-Fi review. The host's
temporary `/dev/ttyUSB1` ACL remains available for UART recovery and may be
removed if no longer needed. The Wi-Fi address is DHCP-assigned, so the
direct-SSH destination must be updated if it changes; Tailscale was optional
and was not authorized or installed. These are operational cautions, not
remaining Wi-Fi acceptance failures.
