#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" != 0 ]]; then
  echo "Run this script through sudo on the KV260." >&2
  exit 2
fi

deploy="${RM08_DEPLOY_DIR:-/tmp/rm08-deploy}"
app="kv260-rm07-bounded-k16"
base_app="k26-starter-kits"
tensor_dir="${RM08_TENSOR_DIR:-$deploy/tensors}"
runner="$deploy/ffn_down_bench"
smoke="$deploy/axilite_smoke"
rollback_unit="rm08-board-benchmark-rollback"
rollback_seconds="${RM08_ROLLBACK_SECONDS:-900}"
log="/tmp/rm08-board-bench-$(date -u +%Y%m%dT%H%M%SZ).log"

test -x "$runner"
test -x "$smoke"
for layer in 0 13 26; do
  for suffix in weight.f16 activation.f32 output.f32; do
    test -s "$tensor_dir/ffn_down-$layer.$suffix"
  done
done
test "$(cat /sys/class/fpga_manager/fpga0/state)" = operating
xmutil listapps | tee "$log"
grep -q "$base_app" "$log"

restore() {
  set +e
  xmutil unloadapp >/dev/null 2>&1
  xmutil loadapp "$base_app" >/dev/null 2>&1
  systemctl stop "$rollback_unit.timer" >/dev/null 2>&1
  systemctl stop "$rollback_unit.service" >/dev/null 2>&1
  systemctl reset-failed "$rollback_unit.timer" "$rollback_unit.service" >/dev/null 2>&1
  echo "starter_kit_restore=$(xmutil listapps 2>&1 | grep -q "$base_app" && echo PASS || echo FAIL)" | tee -a "$log"
  echo "restore_fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null)" | tee -a "$log"
  grep -E '^(MemAvailable|CmaTotal|CmaFree):' /proc/meminfo | tee -a "$log"
}
trap restore EXIT INT TERM

systemd-run --quiet --unit="$rollback_unit" --on-active="${rollback_seconds}s" \
  /bin/bash -c 'xmutil unloadapp >/dev/null 2>&1 || true; xmutil loadapp k26-starter-kits >/dev/null 2>&1'
xmutil unloadapp
xmutil loadapp "$app"
for _ in $(seq 1 120); do
  if [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null)" = operating ]] &&
     grep -q vision_ffn_down_tile_0 /sys/class/uio/uio*/name 2>/dev/null; then
    break
  fi
  sleep 0.5
done
test "$(cat /sys/class/fpga_manager/fpga0/state)" = operating
"$smoke" | tee -a "$log"
echo "board_temp_mC=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo UNKNOWN)" | tee -a "$log"
echo "cpu_freq_kHz=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo UNKNOWN)" | tee -a "$log"
echo "CMA before benchmark:" | tee -a "$log"
grep -E '^(MemAvailable|CmaTotal|CmaFree):' /proc/meminfo | tee -a "$log"
echo "tensor_dir=$tensor_dir runner_sha256=$(sha256sum "$runner" | awk '{print $1}')" | tee -a "$log"

run_case() {
  local layer="$1" n="$2" calls="$3"
  echo "BEGIN layer=$layer N=$n calls=$calls utc=$(date -u +%FT%TZ)" | tee -a "$log"
  "$runner" \
    "$tensor_dir/ffn_down-$layer.weight.f16" \
    "$tensor_dir/ffn_down-$layer.activation.f32" \
    "$tensor_dir/ffn_down-$layer.output.f32" \
    "ffn_down-$layer" "$n" "$calls" | tee -a "$log"
  echo "END layer=$layer N=$n calls=$calls utc=$(date -u +%FT%TZ)" | tee -a "$log"
}

# First calls use three actual captures across the early/middle/late transformer.
run_case 0 1120 1
run_case 13 280 1
run_case 26 280 1

# Five-call repeatability on one representative payload for each extent.
run_case 0 1120 5
run_case 13 280 5

# Shape-weighted 27-layer schedule replayed with captured representative tensors.
# This measures the actual call shape/buffer schedule, but is not a full capture
# of all 27 distinct layer payloads.
run_case 0 1120 35
run_case 13 280 100

echo "board_benchmark_log=$log" | tee -a "$log"
echo "benchmark_complete=PASS" | tee -a "$log"
