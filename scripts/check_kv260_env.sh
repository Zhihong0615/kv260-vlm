#!/usr/bin/env bash
set -u

SSH_HOST="${KV260_SSH_HOST:-kria}"
SSH_OPTIONS=()
if [[ -n "${KV260_WIFI_IP:-}" ]]; then
  ssh_config="$(ssh -G "$SSH_HOST" 2>/dev/null)"
  host_key_alias="$(awk '$1 == "hostkeyalias" && $2 != "none" {print $2; exit}' <<<"$ssh_config")"
  if [[ -z "$host_key_alias" ]]; then
    host_key_alias="$(awk '$1 == "hostname" {print $2; exit}' <<<"$ssh_config")"
  fi
  if [[ ! "$KV260_WIFI_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ || -z "$host_key_alias" ]]; then
    printf '%s\n' 'KV260 environment: FAIL (invalid KV260_WIFI_IP or missing host-key alias)'
    exit 2
  fi
  SSH_OPTIONS=(-o "HostName=$KV260_WIFI_IP" -o "HostKeyAlias=$host_key_alias" -o StrictHostKeyChecking=yes)
fi
failures=0
pass() { printf 'PASS %-24s %s\n' "$1" "$2"; }
fail() { printf 'FAIL %-24s %s\n' "$1" "$2"; failures=$((failures + 1)); }

remote_output="$(ssh -o BatchMode=yes -o ConnectTimeout=5 "${SSH_OPTIONS[@]}" "$SSH_HOST" 'bash -s' <<'REMOTE'
set +e
status=0
printf '%s\n' "OS=$(. /etc/os-release; printf '%s' "$PRETTY_NAME")"
printf '%s\n' "KERNEL=$(uname -r)"
printf '%s\n' "ARCH=$(uname -m)"
printf '%s\n' "MEM=$(free -h | awk '/^Mem:/ {print $2}')"
printf '%s\n' "CMA=$(grep -i '^CmaTotal:' /proc/meminfo)"
if [[ -e /sys/class/fpga_manager/fpga0 ]]; then
  printf '%s\n' "FPGA_MANAGER=present"
else
  printf '%s\n' "FPGA_MANAGER=missing"
  status=1
fi
if command -v xmutil >/dev/null 2>&1; then
  printf '%s\n' "XMUTIL=$(command -v xmutil)"
else
  printf '%s\n' "XMUTIL=missing"
  status=1
fi
if grep -q '^CmaTotal:' /proc/meminfo; then :; else status=1; fi
listapps_output="$(sudo -n /usr/bin/xmutil listapps 2>&1)"
listapps_rc=$?
if [[ "$listapps_rc" -eq 0 ]] \
  && grep -Eq '^[[:space:]]*Accelerator[[:space:]]+Accel_type[[:space:]]+Base[[:space:]]+Base_type' <<<"$listapps_output" \
  && grep -Eq '^[[:space:]]*k26-starter-kits[[:space:]]+XRT_FLAT[[:space:]]+k26-starter-kits[[:space:]]+XRT_FLAT[[:space:]]' <<<"$listapps_output" \
  && ! grep -Eiq 'ERROR|Permission denied|Transport endpoint|password is required|not allowed' <<<"$listapps_output"; then
  printf '%s\n' "XMUTIL_LISTAPPS=ok"
  printf '%s\n' "XMUTIL_LISTAPPS_MODE=sudo-n-exact-command"
  printf '%s\n' "XMUTIL_LISTAPPS_OUTPUT_BEGIN"
  printf '%s\n' "$listapps_output"
  printf '%s\n' "XMUTIL_LISTAPPS_OUTPUT_END"
else
  printf '%s\n' "XMUTIL_LISTAPPS=permission-or-daemon-error"
  printf '%s\n' "XMUTIL_LISTAPPS_RC=$listapps_rc"
  printf '%s\n' "XMUTIL_LISTAPPS_DIAGNOSTIC=$listapps_output"
  status=1
fi
if dpkg -l 2>/dev/null | grep -q '^ii  xrt '; then
  printf '%s\n' "XRT_PACKAGE=$(dpkg -l | awk '/^ii  xrt / {print $3}')"
else
  printf '%s\n' "XRT_PACKAGE=missing"
  status=1
fi
xbutil_output="$(xbutil examine 2>&1 | tr -d '\000')"
printf '%s\n' "$xbutil_output"
if grep -q 'Model.*KV260' <<<"$xbutil_output" && grep -q '\[0000:00:00\.0\].*KV260.*Yes' <<<"$xbutil_output"; then
  printf '%s\n' 'XRT_DEVICE=ready'
else
  printf '%s\n' 'XRT_DEVICE=not-ready-or-unknown'
  status=1
fi
exit "$status"
REMOTE
)"
ssh_rc=$?

printf '%s\n' "$remote_output"
if [[ "$ssh_rc" -eq 255 ]]; then
  fail SSH "connection or authentication failed"
else
  pass SSH "$SSH_HOST reachable via ${KV260_WIFI_IP:-configured address}"
fi
if [[ "$ssh_rc" -ne 0 && "$ssh_rc" -ne 255 ]]; then
  fail remote_checks "remote audit returned $ssh_rc"
fi
grep -q '^FPGA_MANAGER=present$' <<<"$remote_output" && pass FPGA_manager present || fail FPGA_manager missing
grep -q '^CMA=CmaTotal:' <<<"$remote_output" && pass CMA "CmaTotal reported" || fail CMA unknown
grep -q '^XRT_DEVICE=ready$' <<<"$remote_output" && pass XRT_device ready || fail XRT_device not ready
grep -q '^XMUTIL_LISTAPPS=ok$' <<<"$remote_output" && pass xmutil_listapps ok || fail xmutil_listapps permission/daemon error

if [[ "$failures" -eq 0 ]]; then
  echo "KV260 environment: PASS"
  exit 0
fi
echo "KV260 environment: FAIL ($failures check(s))"
exit 1
