#!/usr/bin/env bash
set -Eeuo pipefail

# Run as root on the KV260. FCLK0 is changed only while no XRT app is loaded.
# Each APM calibration is an independent measurement of the clock seen by RM07.

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run through sudo on the KV260: sudo bash $0" >&2
  exit 2
fi

readonly app="kv260-rm07-bounded-k16"
readonly base_app="k26-starter-kits"
readonly deploy="/tmp/rm08-deploy"
readonly tensor_dir="$deploy/tensors"
readonly runner="$deploy/ffn_down_bench"
readonly fclk0="/sys/bus/platform/devices/fclk0/set_rate"
readonly route_limit_hz=187512000
readonly requested_limit_hz=187500000
readonly target_tolerance_hz=1000000
readonly rollback_seconds=1800
readonly bit_sha="b8ba3e533b96e84f8cbb23acc8808146286671ccced979c9381f9afe9ddfbc60"
readonly install_dir="/lib/firmware/xilinx/$app"

for path in "$fclk0" "$runner"; do
  [[ -r "$path" ]] || { echo "missing required path: $path" >&2; exit 2; }
done
[[ -w "$fclk0" ]] || { echo "FCLK0 set_rate is not writable as root" >&2; exit 2; }
[[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == "operating" ]] || {
  echo "FPGA manager is not operating" >&2; exit 2;
}
[[ "$(tr -d '\000' </sys/firmware/devicetree/base/fclk0/compatible 2>/dev/null || true)" == "xlnx,fclk" ]] || {
  echo "fclk0 is not provided by the Xilinx xlnx,fclk driver" >&2; exit 2;
}
for layer in 0 13 26; do
  for suffix in weight.f16 activation.f32 output.f32; do
    [[ -s "$tensor_dir/ffn_down-$layer.$suffix" ]] || {
      echo "missing real tensor: $tensor_dir/ffn_down-$layer.$suffix" >&2; exit 2;
    }
  done
done

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_dir="/tmp/rm09-clock-sweep-$stamp"
install -d -m 0755 "$run_dir"
log="$run_dir/board.log"
restore_log="$run_dir/restore.log"
restore_script="$run_dir/restore_starter_kit.sh"
rollback_unit="rm09-clock-sweep-$stamp-rollback"
timer_armed=0
restore_ok=0

exec > >(tee -a "$log") 2>&1
umask 022

is_starter_active() {
  xmutil listapps 2>&1 | awk '$1 == "k26-starter-kits" && $NF ~ /^0,?$/ { found=1 } END { exit !found }'
}

snapshot() {
  local label="$1"
  echo "snapshot=$label utc=$(date -u +%FT%TZ)"
  echo "fclk0_rate_hz=$(cat "$fclk0" 2>/dev/null || echo UNKNOWN)"
  echo "fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
  echo "board_temp_mC=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo UNKNOWN)"
  echo "cpu0_scaling_cur_freq_kHz=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo UNKNOWN)"
  grep -E '^(MemAvailable|CmaTotal|CmaFree):' /proc/meminfo || true
}

cat >"$restore_script" <<'RESTORE'
#!/usr/bin/env bash
set +e
restore_log="${1:?restore log path required}"
exec >>"$restore_log" 2>&1
echo "restore_begin utc=$(date -u +%FT%TZ) boot_id=$(cat /proc/sys/kernel/random/boot_id)"
xmutil unloadapp
unload_rc=$?
echo "restore_unloadapp_rc=$unload_rc"
if grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null; then
  echo "restore_safety=FAIL rm07_uio_still_present"
  exit 1
fi
printf '%s\n' 100000000 >/sys/bus/platform/devices/fclk0/set_rate
set_rc=$?
rate="$(cat /sys/bus/platform/devices/fclk0/set_rate 2>/dev/null || echo UNKNOWN)"
echo "restore_fclk0_write_rc=$set_rc restore_fclk0_rate_hz=$rate"
if [[ "$set_rc" -ne 0 ]] || (( rate < 99900000 || rate > 100000000 )); then
  echo "restore_fclk0=FAIL"
  exit 1
