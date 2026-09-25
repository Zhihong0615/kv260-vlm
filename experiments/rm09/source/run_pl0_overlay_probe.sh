#!/usr/bin/env bash
set -Eeuo pipefail

# Guarded single-tensor and 135-call clock validation for the RM07 PL0 overlay.
# The experimental app is installed beside the frozen RM07 app; the frozen
# app directory and bitstream are read-only inputs and are never overwritten.

readonly base_app=kv260-rm07-bounded-k16
readonly variant_app=kv260-rm07-bounded-k16-pl0-187m5
readonly starter_app=k26-starter-kits
readonly board_root=/home/ubuntu/kv260-vlm-p2-cpu
readonly deploy=/tmp/rm08-deploy
readonly tensor_dir=$deploy/tensors
readonly runner=$deploy/ffn_down_bench
readonly staged_dtbo=/tmp/rm09-pl0-187m5.dtbo
readonly diagnostics_script=/tmp/rm09-clock-diagnostics.sh
readonly restore_script=/tmp/rm09-restore-starter-kit.sh
readonly diagnostics_sha_expected=3f77d1b8cc7ba0ecce195aacce5c6e9d125d38bb3e7d48eb937895ad74586058
readonly restore_sha_expected=ef428ea3e9215897310cfeaa5d79a4be320005ac8bbd6655c8505f2a9abe7e23
readonly variant_dtbo_sha=9cbb79e53f5610dfc5bffe431fbb1ea1b8fe572190d6d907059a38112c994010
readonly original_bin_sha=b8ba3e533b96e84f8cbb23acc8808146286671ccced979c9381f9afe9ddfbc60
readonly original_dtbo_sha=4fca210afb0258e7f67f6071a1d7d4c98681d60f847bfec5a3f00e0ab7c052d2
readonly shell_json_sha=802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344
readonly runner_sha=c687a693d20a95c81787754aa07b49f51e3cf868116f8652aa22f6d4f30ac914
readonly weight_sha=b2e5111fdd29185654baf47e5437e322ec9433ec58f75921b2a82e2bb2117676
readonly activation_sha=80dfa4a1d48dfa3519ae173eb551bdd22822f075e25d0a5373ace96b6cb12305
readonly output_sha=cabb0c46016184dc66a44177fdc9c209816c864db975fce9b1f064ca5da6c9fe
readonly target_hz=187498123
readonly route_ceiling_hz=187512000
readonly target_tolerance_hz=1000000
readonly rollback_seconds=1800
readonly case_timeout_seconds=300

die() { echo "ERROR: $*" >&2; exit 1; }
sha256_of() { sha256sum "$1" | awk '{print $1}'; }

if [[ "$(id -u)" -ne 0 || "$#" -ne 0 ]]; then
  echo "Usage: sudo bash $0" >&2
  exit 2
fi

readonly original_dir=/lib/firmware/xilinx/$base_app
readonly variant_dir=/lib/firmware/xilinx/$variant_app
readonly original_bin=$original_dir/$base_app.bit.bin
readonly original_dtbo=$original_dir/$base_app.dtbo
readonly original_json=$original_dir/shell.json
readonly variant_dtbo=$variant_dir/$variant_app.dtbo
readonly variant_app_bin=$variant_dir/$variant_app.bit.bin
readonly variant_bin=$variant_dir/$base_app.bit.bin
readonly variant_json=$variant_dir/shell.json
readonly fclk0=/sys/bus/platform/devices/fclk0/set_rate

