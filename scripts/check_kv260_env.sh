#!/usr/bin/env bash
set -u

SSH_HOST="${KV260_SSH_HOST:-kria}"
failures=0
pass() { printf 'PASS %-24s %s\n' "$1" "$2"; }
fail() { printf 'FAIL %-24s %s\n' "$1" "$2"; failures=$((failures + 1)); }

remote_output="$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$SSH_HOST" 'bash -s' <<'REMOTE'
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
listapps_output="$(xmutil listapps 2>&1)"
if grep -Eiq 'ERROR|Permission denied|Transport endpoint' <<<"$listapps_output"; then
  printf '%s\n' "XMUTIL_LISTAPPS=permission-or-daemon-error"
  status=1
else
  printf '%s\n' "XMUTIL_LISTAPPS=ok"
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
if [[ "$ssh_rc" -ne 0 ]]; then
  fail SSH "remote checks returned $ssh_rc"
else
  pass SSH "$SSH_HOST reachable"
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
