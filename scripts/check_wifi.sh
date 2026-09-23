#!/usr/bin/env bash
# Read-only KV260 Wi-Fi snapshot. No NetworkManager secrets are queried.
set -uo pipefail

ssh_host="${KV260_SSH_HOST:-kria}"
wired_host="$(ssh -G "$ssh_host" 2>/dev/null | awk '$1 == "hostname" {print $2; exit}')"
wifi_override="${KV260_WIFI_IP:-}"
remote_ssh_options=()
if [[ -n "$wifi_override" ]]; then
  if [[ ! "$wifi_override" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ || -z "$wired_host" ]]; then
    printf '%s\n' 'REMOTE_CHECK=FAIL (KV260_WIFI_IP must be IPv4 and wired host-key alias must exist)'
    exit 2
  fi
  remote_ssh_options=(-o "HostName=$wifi_override" -o "HostKeyAlias=$wired_host" -o StrictHostKeyChecking=yes)
  printf 'REMOTE_TRANSPORT=Wi-Fi IP %s (wired host key pinned)\n' "$wifi_override"
else
  printf '%s\n' 'REMOTE_TRANSPORT=configured SSH alias'
fi

remote_output="$(ssh -T -o BatchMode=yes -o ConnectTimeout=5 "${remote_ssh_options[@]}" "$ssh_host" 'bash -s' <<'REMOTE'
set -u
wifi_if="$(nmcli -t -f DEVICE,TYPE device | awk -F: '$2 == "wifi" {print $1; exit}')"
if [[ -z "$wifi_if" ]]; then
  printf '%s\n' 'WIFI_INTERFACE=missing'
  printf '%s\n' 'WIFI_SNAPSHOT=BLOCKED (no wireless interface)'
  exit 2
fi
printf 'WIFI_INTERFACE=%s\n' "$wifi_if"
printf 'KERNEL=%s\n' "$(uname -r)"
if command -v ethtool >/dev/null 2>&1; then
  ethtool -i "$wifi_if" 2>/dev/null | awk -F': ' '
    /^driver:/ {print "DRIVER=" $2}
    /^version:/ {print "DRIVER_VERSION=" $2}
    /^firmware-version:/ {print "FIRMWARE_VERSION=" $2}
    /^bus-info:/ {print "BUS_INFO=" $2}'
fi
nmcli -f GENERAL.STATE,GENERAL.CONNECTION device show "$wifi_if" 2>/dev/null
active_profile="$(nmcli -g GENERAL.CONNECTION device show "$wifi_if" 2>/dev/null)"
if [[ -n "$active_profile" && "$active_profile" != -- ]]; then
  printf 'WIFI_AUTOCONNECT=%s\n' "$(nmcli -g connection.autoconnect connection show "$active_profile" 2>/dev/null)"
else
  printf '%s\n' 'WIFI_AUTOCONNECT=none'
fi
printf 'NETWORKMANAGER_BOOT=%s\n' "$(systemctl is-enabled NetworkManager 2>/dev/null)"
printf 'ETHERNET_IPV4=%s\n' "$(ip -4 -o addr show dev eth0 2>/dev/null | awk '{print $4; exit}')"
printf '%s\n' 'ACTIVE_AP_BEGIN'
nmcli -f IN-USE,SSID,BSSID,CHAN,FREQ,RATE,SIGNAL,SECURITY device wifi list ifname "$wifi_if" --rescan no 2>/dev/null |
  awk 'NR == 1 || /^[[:space:]]*\*/'
printf '%s\n' 'ACTIVE_AP_END'
iw_bin="$(command -v iw 2>/dev/null || true)"
if [[ -z "$iw_bin" && -x /home/ubuntu/.local/bin/iw ]]; then
  iw_bin=/home/ubuntu/.local/bin/iw
fi
if [[ -n "$iw_bin" ]]; then
  printf '%s\n' 'IW_LINK_BEGIN'
  "$iw_bin" dev "$wifi_if" link 2>/dev/null
  printf '%s\n' 'IW_LINK_END'
