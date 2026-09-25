#!/usr/bin/env bash
set -Eeuo pipefail

# One guarded exact-rate request against the official Xilinx fclk0 sysfs API.
# This changes the active FCLK only after unloading starter-kit. A failed
# readback/numeric gate restores 100 MHz and starter-kit without replaying.

readonly app=kv260-rm07-bounded-k16
readonly starter_app=k26-starter-kits
readonly board_root=/home/ubuntu/kv260-vlm-p2-cpu
readonly deploy=/tmp/rm08-deploy
readonly tensor_dir=$deploy/tensors
readonly runner=$deploy/ffn_down_bench
readonly fclk0=/sys/bus/platform/devices/fclk0/set_rate
readonly restore_script=/tmp/rm09-restore-starter-kit.sh
readonly diagnostics_script=/tmp/rm09-clock-diagnostics.sh
readonly restore_sha=ef428ea3e9215897310cfeaa5d79a4be320005ac8bbd6655c8505f2a9abe7e23
readonly diagnostics_sha=3f77d1b8cc7ba0ecce195aacce5c6e9d125d38bb3e7d48eb937895ad74586058
readonly bit_sha=b8ba3e533b96e84f8cbb23acc8808146286671ccced979c9381f9afe9ddfbc60
readonly dtbo_sha=4fca210afb0258e7f67f6071a1d7d4c98681d60f847bfec5a3f00e0ab7c052d2
readonly shell_sha=802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344
readonly runner_sha=c687a693d20a95c81787754aa07b49f51e3cf868116f8652aa22f6d4f30ac914
readonly requested_hz=187498123
readonly route_ceiling_hz=187512000
readonly target_tolerance_hz=1000000
readonly safe_hz=100000000
readonly rollback_seconds=1800
readonly case_timeout_seconds=300
readonly tensor_hashes=(
  b2e5111fdd29185654baf47e5437e322ec9433ec58f75921b2a82e2bb2117676
  80dfa4a1d48dfa3519ae173eb551bdd22822f075e25d0a5373ace96b6cb12305
  cabb0c46016184dc66a44177fdc9c209816c864db975fce9b1f064ca5da6c9fe
  38311e9e31a292f0dd1f1e955e051ec3d1d97f9543a2decebd47e78ec7b55ce2
  0bc7cc1b61f1e7f1267d9b406fdc4d760f76054c0ee0c78f5dd7e537b2d6013b
  39efbf7ee3633615bf173e66df3052f7ca141f634699f4eefe9e7c1447c264b7
)

die() { echo "ERROR: $*" >&2; exit 1; }
sha256_of() { sha256sum "$1" | awk '{print $1}'; }
valid_sha() { [[ "$1" =~ ^[0-9a-f]{64}$ ]]; }

if [[ "$(id -u)" -ne 0 || "$#" -ne 0 ]]; then
  echo "Usage: sudo bash $0" >&2
  exit 2
fi

for value in "$restore_sha" "$diagnostics_sha" "$bit_sha" "$dtbo_sha" "$shell_sha" "$runner_sha" "${tensor_hashes[@]}"; do
  valid_sha "$value" || die "invalid pinned SHA-256 length/value: $value"
done

readonly install_dir=/lib/firmware/xilinx/$app
readonly bit_file=$install_dir/$app.bit.bin
readonly dtbo_file=$install_dir/$app.dtbo
readonly shell_file=$install_dir/shell.json
readonly fclk_compatible=/sys/firmware/devicetree/base/fclk0/compatible