for helper in "$diagnostics_script:$diagnostics_sha_expected" "$restore_script:$restore_sha_expected"; do
  path=${helper%%:*}
  expected=${helper##*:}
  [[ -r "$path" && "$(sha256_of "$path")" == "$expected" ]] || die "missing or changed board helper $path"
done
for path in "$staged_dtbo" "$original_bin" "$original_dtbo" "$original_json" "$runner" "$fclk0"; do
  [[ -r "$path" ]] || die "missing required path $path"
done
[[ -x "$runner" && -w "$fclk0" ]] || die "runner or fclk0 access check failed"
[[ "$(sha256_of "$staged_dtbo")" == "$variant_dtbo_sha" ]] || die "staged variant DTBO SHA mismatch"
[[ "$(sha256_of "$original_bin")" == "$original_bin_sha" ]] || die "frozen RM07 .bit.bin SHA mismatch"
[[ "$(sha256_of "$original_dtbo")" == "$original_dtbo_sha" ]] || die "frozen RM07 .dtbo SHA mismatch"
[[ "$(sha256_of "$original_json")" == "$shell_json_sha" ]] || die "frozen RM07 shell.json SHA mismatch"
[[ "$(sha256_of "$runner")" == "$runner_sha" ]] || die "ffn_down_bench SHA mismatch"
for spec in \
  "$tensor_dir/ffn_down-0.weight.f16:$weight_sha" \
  "$tensor_dir/ffn_down-0.activation.f32:$activation_sha" \
  "$tensor_dir/ffn_down-0.output.f32:$output_sha"; do
  path=${spec%%:*}
  expected=${spec##*:}
  [[ -s "$path" && "$(sha256_of "$path")" == "$expected" ]] || die "missing or changed real tensor $path"
done

[[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] || die "FPGA manager is not operating"
xmutil listapps 2>&1 | awk -v app="$starter_app" '$1 == app && $NF ~ /^0,?$/ { found=1 } END { exit !found }' || die "starter-kit must be active at entry"
[[ "$(cat "$fclk0")" == 99999999 ]] || die "expected the measured safe 100MHz FCLK0 state at entry"
[[ -z "$(pgrep -x llama-mtmd-cli || true)" ]] || die "a VLM CLI is active"
! grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null || die "RM07 HLS UIO unexpectedly active at entry"

umask 022
mkdir -p "$board_root/runs"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
run_dir=$board_root/runs/rm09-pl0-overlay-$stamp
mkdir -m 0755 -- "$run_dir"
exec > >(tee -a "$run_dir/driver.log") 2>&1
restore_log=$run_dir/restore.log
rollback_unit=rm09-pl0-overlay-$stamp-rollback
timer_armed=0
restore_ok=0

snapshot() {
  local label=$1
  echo "snapshot=$label utc=$(date -u +%FT%TZ)"
  echo "fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
  echo "fclk0_hz=$(cat "$fclk0" 2>/dev/null || echo UNKNOWN)"
  echo "cpu0_scaling_cur_freq_kHz=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo UNKNOWN)"
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
    if [[ "$restore_rc" -eq 0 ]] && is_starter_active &&
       [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null)" == operating ]]; then
      local restored_rate
      restored_rate=$(cat "$fclk0" 2>/dev/null || echo UNKNOWN)
      if [[ "$restored_rate" != UNKNOWN ]] && (( restored_rate >= 99000000 && restored_rate <= 101000000 )); then
        restore_ok=1
        systemctl stop "$rollback_unit.timer" >/dev/null 2>&1
        systemctl stop "$rollback_unit.service" >/dev/null 2>&1
        systemctl reset-failed "$rollback_unit.timer" "$rollback_unit.service" >/dev/null 2>&1
      else
        restore_rc=1
      fi
    fi
    if [[ "$(sha256_of "$original_bin")" != "$original_bin_sha" ||
          "$(sha256_of "$original_dtbo")" != "$original_dtbo_sha" ||
          "$(sha256_of "$original_json")" != "$shell_json_sha" ]]; then
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
echo "base_app=$base_app variant_app=$variant_app"
echo "original_bit_bin=$original_bin sha256=$original_bin_sha"
echo "original_dtbo=$original_dtbo sha256=$original_dtbo_sha"
echo "variant_dtbo_source=$staged_dtbo sha256=$variant_dtbo_sha"
echo "firmware_name=$base_app.bit.bin variant_bit_bin_target=$variant_bin"
echo "shell_json_sha256=$shell_json_sha runner_sha256=$runner_sha"
echo "target_hz=$target_hz route_ceiling_hz=$route_ceiling_hz target_tolerance_hz=$target_tolerance_hz"
snapshot before_variant_stage
bash "$diagnostics_script" "$run_dir/clock-diagnostics-before-load"

# Add a separate app package. firmware-name in the new DTBO stays at the
# frozen bitstream basename, so the variant app directory has a symlink to
# the exact installed original payload. The original app package is untouched.
install -d -m 0755 "$variant_dir"
install -m 0644 "$staged_dtbo" "$variant_dtbo"
install -m 0644 "$original_json" "$variant_json"
ln -sfn "$original_bin" "$variant_bin"
ln -sfn "$original_bin" "$variant_app_bin"
[[ "$(sha256_of "$variant_dtbo")" == "$variant_dtbo_sha" ]] || die "installed variant DTBO SHA mismatch"
[[ "$(sha256_of "$variant_json")" == "$shell_json_sha" ]] || die "installed variant shell.json SHA mismatch"
[[ "$(readlink -f "$variant_bin")" == "$(readlink -f "$original_bin")" ]] || die "variant bitstream link does not resolve to frozen base payload"
[[ "$(readlink -f "$variant_app_bin")" == "$(readlink -f "$original_bin")" ]] || die "variant app bitstream link does not resolve to frozen base payload"
[[ "$(sha256_of "$variant_bin")" == "$original_bin_sha" ]] || die "variant bitstream payload SHA mismatch"
[[ "$(sha256_of "$variant_app_bin")" == "$original_bin_sha" ]] || die "variant app bitstream payload SHA mismatch"
printf '%s\n' "firmware-name=$base_app.bit.bin" "variant_dtbo=$variant_dtbo" "variant_shell_json=$variant_json" "variant_bit_bin=$(readlink -f "$variant_bin")" "variant_app_bit_bin=$(readlink -f "$variant_app_bin")"
xmutil listapps 2>&1 | tee "$run_dir/apps-before-load.txt"
grep -Fq "$variant_app" "$run_dir/apps-before-load.txt" || die "xmutil does not list the separate overlay app"

# Rollback is armed before unloading the starter-kit or loading the variant.
systemd-run --quiet --unit="$rollback_unit" --on-active="${rollback_seconds}s" \
  /bin/bash "$restore_script" "$restore_log"
timer_armed=1
echo "rollback_timer=$rollback_unit.timer restore_after_seconds=$rollback_seconds"

xmutil unloadapp
for _ in $(seq 1 120); do
  if ! grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null; then break; fi
  sleep 0.5
done
! grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null || die "RM07 HLS UIO remained after starter-kit unload"

echo "variant_load_begin_utc=$(date -u +%FT%TZ)"
xmutil loadapp "$variant_app"
ready=0
for _ in $(seq 1 120); do
  if [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] &&
     grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null &&
     xmutil listapps 2>&1 | awk -v app="$variant_app" '$1 == app && $NF ~ /^0,?$/ { found=1 } END { exit !found }'; then
    ready=1
    break
  fi
  sleep 0.5
done
[[ "$ready" == 1 ]] || die "variant app did not become ready"
actual_hz=$(cat "$fclk0")
echo "variant_load_end_utc=$(date -u +%FT%TZ) fclk0_readback_hz=$actual_hz"
(( actual_hz <= route_ceiling_hz && actual_hz >= target_hz-target_tolerance_hz && actual_hz <= target_hz+target_tolerance_hz )) || die "actual FCLK0 readback is not within 1MHz of assigned rate or exceeds route ceiling"
snapshot variant_loaded
bash "$diagnostics_script" "$run_dir/clock-diagnostics-variant-loaded"

check_apm_and_numeric() {
  local case_file=$1 expected_calls=$2 expected_n=$3
  local apm_count total_line apm_values
  apm_count=$(grep -c '^APM_CLOCK_CAL ' "$case_file" || true)
  [[ "$apm_count" == 1 ]] || die "expected one APM calibration in $case_file, found $apm_count"
  total_line=$(grep '^TOTAL ' "$case_file" | tail -n 1)
  [[ -n "$total_line" ]] || die "TOTAL metrics missing from $case_file"
  grep -Fq "TOTAL calls=$expected_calls N=$expected_n " <<<"$total_line" || die "wrong TOTAL shape/call count in $case_file"
  apm_values=$(sed -n 's/.*measured_MHz=\([0-9.]*\).*/\1/p' "$case_file")
  awk -v measured="$apm_values" -v target="$target_hz" -v tolerance="$target_tolerance_hz" -v route="$route_ceiling_hz" '
    BEGIN {
      rate=measured+0
      target_mhz=target/1000000
      tolerance_mhz=tolerance/1000000
      route_mhz=route/1000000
      upper=target_mhz+tolerance_mhz
      if (upper>route_mhz) upper=route_mhz
      if (rate<target_mhz-tolerance_mhz || rate>upper) exit 1
      printf "apm_measured_mhz=%.3f target_mhz=%.6f route_ceiling_mhz=%.6f\n", rate, target_mhz, route_mhz
    }
  ' || die "APM measured rate outside target tolerance or route ceiling in $case_file"
  local max_abs rmse cosine
  max_abs=$(sed -n 's/.* max_abs=\([^ ]*\).*/\1/p' <<<"$total_line")
  rmse=$(sed -n 's/.* RMSE=\([^ ]*\).*/\1/p' <<<"$total_line")
  cosine=$(sed -n 's/.* cosine=\([^ ]*\).*/\1/p' <<<"$total_line")
  awk -v a="$max_abs" -v r="$rmse" -v c="$cosine" 'BEGIN { if ((a+0)>1e-3 || (r+0)>1e-4 || (c+0)<0.999) exit 1; printf "numeric max_abs=%s RMSE=%s cosine=%s PASS\n", a, r, c }' || die "numeric comparison outside RM08 tolerance in $case_file"
}

run_case() {
  local name=$1 layer=$2 n=$3 calls=$4
  local output=$run_dir/$name.log
  echo "BEGIN_CASE name=$name layer=$layer N=$n calls=$calls utc=$(date -u +%FT%TZ)"
  local rc=0
  timeout --signal=TERM --kill-after=5s "${case_timeout_seconds}s" \
    "$runner" "$tensor_dir/ffn_down-$layer.weight.f16" \
      "$tensor_dir/ffn_down-$layer.activation.f32" \
      "$tensor_dir/ffn_down-$layer.output.f32" "ffn_down-$layer" "$n" "$calls" \
      >"$output" 2>&1 || rc=$?
  cat "$output"
  echo "END_CASE name=$name rc=$rc utc=$(date -u +%FT%TZ)"
  [[ "$rc" -eq 0 ]] || die "$name ffn_down_bench returned $rc"
  check_apm_and_numeric "$output" "$calls" "$n"
}

# One real N1120 tensor must pass both direct XRT numeric comparison and APM
# rate checks before the longer shape-weighted replay can begin.
snapshot before_real_tensor
run_case real_n1120_1call 0 1120 1
run_case replay_n1120_35calls 0 1120 35
run_case replay_n280_100calls 13 280 100
snapshot after_clock_validation
echo "135_call_replay=PASS N1120_calls=35 N280_calls=100 total_calls=135"
echo "clock_overlay_probe=PASS variant_app=$variant_app evidence_dir=$run_dir"
