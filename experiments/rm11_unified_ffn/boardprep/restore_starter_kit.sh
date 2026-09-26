#!/usr/bin/env bash
set +e

if [[ "$(id -u)" -ne 0 || "$#" -ne 1 || "$1" != /* ]]; then
  echo "Usage: sudo bash $0 /absolute/restore-log" >&2
  exit 2
fi

restore_log="$1"
exec >>"$restore_log" 2>&1
echo "restore_begin_utc=$(date -u +%FT%TZ) boot_id=$(cat /proc/sys/kernel/random/boot_id)"

die() {
  echo "starter_kit_restore=FAIL reason=$*"
  echo "restore_end_utc=$(date -u +%FT%TZ)"
  exit 1
}

xmutil unloadapp
unload_rc=$?
echo "unload_rc=$unload_rc"
[[ "$unload_rc" -eq 0 ]] || die "xmutil_unloadapp_rc_$unload_rc"

uio_wait=0
for _ in $(seq 1 120); do
  if ! grep -q '^vision_ffn_unified_tile_0$' /sys/class/uio/uio*/name 2>/dev/null; then
    uio_wait=1
    break
  fi
  sleep 0.5
done
[[ "$uio_wait" == 1 ]] || die "rm11_uio_still_present"

printf '%s\n' 100000000 >/sys/bus/platform/devices/fclk0/set_rate
rate_rc=$?
rate="$(cat /sys/bus/platform/devices/fclk0/set_rate 2>/dev/null || echo UNKNOWN)"
echo "fclk0_set_rc=$rate_rc fclk0_readback_hz=$rate"
[[ "$rate_rc" -eq 0 && "$rate" != UNKNOWN ]] || die "fclk0_write_failed"
(( rate >= 99000000 && rate <= 101000000 )) || die "fclk0_not_near_100MHz"

xmutil loadapp k26-starter-kits
load_rc=$?
echo "starter_load_rc=$load_rc"
[[ "$load_rc" -eq 0 ]] || die "xmutil_starter_load_rc_$load_rc"

for _ in $(seq 1 120); do
  if [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null)" == operating ]] &&
     xmutil listapps 2>&1 | awk '$1 == "k26-starter-kits" && $NF ~ /^0,?$/ { found=1 } END { exit !found }'; then
    rate="$(cat /sys/bus/platform/devices/fclk0/set_rate 2>/dev/null || echo UNKNOWN)"
    [[ "$rate" != UNKNOWN ]] && (( rate >= 99000000 && rate <= 101000000 )) || die "starter_load_changed_fclk0"
    echo "starter_kit_restore=PASS"
    echo "fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state)"
    echo "fclk0_readback_hz=$rate"
    echo "restore_end_utc=$(date -u +%FT%TZ)"
    exit 0
  fi
  sleep 0.5
done
xmutil listapps 2>&1
die "starter_app_not_ready"