[[ -x "$restore_script" && "$(sha256_of "$restore_script")" == "$restore_sha" ]] || die "restore helper missing, not executable, or changed"
[[ -r "$diagnostics_script" && "$(sha256_of "$diagnostics_script")" == "$diagnostics_sha" ]] || die "diagnostics helper missing or changed"
for path in "$fclk0" "$runner" "$bit_file" "$dtbo_file" "$shell_file"; do [[ -r "$path" ]] || die "missing required path $path"; done
[[ -x "$runner" && -w "$fclk0" ]] || die "runner or FCLK0 permission check failed"
[[ "$(sha256_of "$runner")" == "$runner_sha" ]] || die "ffn_down_bench SHA mismatch"
[[ "$(sha256_of "$bit_file")" == "$bit_sha" ]] || die "frozen RM07 .bit.bin SHA mismatch"
[[ "$(sha256_of "$dtbo_file")" == "$dtbo_sha" ]] || die "frozen RM07 .dtbo SHA mismatch"
[[ "$(sha256_of "$shell_file")" == "$shell_sha" ]] || die "frozen RM07 shell.json SHA mismatch"
[[ "$(tr -d '\000' <"$fclk_compatible" 2>/dev/null || true)" == xlnx,fclk ]] || die "fclk0 is not the Xilinx xlnx,fclk node"
[[ "$(readlink -f /sys/bus/platform/devices/fclk0/driver 2>/dev/null || true)" == */xilinx_fclk ]] || die "fclk0 driver is not xilinx_fclk"
[[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] || die "FPGA manager is not operating"
xmutil listapps 2>&1 | awk -v app="$starter_app" '$1 == app && $NF ~ /^0,?$/ { found=1 } END { exit !found }' || die "starter-kit must be active at entry"
[[ "$(cat "$fclk0")" == 99999999 ]] || die "expected measured safe 100MHz FCLK0 at entry"
[[ -z "$(pgrep -x llama-mtmd-cli || true)" ]] || die "a VLM CLI is active"
! grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null || die "RM07 HLS UIO unexpectedly active at entry"

tensor_paths=(
  "$tensor_dir/ffn_down-0.weight.f16" "$tensor_dir/ffn_down-0.activation.f32" "$tensor_dir/ffn_down-0.output.f32"
  "$tensor_dir/ffn_down-13.weight.f16" "$tensor_dir/ffn_down-13.activation.f32" "$tensor_dir/ffn_down-13.output.f32"
)
for i in "${!tensor_paths[@]}"; do
  [[ -s "${tensor_paths[$i]}" && "$(sha256_of "${tensor_paths[$i]}")" == "${tensor_hashes[$i]}" ]] || die "missing or changed frozen tensor ${tensor_paths[$i]}"
done

umask 022
mkdir -p "$board_root/runs"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
run_dir=$board_root/runs/rm09-sysfs-fclk-$stamp
mkdir -m 0755 -- "$run_dir"
exec > >(tee -a "$run_dir/driver.log") 2>&1
restore_log=$run_dir/restore.log
rollback_unit=rm09-sysfs-fclk-$stamp-rollback
timer_armed=0
restore_ok=0

snapshot() {
  local label=$1
  echo "snapshot=$label utc=$(date -u +%FT%TZ)"
  echo "fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
  echo "fclk0_hz=$(cat "$fclk0" 2>/dev/null || echo UNKNOWN)"
  echo "board_temp_mC=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo UNKNOWN)"
  grep -E '^(MemAvailable|CmaTotal|CmaFree|SwapFree):' /proc/meminfo || true
  echo "loadavg=$(cat /proc/loadavg)"
}

is_starter_active() {
  xmutil listapps 2>&1 | awk -v app="$starter_app" '$1 == app && $NF ~ /^0,?$/ { found=1 } END { exit !found }'
}

finish() {
  local original_rc=$?
  local restore_rc=0
  trap - EXIT INT TERM
  set +e
  if [[ "$timer_armed" == 1 ]]; then
    echo "explicit_restore_begin_utc=$(date -u +%FT%TZ)"
    bash "$restore_script" "$restore_log"
    restore_rc=$?
    cat "$restore_log"
    local restored_rate
    restored_rate=$(cat "$fclk0" 2>/dev/null || echo UNKNOWN)
    if [[ "$restore_rc" -eq 0 ]] && is_starter_active &&
       [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] &&
       [[ "$restored_rate" != UNKNOWN ]] && (( restored_rate >= 99000000 && restored_rate <= 101000000 )); then
      restore_ok=1
      systemctl stop "$rollback_unit.timer" >/dev/null 2>&1
      systemctl stop "$rollback_unit.service" >/dev/null 2>&1
      systemctl reset-failed "$rollback_unit.timer" "$rollback_unit.service" >/dev/null 2>&1
    else
      restore_rc=1
    fi
    if [[ "$(sha256_of "$bit_file")" != "$bit_sha" || "$(sha256_of "$dtbo_file")" != "$dtbo_sha" || "$(sha256_of "$shell_file")" != "$shell_sha" ]]; then
      echo "frozen_original_rm07_package=FAIL"
      restore_rc=1
    else
      echo "frozen_original_rm07_package=PASS"
    fi
    snapshot after_restore
    echo "starter_kit_restore=$([[ "$restore_ok" == 1 ]] && echo PASS || echo FAIL) watchdog_timer_left_armed=$([[ "$restore_ok" == 1 ]] && echo 0 || echo 1)"
  fi
  if [[ "$original_rc" -eq 0 && "$restore_rc" -ne 0 ]]; then original_rc=1; fi
  echo "run_exit_status=$original_rc"
  exit "$original_rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "run_dir=$run_dir"
echo "host=$(hostname) utc=$(date -u +%FT%TZ) boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "app=$app requested_hz=$requested_hz route_ceiling_hz=$route_ceiling_hz tolerance_hz=$target_tolerance_hz"
echo "official_driver=$(readlink -f /sys/bus/platform/devices/fclk0/driver)"
echo "bit_sha256=$bit_sha dtbo_sha256=$dtbo_sha shell_json_sha256=$shell_sha runner_sha256=$runner_sha"
for i in "${!tensor_paths[@]}"; do echo "tensor_sha256 ${tensor_hashes[$i]} ${tensor_paths[$i]}"; done
snapshot before_rate_change
bash "$diagnostics_script" "$run_dir/clock-diagnostics-before-change"

# Arm and verify recovery before the first app or clock mutation.
if ! systemd-run --quiet --unit="$rollback_unit" --on-active="${rollback_seconds}s" \
    /bin/bash "$restore_script" "$restore_log"; then
  systemctl stop "$rollback_unit.timer" "$rollback_unit.service" >/dev/null 2>&1 || true
  systemctl reset-failed "$rollback_unit.timer" "$rollback_unit.service" >/dev/null 2>&1 || true
  die "could not create rollback timer"
fi
timer_armed=1
systemctl is-active --quiet "$rollback_unit.timer" || die "rollback timer did not become active"
echo "rollback_timer=$rollback_unit.timer restore_after_seconds=$rollback_seconds state=active"

xmutil unloadapp
for _ in $(seq 1 120); do
  if ! grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null; then break; fi
  sleep 0.5
done
! grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null || die "RM07 HLS UIO remained after starter-kit unload"
echo "clock_change_state=all_apps_unloaded"
echo "fclk0_before_request_hz=$(cat "$fclk0")"
printf '%s\n' "$requested_hz" >"$fclk0"
actual_hz=$(cat "$fclk0")
echo "fclk0_requested_hz=$requested_hz fclk0_readback_hz=$actual_hz"
[[ "$actual_hz" =~ ^[0-9]+$ ]] || die "FCLK0 readback is not numeric"
(( actual_hz <= route_ceiling_hz && actual_hz >= requested_hz-target_tolerance_hz && actual_hz <= requested_hz+target_tolerance_hz )) || die "fclk0 readback outside target band or route ceiling; no RM07 app/benchmark will run"
echo "fclk0_readback_gate=PASS"

echo "rm07_load_begin_utc=$(date -u +%FT%TZ)"
xmutil loadapp "$app"
ready=0
for _ in $(seq 1 120); do
  if [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] &&
     grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null &&
     xmutil listapps 2>&1 | awk -v app="$app" '$1 == app && $NF ~ /^0,?$/ { found=1 } END { exit !found }'; then
    ready=1
    break
  fi
  sleep 0.5
done
[[ "$ready" == 1 ]] || die "frozen RM07 app did not become ready"
loaded_hz=$(cat "$fclk0")
echo "rm07_load_end_utc=$(date -u +%FT%TZ) fclk0_after_load_hz=$loaded_hz"
[[ "$loaded_hz" =~ ^[0-9]+$ ]] || die "post-load FCLK0 readback is not numeric"
(( loaded_hz == actual_hz && loaded_hz <= route_ceiling_hz )) || die "FCLK0 changed during RM07 load"
snapshot rm07_loaded

check_apm_and_numeric() {
  local case_file=$1 expected_calls=$2 expected_n=$3 total_line apm_values
  [[ "$(grep -c '^APM_CLOCK_CAL ' "$case_file" || true)" == 1 ]] || die "expected one APM calibration in $case_file"
  total_line=$(grep '^TOTAL ' "$case_file" | tail -n 1)
  [[ -n "$total_line" ]] || die "TOTAL metrics missing from $case_file"
  grep -Fq "TOTAL calls=$expected_calls N=$expected_n " <<<"$total_line" || die "wrong TOTAL shape/call count in $case_file"
  apm_values=$(sed -n 's/.*measured_MHz=\([0-9.]*\).*/\1/p' "$case_file")
  awk -v measured="$apm_values" -v target="$requested_hz" -v tolerance="$target_tolerance_hz" -v route="$route_ceiling_hz" '
    BEGIN { rate=measured+0; target_mhz=target/1000000; tol=tolerance/1000000; route_mhz=route/1000000; upper=target_mhz+tol; if (upper>route_mhz) upper=route_mhz; if (rate<target_mhz-tol || rate>upper) exit 1; printf "apm_measured_mhz=%.3f target_mhz=%.6f route_ceiling_mhz=%.6f\n", rate,target_mhz,route_mhz }
  ' || die "APM rate outside target tolerance or routed ceiling in $case_file"
  local max_abs rmse cosine
  max_abs=$(sed -n 's/.* max_abs=\([^ ]*\).*/\1/p' <<<"$total_line")
  rmse=$(sed -n 's/.* RMSE=\([^ ]*\).*/\1/p' <<<"$total_line")
  cosine=$(sed -n 's/.* cosine=\([^ ]*\).*/\1/p' <<<"$total_line")
  awk -v a="$max_abs" -v r="$rmse" -v c="$cosine" 'BEGIN { if ((a+0)>1e-3 || (r+0)>1e-4 || (c+0)<0.999) exit 1; printf "numeric max_abs=%s RMSE=%s cosine=%s PASS\n",a,r,c }' || die "numeric comparison outside frozen RM08 tolerance in $case_file"
}

run_case() {
  local name=$1 layer=$2 n=$3 calls=$4 rc=0
  local output=$run_dir/$name.log
  echo "BEGIN_CASE name=$name layer=$layer N=$n calls=$calls utc=$(date -u +%FT%TZ)"
  timeout --signal=TERM --kill-after=5s "${case_timeout_seconds}s" \
    "$runner" "$tensor_dir/ffn_down-$layer.weight.f16" \
      "$tensor_dir/ffn_down-$layer.activation.f32" \
      "$tensor_dir/ffn_down-$layer.output.f32" "ffn_down-$layer" "$n" "$calls" \
      >"$output" 2>&1 || rc=$?
  cat "$output"
  echo "END_CASE name=$name rc=$rc utc=$(date -u +%FT%TZ)"
  [[ "$rc" -eq 0 ]] || die "$name ffn_down_bench returned $rc"
  check_apm_and_numeric "$output" "$calls" "$n"
  [[ "$(cat "$fclk0")" == "$actual_hz" ]] || die "FCLK0 changed during $name"
}

# The one real N1120 tensor gates whether the 135-call replay may proceed.
snapshot before_real_tensor
run_case real_n1120_1call 0 1120 1
run_case replay_n1120_35calls 0 1120 35
run_case replay_n280_100calls 13 280 100
snapshot after_replay
echo "135_call_replay=PASS N1120_calls=35 N280_calls=100 total_calls=135"
echo "sysfs_fclk_exact_probe=PASS requested_hz=$requested_hz actual_hz=$actual_hz run_dir=$run_dir"