fi
wifi_ipv4="$(ip -4 -o addr show dev "$wifi_if" | awk '{print $4; exit}')"
printf 'WIFI_IPV4=%s\n' "${wifi_ipv4:-none}"
printf 'WIFI_DEFAULT_ROUTE=%s\n' "$(ip -4 route show default dev "$wifi_if" | head -n 1)"
if [[ -n "$wifi_ipv4" ]] && command -v curl >/dev/null 2>&1; then
  campus_code="$(curl --noproxy '*' -sS -o /dev/null --connect-timeout 4 --max-time 10 --interface "$wifi_if" -w '%{http_code}' https://www.zju.edu.cn/ 2>/dev/null)"
  campus_rc=$?
  if [[ "$campus_rc" -eq 0 && "$campus_code" == 200 ]]; then
    printf '%s\n' 'CAMPUS_HTTPS=PASS (www.zju.edu.cn HTTP 200 over Wi-Fi)'
  else
    printf 'CAMPUS_HTTPS=FAIL (curl rc=%s, HTTP %s)\n' "$campus_rc" "${campus_code:-none}"
  fi
  internet_pass=0
  for site in www.baidu.com www.cloudflare.com; do
    http_code="$(curl --noproxy '*' -sS -o /dev/null --connect-timeout 4 --max-time 10 --interface "$wifi_if" -w '%{http_code}' "https://$site/" 2>/dev/null)"
    curl_rc=$?
    if [[ "$curl_rc" -eq 0 && "$http_code" == 200 ]]; then
      printf 'INTERNET_HTTPS=PASS (%s HTTP 200 over Wi-Fi)\n' "$site"
      internet_pass=1
      break
    fi
    printf 'INTERNET_PROBE=%s curl_rc=%s HTTP=%s\n' "$site" "$curl_rc" "${http_code:-none}"
  done
  if [[ "$internet_pass" -eq 0 ]]; then
    printf '%s\n' 'INTERNET_HTTPS=FAIL (no external HTTPS probe succeeded)'
  fi
else
  printf '%s\n' 'CAMPUS_HTTPS=NOT_TESTED (no IPv4 or curl)'
  printf '%s\n' 'INTERNET_HTTPS=NOT_TESTED (no IPv4 or curl)'
fi
REMOTE
)"
remote_rc=$?
printf '%s\n' "$remote_output"
if [[ "$remote_rc" -ne 0 ]]; then
  printf 'REMOTE_CHECK=FAIL (ssh/remote status %s)\n' "$remote_rc"
  exit 1
fi

wifi_ip="$(sed -n 's/^WIFI_IPV4=//p' <<<"$remote_output" | head -n 1)"
wifi_ip="${wifi_ip%%/*}"
if [[ -z "$wifi_ip" || "$wifi_ip" == none || -z "$wired_host" ]]; then
  printf '%s\n' 'SSH_WIFI=NOT_TESTED (Wi-Fi IPv4 or wired host-key alias missing)'
  exit 1
fi
if ssh -T -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=yes \
  -o HostName="$wifi_ip" -o HostKeyAlias="$wired_host" "$ssh_host" true 2>/dev/null; then
  printf '%s\n' 'SSH_WIFI=PASS (wired host key pinned)'
else
  printf '%s\n' 'SSH_WIFI=FAIL (unreachable, client isolation or host-key mismatch)'
  exit 1
fi

if grep -q '^DRIVER=mt76x2u$' <<<"$remote_output" \
  && grep -q '^GENERAL.CONNECTION:.*kv260-zjuwlan-5g' <<<"$remote_output" \
  && grep -q '^[[:space:]]*SSID: ZJUWLAN$' <<<"$remote_output" \
  && grep -q '^CAMPUS_HTTPS=PASS' <<<"$remote_output" \
  && grep -q '^INTERNET_HTTPS=PASS' <<<"$remote_output"; then
  printf '%s\n' 'WIFI_SNAPSHOT=PASS (not full 10-minute/reboot acceptance)'
  exit 0
fi
printf '%s\n' 'WIFI_SNAPSHOT=PARTIAL (driver, SSID or HTTPS not verified)'
exit 1