fi
xmutil loadapp k26-starter-kits
load_rc=$?
echo "restore_load_starter_rc=$load_rc"
for _ in $(seq 1 120); do
  if [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null)" == "operating" ]] &&
     xmutil listapps 2>&1 | awk '$1 == "k26-starter-kits" && $NF ~ /^0,?$/ { found=1 } END { exit !found }'; then
    echo "restore_starter_kit=PASS"
    echo "restore_fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state)"
    echo "restore_fclk0_rate_hz=$(cat /sys/bus/platform/devices/fclk0/set_rate)"
    echo "restore_end utc=$(date -u +%FT%TZ)"
    exit 0
  fi
  sleep 0.5
done
echo "restore_starter_kit=FAIL"
echo "restore_fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
xmutil listapps 2>&1
exit 1
RESTORE
chmod 0700 "$restore_script"

finish() {
  local rc=$?
  local restore_rc=0
  trap - EXIT INT TERM
  set +e
  if [[ "$timer_armed" == 1 ]]; then
    echo "explicit_restore_begin utc=$(date -u +%FT%TZ)"
    /bin/bash "$restore_script" "$restore_log"
    restore_rc=$?
    cat "$restore_log"
    if [[ "$restore_rc" -eq 0 ]] &&
       [[ "$(cat /sys/bus/platform/devices/fclk0/set_rate 2>/dev/null)" -le 100000000 ]] &&
       is_starter_active; then
      restore_ok=1
      systemctl stop "$rollback_unit.timer" >/dev/null 2>&1
      systemctl stop "$rollback_unit.service" >/dev/null 2>&1
      systemctl reset-failed "$rollback_unit.timer" "$rollback_unit.service" >/dev/null 2>&1
    else
      echo "explicit_restore=FAIL; watchdog timer left armed"
      restore_rc=1
    fi
    snapshot after_restore
    echo "starter_kit_restore=$([[ "$restore_ok" == 1 ]] && echo PASS || echo FAIL)"
  fi
  if [[ "$rc" -eq 0 && "$restore_rc" -ne 0 ]]; then rc=1; fi
  echo "run_exit_status=$rc"
  exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "run_dir=$run_dir"
echo "host=$(hostname) utc=$(date -u +%FT%TZ)"
echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state)"
echo "rm07_bitstream_source_sha256=1d537918b45bc9a53afb290beecda379918b7fd1a14374d6b5173358d8291942"
echo "rm07_bootgen_payload_sha256=$bit_sha"
echo "rm07_bitstream_source_note=Vivado .bit is converted by Bootgen into the .bit.bin payload loaded by xmutil"
for bit_file in "$deploy/$app/$app.bit.bin" "$install_dir/$app.bit.bin"; do
  printf '%s  %s\n' "$bit_sha" "$bit_file" | sha256sum -c -
done
cmp -s "$deploy/$app/$app.bit.bin" "$install_dir/$app.bit.bin"
echo "bench_sha256=$(sha256sum "$runner" | awk '{print $1}')"
for layer in 0 13 26; do
  for suffix in weight.f16 activation.f32 output.f32; do
    sha256sum "$tensor_dir/ffn_down-$layer.$suffix"
  done
done
apps="$(xmutil listapps)"
printf '%s\n' "$apps"
is_starter_active || { echo "k26-starter-kits must be active before the sweep" >&2; exit 2; }
echo "fclk0_node_compatible=$(tr -d '\000' </sys/firmware/devicetree/base/fclk0/compatible)"
echo "fclk0_current_rate_hz=$(cat "$fclk0")"
echo "route_max_hz=$route_limit_hz requested_max_hz=$requested_limit_hz"
snapshot before_sweep

# Recovery is armed before unloading the currently active starter-kit.
systemd-run --quiet --unit="$rollback_unit" --on-active="${rollback_seconds}s" \
  /bin/bash "$restore_script" "$restore_log"
timer_armed=1
echo "rollback_timer=$rollback_unit.timer restore_after_seconds=$rollback_seconds"

run_case() {
  local layer="$1" n="$2" calls="$3"
  echo "BEGIN_CASE layer=$layer N=$n calls=$calls utc=$(date -u +%FT%TZ)"
  "$runner" \
    "$tensor_dir/ffn_down-$layer.weight.f16" \
    "$tensor_dir/ffn_down-$layer.activation.f32" \
    "$tensor_dir/ffn_down-$layer.output.f32" \
    "ffn_down-$layer" "$n" "$calls"
  echo "END_CASE layer=$layer N=$n calls=$calls utc=$(date -u +%FT%TZ)"
}

