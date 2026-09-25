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

echo "utc=$(date -u +%FT%TZ) host=$(hostname)" | tee "$log"
echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)" | tee -a "$log"
grep -E '^(MemAvailable|CmaTotal|CmaFree):' /proc/meminfo | tee -a "$log"
xmutil listapps | tee -a "$log"
test "$(cat /sys/class/fpga_manager/fpga0/state)" = operating
grep -q "$base_app" "$log"

expected_bin="b8ba3e533b96e84f8cbb23acc8808146286671ccced979c9381f9afe9ddfbc60"
expected_dtbo="4fca210afb0258e7e67f6071a1d7d4c98681d60f847bfec5a3f00e0ab7c052d2"
expected_json="802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344"
printf '%s  %s\n' "$expected_bin" "$src_dir/$app.bit.bin" | sha256sum -c -
printf '%s  %s\n' "$expected_dtbo" "$src_dir/$app.dtbo" | sha256sum -c -
printf '%s  %s\n' "$expected_json" "$src_dir/shell.json" | sha256sum -c -

install -d -m 0755 "$install_dir"
install -m 0644 "$src_dir/$app.bit.bin" "$install_dir/$app.bit.bin"
install -m 0644 "$src_dir/$app.dtbo" "$install_dir/$app.dtbo"
install -m 0644 "$src_dir/shell.json" "$install_dir/shell.json"
xmutil listapps | tee -a "$log"
grep -q "$app" "$log"

# Prove that a transient rollback timer can fire before changing PL state.
check_unit="rm08-watchdog-check-$$"
rm -f /tmp/rm08-watchdog-check
systemd-run --quiet --unit="$check_unit" --on-active=2s /usr/bin/touch /tmp/rm08-watchdog-check
for _ in $(seq 1 50); do
  [[ -e /tmp/rm08-watchdog-check ]] && break
  sleep 0.1
done
test -e /tmp/rm08-watchdog-check
rm -f /tmp/rm08-watchdog-check
systemctl reset-failed "$check_unit.service" 2>/dev/null || true

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

xmutil unloadapp
xmutil loadapp "$app"
for _ in $(seq 1 120); do
  if [[ -e /sys/class/fpga_manager/fpga0/state ]] &&
     [[ "$(cat /sys/class/fpga_manager/fpga0/state)" = operating ]] &&
     grep -q vision_ffn_down_tile_0 /sys/class/uio/uio*/name 2>/dev/null; then
    break
  fi
  sleep 0.5
done
test "$(cat /sys/class/fpga_manager/fpga0/state)" = operating
gcc -O2 -Wall -Wextra "$src_dir/axilite_smoke.c" -o /tmp/rm08_axilite_smoke
/tmp/rm08_axilite_smoke | tee -a "$log"
echo "custom_app_smoke=PASS" | tee -a "$log"

restore
trap - EXIT INT TERM
test "$(cat /sys/class/fpga_manager/fpga0/state)" = operating
xmutil listapps | tee -a "$log"
grep -q "$base_app" "$log"
echo "starter_kit_restore=PASS" | tee -a "$log"
grep -E '^(MemAvailable|CmaTotal|CmaFree):' /proc/meminfo | tee -a "$log"
cat "$log"
