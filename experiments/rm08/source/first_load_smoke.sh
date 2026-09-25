#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" != 0 ]]; then
  echo "Run this script once with sudo on the KV260." >&2
  exit 2
fi

app="kv260-rm07-bounded-k16"
base_app="k26-starter-kits"
src_dir="${1:-/tmp/rm08-deploy/$app}"
install_dir="/lib/firmware/xilinx/$app"
rollback_unit="rm08-first-load-rollback"
log="/tmp/rm08-first-load-smoke.log"

: >"$log"
exec > >(tee -a "$log") 2>&1
PS4='+ [${BASH_SOURCE##*/}:${LINENO}] '
set -x
trap 'rc=$?; echo "ERROR rc=$rc line=$LINENO command=$BASH_COMMAND"' ERR

echo "utc=$(date -u +%FT%TZ) host=$(hostname)"
echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
grep -E '^(MemAvailable|CmaTotal|CmaFree):' /proc/meminfo
apps="$(xmutil listapps)"
printf '%s\n' "$apps"
test "$(cat /sys/class/fpga_manager/fpga0/state)" = operating
grep -q "$base_app" <<<"$apps"

expected_bin="b8ba3e533b96e84f8cbb23acc8808146286671ccced979c9381f9afe9ddfbc60"
expected_dtbo="4fca210afb0258e7f67f6071a1d7d4c98681d60f847bfec5a3f00e0ab7c052d2"
expected_json="802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344"
printf '%s  %s\n' "$expected_bin" "$src_dir/$app.bit.bin" | sha256sum -c -
printf '%s  %s\n' "$expected_dtbo" "$src_dir/$app.dtbo" | sha256sum -c -
printf '%s  %s\n' "$expected_json" "$src_dir/shell.json" | sha256sum -c -

install -d -m 0755 "$install_dir"
install -m 0644 "$src_dir/$app.bit.bin" "$install_dir/$app.bit.bin"
install -m 0644 "$src_dir/$app.dtbo" "$install_dir/$app.dtbo"
install -m 0644 "$src_dir/shell.json" "$install_dir/shell.json"
apps="$(xmutil listapps)"
printf '%s\n' "$apps"
grep -q "$app" <<<"$apps"

# Prove the transient timer can fire before changing PL state. Allow for
# systemd scheduling jitter on the board rather than failing after 5 seconds.
echo "step=verify_rollback_timer"
check_unit="rm08-watchdog-check-$$"
rm -f /tmp/rm08-watchdog-check
systemd-run --quiet --unit="$check_unit" --on-active=2s /usr/bin/touch /tmp/rm08-watchdog-check
for _ in $(seq 1 300); do
  [[ -e /tmp/rm08-watchdog-check ]] && break
  sleep 0.1
done
if [[ ! -e /tmp/rm08-watchdog-check ]]; then
  echo "timer_self_test=FAIL unit=$check_unit.timer"
  systemctl status "$check_unit.timer" "$check_unit.service" --no-pager || true
  exit 1
fi
rm -f /tmp/rm08-watchdog-check
systemctl reset-failed "$check_unit.service" 2>/dev/null || true
echo "timer_self_test=PASS"

echo "step=arm_180s_restore"
systemd-run --quiet --unit="$rollback_unit" --on-active=180s \
  /bin/bash -c 'xmutil unloadapp >/dev/null 2>&1 || true; xmutil loadapp k26-starter-kits >/dev/null 2>&1'
restore() {
  set +e
  xmutil unloadapp >/dev/null 2>&1
  xmutil loadapp "$base_app" >/dev/null 2>&1
  systemctl stop "$rollback_unit.timer" >/dev/null 2>&1
  systemctl stop "$rollback_unit.service" >/dev/null 2>&1
  systemctl reset-failed "$rollback_unit.timer" "$rollback_unit.service" >/dev/null 2>&1
}
trap restore EXIT INT TERM

echo "step=load_custom_app"
xmutil unloadapp
xmutil loadapp "$app"
echo "loadapp_returned fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
set +x
for _ in $(seq 1 120); do
  if [[ -e /sys/class/fpga_manager/fpga0/state ]] &&
     [[ "$(cat /sys/class/fpga_manager/fpga0/state)" = operating ]] &&
     grep -q vision_ffn_down_tile_0 /sys/class/uio/uio*/name 2>/dev/null; then
    break
  fi
  sleep 0.5
done
echo "uio_names_begin"
for f in /sys/class/uio/uio*/name; do test -e "$f" && cat "$f"; done
echo "uio_names_end"
manager_state="$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
echo "post_load_fpga_manager=$manager_state"
[[ "$manager_state" = operating ]]
grep -q vision_ffn_down_tile_0 /sys/class/uio/uio*/name
set -x
gcc -O2 -Wall -Wextra "$src_dir/axilite_smoke.c" -o /tmp/rm08_axilite_smoke
/tmp/rm08_axilite_smoke
echo "custom_app_smoke=PASS"

restore
trap - EXIT INT TERM
test "$(cat /sys/class/fpga_manager/fpga0/state)" = operating
apps="$(xmutil listapps)"
printf '%s\n' "$apps"
grep -q "$base_app" <<<"$apps"
echo "starter_kit_restore=PASS"
grep -E '^(MemAvailable|CmaTotal|CmaFree):' /proc/meminfo