run_rate() {
  local target_hz="$1"
  local actual_hz loaded_hz log_lines measured_mhz
  echo "BEGIN_CLOCK requested_hz=$target_hz utc=$(date -u +%FT%TZ)"

  # FCLK0 must be changed only after unloading whichever app is active.
  xmutil unloadapp
  if grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null; then
    echo "ERROR RM07 UIO remained after xmutil unloadapp" >&2
    return 1
  fi
  echo "clock_change_state=app_unloaded"
  echo "fclk0_before_set_hz=$(cat "$fclk0")"
  printf '%s\n' "$target_hz" >"$fclk0"
  actual_hz="$(cat "$fclk0")"
  echo "fclk0_requested_hz=$target_hz fclk0_readback_hz=$actual_hz"
  if (( actual_hz > target_hz || actual_hz > route_limit_hz || actual_hz > requested_limit_hz ||
        target_hz - actual_hz > target_tolerance_hz )); then
    echo "clock_readback=REJECT rounded_rate_outside_target_tolerance_or_safe_limit"
    return 1
  fi
  echo "clock_readback=PASS rounded_rate_within_1MHz_target_tolerance_and_safe_limits"

  xmutil loadapp "$app"
  for _ in $(seq 1 120); do
    if [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == "operating" ]] &&
       grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null; then
      break
    fi
    sleep 0.5
  done
  [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == "operating" ]]
  grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name
  loaded_hz="$(cat "$fclk0")"
  echo "fclk0_after_rm07_load_hz=$loaded_hz"
  if [[ "$loaded_hz" != "$actual_hz" ]] ||
     (( loaded_hz > target_hz || loaded_hz > route_limit_hz || loaded_hz > requested_limit_hz )); then
    echo "clock_persistence_after_load=FAIL"
    return 1
  fi
  echo "clock_persistence_after_load=PASS"
  snapshot "before_benchmark_${target_hz}"

  log_lines="$(wc -l <"$log")"
  run_case 0 1120 1
  run_case 0 1120 35
  run_case 13 280 100
  measured_mhz="$(sed -n "$((log_lines + 1)),\$p" "$log" | sed -n 's/.*APM_CLOCK_CAL .*measured_MHz=\([0-9.]*\).*/\1/p')"
  echo "apm_measured_mhz_values=$(tr '\n' ',' <<<"$measured_mhz" | sed 's/,$//')"
  awk -v values="$measured_mhz" -v target="$(awk -v hz="$target_hz" 'BEGIN { printf "%.6f", hz / 1000000 }')" \
    -v tolerance="$(awk -v hz="$target_tolerance_hz" 'BEGIN { printf "%.6f", hz / 1000000 }')" \
    -v route="$(awk -v hz="$route_limit_hz" 'BEGIN { printf "%.6f", hz / 1000000 }')" \
    'BEGIN { n=split(values, a, "\n"); upper=target+tolerance; if (upper > route) upper=route; if (n != 3) exit 1; for (i=1; i<=n; i++) if (a[i] < target-tolerance || a[i] > upper) exit 1; }' || {
      echo "apm_clock_calibration=FAIL expected_three_measurements_within_1MHz" >&2
      return 1
    }
  echo "apm_clock_calibration=PASS samples=3 target_mhz=$(awk -v hz="$target_hz" 'BEGIN { printf "%.6f", hz / 1000000 }')"

  snapshot "after_benchmark_${target_hz}"
  xmutil unloadapp
  loaded_hz="$(cat "$fclk0")"
  echo "fclk0_after_rm07_unload_hz=$loaded_hz"
  if [[ "$loaded_hz" != "$actual_hz" ]]; then
    echo "clock_persistence_after_unload=FAIL"
    return 1
  fi
  echo "clock_persistence_after_unload=PASS"
  echo "END_CLOCK requested_hz=$target_hz actual_hz=$actual_hz utc=$(date -u +%FT%TZ)"
}

# 187.5 MHz is the requested ceiling. The Xilinx driver rounds the request;
# if the readback is above either limit, this sweep aborts and rollback runs.
run_rate 100000000
run_rate 150000000
run_rate 187500000
echo "clock_sweep_complete=PASS"
