#!/usr/bin/env bash
set -euo pipefail

readonly base_app=k26-starter-kits
readonly app=kv260-rm09-static-extent
readonly deploy_dir=/tmp/rm09-static-extent
readonly package_source=$deploy_dir/package/$app
readonly board_root=/home/ubuntu/kv260-vlm-p2-cpu
readonly install_dir=/lib/firmware/xilinx/$app
readonly runtime_id=22d96ed06be3
readonly runtime_root=$board_root/rm09-static-extent-build-$runtime_id
readonly runtime_manifest=$runtime_root/RM09_RUNTIME_ARTIFACTS.sha256
readonly cli=$runtime_root/bin/llama-mtmd-cli
readonly cpu_lib=$runtime_root/bin/libggml-cpu.so.0.24.0
readonly cpu_lib_link=$runtime_root/bin/libggml-cpu.so.0
readonly model=$board_root/input/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf
readonly mmproj=$board_root/input/mmproj-MiniCPM-V-4.6-f16.gguf
readonly helper=$runtime_root/bin/rm08-ffn-down-helper-smoke
readonly identity_source=$deploy_dir/boardprep/axilite_probe.c
readonly tensor_dir=/tmp/rm08-deploy/tensors
readonly diagnostics_script=$deploy_dir/boardprep/collect_clock_diagnostics.sh
readonly restore_script=$deploy_dir/boardprep/restore_starter_kit.sh
readonly cpu_pair_lock=/tmp/rm09-f16x/cpu-pair-active
readonly diagnostics_sha_expected=3f77d1b8cc7ba0ecce195aacce5c6e9d125d38bb3e7d48eb937895ad74586058
readonly restore_sha_expected=ef428ea3e9215897310cfeaa5d79a4be320005ac8bbd6655c8505f2a9abe7e23
readonly package_manifest_sha=cae3a750941c191ba17f1c9cbfacaa5a5093ecc41eaa9a99f1ba1f00a0134a66
readonly app_bin_sha=819b088199ac4346c1eb9b7bb65ade42afe8f95eaeec02cca4bc6bdd2bb0d87b
readonly app_dtbo_sha=85fd0a2e2186886d8d52178c0934ba51585c37c28e5dd54a1c5536f2e506521e
readonly app_json_sha=802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344
readonly runtime_manifest_sha=__RM09_RUNTIME_ARTIFACTS_SHA256__
readonly cli_sha=__RM09_RUNTIME_CLI_SHA256__
readonly model_sha=8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773
readonly mmproj_sha=ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293
readonly cpu_lib_sha=__RM09_RUNTIME_CPU_LIBRARY_SHA256__
readonly helper_sha=__RM09_RUNTIME_HELPER_SHA256__
readonly route_ceiling_hz=100000000
# Rounded XRT BOs: W=1,101,824; X=552,960; Y=16,384 bytes.
readonly rm09_bounded_pool_bytes=1671168
readonly cma_margin_kb=8192
readonly cma_minimum_kb=$(((rm09_bounded_pool_bytes + 1023) / 1024 + cma_margin_kb))
readonly cli_timeout_seconds=1800
readonly rollback_seconds=4200
die() { echo "ERROR: $*" >&2; exit 1; }
sha256_of() { sha256sum "$1" | awk '{print $1}'; }

if [[ "$(id -u)" -ne 0 || "$#" -ne 0 ]]; then
  echo "Usage: sudo bash $0" >&2
  exit 2
fi
for digest_name in runtime_manifest_sha cli_sha cpu_lib_sha helper_sha; do
  digest="${!digest_name}"
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]] || die "$digest_name has not been filled with its final SHA-256"
done
for script_and_sha in "$diagnostics_script:$diagnostics_sha_expected" "$restore_script:$restore_sha_expected"; do
  path="${script_and_sha%%:*}"
  expected="${script_and_sha##*:}"
  [[ -r "$path" && "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || {
    echo "Missing or changed board helper script: $path" >&2
    exit 2
  }
done
[[ -x "$cli" && -x "$helper" && -x /usr/bin/time && -x "$(command -v timeout)" ]]
[[ -r "$runtime_manifest" && "$(sha256_of "$runtime_manifest")" == "$runtime_manifest_sha" ]] || die "runtime artifact manifest missing or changed"
(cd "$runtime_root" && sha256sum -c RM09_RUNTIME_ARTIFACTS.sha256) || die "runtime artifact checksum failed"
if [[ -e "$cpu_pair_lock" ]]; then
  echo "ERROR: RM09 CPU-only P0/P1 pair is active; refusing an overlapping PL app load" >&2
  exit 1
fi
[[ "$(sha256_of "$cli")" == "$cli_sha" ]]
[[ "$(sha256sum "$model" | awk '{print $1}')" == "$model_sha" ]]
[[ "$(sha256sum "$mmproj" | awk '{print $1}')" == "$mmproj_sha" ]]
[[ -r "$cpu_lib" && "$(readlink -f "$cpu_lib_link")" == "$cpu_lib" ]]
[[ "$(sha256_of "$cpu_lib")" == "$cpu_lib_sha" ]]
[[ "$(sha256_of "$helper")" == "$helper_sha" ]]
LD_LIBRARY_PATH="$runtime_root/bin" ldd "$cli" | awk -v library="$cpu_lib_link" '$1 == "libggml-cpu.so.0" && $3 == library { found=1 } END { exit !found }' || die "llama-mtmd-cli does not resolve the RM09 CPU library"
LD_LIBRARY_PATH="$runtime_root/bin" ldd "$helper" | awk -v library="$cpu_lib_link" '$1 == "libggml-cpu.so.0" && $3 == library { found=1 } END { exit !found }' || die "real-tensor helper does not resolve the RM09 CPU library"
export LD_LIBRARY_PATH="$runtime_root/bin${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
for layer in 0 13 26; do
  for suffix in weight.f16 activation.f32 output.f32; do
    [[ -s "$tensor_dir/ffn_down-$layer.$suffix" ]]
  done
done
[[ -r "$identity_source" ]] || die "RM09 AXI-Lite identity probe source is missing"
[[ -r "$package_source/SHA256SUMS" && "$(sha256_of "$package_source/SHA256SUMS")" == "$package_manifest_sha" ]] || die "RM09 route package manifest missing or changed"
(cd "$package_source" && sha256sum -c SHA256SUMS) || die "RM09 route package manifest validation failed"
for item in "$app_bin_sha $package_source/$app.bit.bin" "$app_dtbo_sha $package_source/$app.dtbo" "$app_json_sha $package_source/shell.json"; do
  read -r expected file <<<"$item"
  [[ -s "$file" && "$(sha256_of "$file")" == "$expected" ]] || die "RM09 route package artifact missing or changed: $file"
done

is_starter_active() {
  xmutil listapps 2>&1 | awk '$1 == "k26-starter-kits" && $NF ~ /^0,?$/ { found=1 } END { exit !found }'
}
is_rm09_active() {
  xmutil listapps 2>&1 | awk -v app="$app" '$1 == app && $NF ~ /^0,?$/ { found=1 } END { exit !found }'
}
snapshot() {
  local label="$1"
  echo "snapshot=$label utc=$(date -u +%FT%TZ)"
  grep -E '^(MemAvailable|CmaTotal|CmaFree|SwapFree):' /proc/meminfo || true
  echo "loadavg=$(cat /proc/loadavg)"
  echo "cpu0_scaling_cur_freq_kHz=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo UNKNOWN)"
  echo "fclk0=$(cat /sys/bus/platform/devices/fclk0/set_rate 2>/dev/null || echo UNKNOWN)"
  echo "fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
}
require_cma_for_dma() {
  local stage="$1" free_kb
  free_kb="$(awk '$1 == "CmaFree:" { print $2 }' /proc/meminfo)"
  [[ "$free_kb" =~ ^[0-9]+$ ]] || die "$stage could not read CmaFree"
  echo "stage=$stage CmaFree_kB=$free_kb bounded_XRT_pool_bytes=$rm09_bounded_pool_bytes cma_margin_kB=$cma_margin_kb dma_minimum_kB=$cma_minimum_kb"
  (( free_kb >= cma_minimum_kb )) || die "$stage has less than the 1.6 MiB bounded XRT pool plus 8 MiB CMA margin"
}
[[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] || die "FPGA manager is not operating"
is_starter_active || die "starter-kit must be active at entry"
[[ "$(cat /sys/bus/platform/devices/fclk0/set_rate)" == 99999999 ]] || die "FCLK0 must be at the measured 100MHz readback"
[[ -z "$(pgrep -x llama-mtmd-cli || true)" ]] || die "another llama-mtmd-cli is active"
if [[ -e "$install_dir" ]]; then
  for item in "$app_bin_sha $install_dir/$app.bit.bin" "$app_dtbo_sha $install_dir/$app.dtbo" "$app_json_sha $install_dir/shell.json"; do
    read -r expected file <<<"$item"
    [[ -s "$file" && "$(sha256_of "$file")" == "$expected" ]] || die "existing app install differs from the pinned RM09 package: $file"
  done
  package_preinstalled=1
else
  package_preinstalled=0
fi

umask 022
mkdir -p "$board_root/runs"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_dir="$board_root/runs/rm09-pl-q38299-q35419-$stamp"
mkdir -m 0755 -- "$run_dir"
exec > >(tee -a "$run_dir/driver.log") 2>&1

echo "run_dir=$run_dir"
echo "host=$(hostname) utc=$(date -u +%FT%TZ) boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "runtime=$cli cli_sha256=$cli_sha model_sha256=$model_sha mmproj_sha256=$mmproj_sha"
echo "runtime_cpu_library=$cpu_lib runtime_cpu_library_sha256=$cpu_lib_sha ldd_resolution=$(LD_LIBRARY_PATH="$runtime_root/bin" ldd "$cli" | awk '$1 == "libggml-cpu.so.0" { print $0 }')"
echo "rm09_bit_bin_sha256=$app_bin_sha dtbo_sha256=$app_dtbo_sha package_manifest_sha256=$package_manifest_sha route_clock_ceiling_hz=$route_ceiling_hz"
echo "runtime_manifest_sha256=$runtime_manifest_sha helper_sha256=$helper_sha"
snapshot before_clock_diagnostics
bash "$diagnostics_script" "$run_dir/clock-diagnostics-before-load"
snapshot after_clock_diagnostics
require_cma_for_dma before_rm09_load

restore_log="$run_dir/restore.log"
rollback_unit="rm09-static-extent-$stamp-rollback"
restore_ok=0
timer_armed=0
package_installed_by_script=0
finish() {
  local original_rc=$?
  local restore_rc=0
  trap - EXIT INT TERM
  set +e
  if [[ "$timer_armed" == 1 ]]; then
    echo "explicit_restore_begin utc=$(date -u +%FT%TZ)"
    bash "$restore_script" "$restore_log"
    restore_rc=$?
    if (( restore_rc == 0 )); then
      restore_ok=1
      if [[ "$package_installed_by_script" == 1 ]]; then
        if rm -f -- "$install_dir/$app.bit.bin" "$install_dir/$app.dtbo" "$install_dir/shell.json" &&
           rmdir -- "$install_dir"; then
          package_installed_by_script=0
          echo "rm09_package_cleanup=PASS"
        else
          restore_rc=1
          echo "rm09_package_cleanup=FAIL"
        fi
      fi
      systemctl stop "$rollback_unit.timer" >/dev/null 2>&1
      systemctl stop "$rollback_unit.service" >/dev/null 2>&1
      systemctl reset-failed "$rollback_unit.timer" "$rollback_unit.service" >/dev/null 2>&1
      echo "starter_kit_restore=PASS"
    else
      echo "starter_kit_restore=FAIL watchdog_timer_left_armed=1"
    fi
    snapshot after_restore
    echo "explicit_restore_end utc=$(date -u +%FT%TZ)"
  fi
  if [[ "$original_rc" -eq 0 && "$restore_rc" -ne 0 ]]; then original_rc=1; fi
  echo "run_exit_status=$original_rc starter_kit_restore=$([[ "$restore_ok" == 1 ]] && echo PASS || echo NOT_CONFIRMED)"
  exit "$original_rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

systemd-run --quiet --unit="$rollback_unit" --on-active="${rollback_seconds}s" "$restore_script" "$restore_log"
timer_armed=1
echo "rollback_timer=$rollback_unit.timer restore_after_seconds=$rollback_seconds"
if [[ "$package_preinstalled" == 0 ]]; then
  install -d -m 0755 -- "$install_dir"
  install -m 0644 -- "$package_source/$app.bit.bin" "$install_dir/$app.bit.bin"
  install -m 0644 -- "$package_source/$app.dtbo" "$install_dir/$app.dtbo"
  install -m 0644 -- "$package_source/shell.json" "$install_dir/shell.json"
  package_installed_by_script=1
fi
snapshot before_app_unload
xmutil unloadapp
for _ in $(seq 1 120); do
  if ! grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null; then break; fi
  sleep 0.5
done
! grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null || die "old HLS UIO remains after unload"

xmutil loadapp "$app"
ready=0
for _ in $(seq 1 120); do
  if [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] &&
     grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null &&
     grep -q '^axi_perf_mon_0$' /sys/class/uio/uio*/name 2>/dev/null && is_rm09_active; then
    ready=1
    break
  fi
  sleep 0.5
done
[[ "$ready" == 1 ]] || die "RM09 HLS/APM UIOs did not become ready"
snapshot rm09_loaded
active_fclk0_hz="$(cat /sys/bus/platform/devices/fclk0/set_rate)"
echo "active_fclk0_hz=$active_fclk0_hz"
(( active_fclk0_hz >= 99000000 && active_fclk0_hz <= 101000000 && active_fclk0_hz <= route_ceiling_hz )) || die "RM09 PL0 readback exceeds the routed 100MHz clock"
echo "hls_uio_name=$(grep -h '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name | head -n1)"
echo "apm_uio_name=$(grep -h '^axi_perf_mon_0$' /sys/class/uio/uio*/name | head -n1)"
gcc -O2 -Wall -Wextra -Werror "$identity_source" -o "$run_dir/rm09-axilite-identity-probe" || die "could not build RM09 AXI-Lite identity probe"
"$run_dir/rm09-axilite-identity-probe" | tee "$run_dir/axilite-identity-probe.log" || die "RM09 AXI-Lite identity/invalid-task probe failed"
grep -Fq 'AXI_LITE_ABI_PROBE=0xfffffffc (-4) expected=-4 PASS' "$run_dir/axilite-identity-probe.log" || die "RM09 invalid-task result did not return -4"
echo "rm09_hls_identity_probe=PASS compatible=xlnx,vision-ffn-down-tile-1.0 axi_control=0xa0010000 size=0x10000 invalid_task_return=-4"

run_helper() {
  local stem="$1"
  local trace="$run_dir/$stem-helper-trace.txt"
  local logfile="$run_dir/$stem-helper.log"
  require_cma_for_dma "$stem-before-real-tensor-DMA"
  : >"$trace"
  env RM08_FFN_DOWN_PL=1 RM08_PL_EXPECTED_MEDIA_GROUPS=0 RM08_PL_TRACE="$trace" \
    "$helper" "$tensor_dir" >"$logfile" 2>&1 || die "$stem real-tensor helper failed"
  cat "$logfile"
  for expected in \
    'SMOKE_RESULT layer=ffn_down-0 status=PASS K=4304 M=1152 N=1120 ' \
    'SMOKE_RESULT layer=ffn_down-13 status=PASS K=4304 M=1152 N=280 ' \
    'SMOKE_RESULT layer=ffn_down-26 status=PASS K=4304 M=1152 N=280 '; do
    grep -Fq "$expected" "$logfile" || die "$stem missing real-tensor check: $expected"
  done
  [[ "$(grep -c '^RM08_PL_CALL .*status=PL ' "$trace" || true)" -eq 3 ]] || die "$stem helper did not record three PL calls"
  [[ "$(grep -c '^RM08_PL_CALL .*status=CPU_FALLBACK ' "$trace" || true)" -eq 0 ]] || die "$stem helper has a CPU fallback"
  grep -Fq 'RM08_PL_CALL layer=ffn_down-0 status=PL K=4304 M=1152 N=1120 ' "$trace" || die "$stem helper missing N1120 PL check"
  grep -Fq 'RM08_PL_CALL layer=ffn_down-13 status=PL K=4304 M=1152 N=280 ' "$trace" || die "$stem helper missing layer 13 PL check"
  grep -Fq 'RM08_PL_CALL layer=ffn_down-26 status=PL K=4304 M=1152 N=280 ' "$trace" || die "$stem helper missing layer 26 PL check"
  echo "$stem real_tensor_helper=PASS trace=$trace log=$logfile"
}

run_request() {
  local qid="$1" groups="$2" image_id="$3" image_sha="$4" answer_expected="$5" prompt="$6"
  local stem="q$qid"
  local image="$board_root/input/textvqa-dev50/$image_id.jpg"
  local trace="$run_dir/$stem-pl-trace.txt"
  local time_log="$run_dir/$stem-time-v.txt"
  local stdout_log="$run_dir/$stem-stdout.log"
  local stderr_log="$run_dir/$stem-stderr.log"
  [[ -r "$image" ]] || die "$stem frozen image missing"
  [[ "$(sha256sum "$image" | awk '{print $1}')" == "$image_sha" ]] || die "$stem frozen image hash mismatch"
  run_helper "$stem"
  snapshot "$stem-before-request"
  local expected_calls=$((27 * groups))
  local expected_total_calls=$((29 * groups))
  local expected_n1120=0 expected_n280=0
  local expected_n960=0 expected_n1008=0 expected_n1024=0 expected_n1056=0
  local expected_n240=0 expected_n252=0 expected_n256=0 expected_n264=0
  local expected_vit_n252=0 expected_vit_n256=0 expected_vit_n264=0
  local expected_mm_n63=0 expected_mm_n64=0 expected_mm_n66=0
  case "$qid" in
    38299)
      expected_n1024=14 expected_n1056=7 expected_n256=40 expected_n264=20
      expected_vit_n256=2 expected_vit_n264=1 expected_mm_n64=2 expected_mm_n66=1
      ;;
    35419)
      expected_n1008=49 expected_n252=140
      expected_vit_n252=7 expected_mm_n63=7
      ;;
    *) die "$stem has no frozen RM09 extent expectation" ;;
  esac
  local expected_fallbacks=$((2 * groups))
  echo "request=$stem media_groups=$groups expected_PL_calls=27x$groups=$expected_calls expected_total_calls=$expected_total_calls expected_N1120=$expected_n1120 expected_N280=$expected_n280 expected_fallbacks=$expected_fallbacks threads=4 batch_threads=4"
  echo "image_id=$image_id image_sha256=$image_sha expected_answer=$(printf '%q' "$answer_expected")"
  echo "frozen_prompt=$(printf '%q' "$prompt")"
  echo "cli_args=-m $model --mmproj $mmproj --image $image -p <frozen-prompt> -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4"
  : >"$trace"
  export RM08_FFN_DOWN_PL=1
  export RM08_PL_EXPECTED_MEDIA_GROUPS="$groups"
  export RM08_PL_TRACE="$trace"
  export RM09_PL_EXPECTED_QID="$qid"
  export LD_LIBRARY_PATH="$runtime_root/bin${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  require_cma_for_dma "$stem-before-VLM-DMA"
  local request_rc=0
  echo "$stem request_begin_utc=$(date -u +%FT%TZ)"
  /usr/bin/time -v -o "$time_log" \
    "$(command -v timeout)" --signal=TERM --kill-after=10s "${cli_timeout_seconds}s" \
    "$cli" -m "$model" --mmproj "$mmproj" --image "$image" -p "$prompt" \
    -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 \
    --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4 \
    </dev/null >"$stdout_log" 2>"$stderr_log" || request_rc=$?
  echo "$stem request_end_utc=$(date -u +%FT%TZ) request_exit_code=$request_rc"
  snapshot "$stem-after-request"
  [[ -s "$time_log" && -s "$stdout_log" ]] || die "$stem missing time/stdout evidence"
  local answer
  answer="$(awk 'NF { sub(/\r$/, ""); last=$0 } END { print last }' "$stdout_log")"
  echo "$stem answer=$(printf '%q' "$answer") expected=$(printf '%q' "$answer_expected")"
  [[ "$request_rc" -eq 0 && "$answer" == "$answer_expected" ]] || die "$stem request status/answer mismatch"

  local summary
  summary="$(grep '^RM08_PL_SUMMARY ' "$trace" | tail -n1 || true)"
  [[ -n "$summary" ]] || die "$stem RM08_PL_SUMMARY missing"
  value() { sed -n "s/.*\<$1=\([^ ]*\).*/\1/p" <<<"$summary"; }
  for check in \
    "expected_calls:$expected_calls" "expected_total_calls:$expected_total_calls" \
    "actual_calls:$expected_total_calls" "expected_PL:$expected_calls" "actual_PL:$expected_calls" \
    "cpu_fallbacks:$expected_fallbacks" "expected_N1120:$expected_n1120" "actual_N1120:$expected_n1120" \
    "expected_N280:$expected_n280" "actual_N280:$expected_n280" \
    "expected_merger_cpu:$expected_fallbacks" "merger_cpu:$expected_fallbacks" \
    "expected_vit_merger_cpu:$groups" "vit_merger_cpu:$groups" \
    "expected_mm_down_cpu:$groups" "mm_down_cpu:$groups" \
    "matches_expected:1" "media_groups:$groups"; do
    local key="${check%%:*}" expected="${check#*:}" actual
    actual="$(value "$key")"
    echo "$stem trace_check=$key actual=${actual:-MISSING} expected=$expected"
    [[ "$actual" == "$expected" ]] || die "$stem PL summary mismatch: $key"
  done
  [[ "$(value expectation_enabled)" == 1 ]] || die "$stem dispatch expectation not enabled"

  local extent_summary
  extent_summary="$(grep '^RM09_PL_EXTENTS ' "$trace" | tail -n1 || true)"
  [[ -n "$extent_summary" ]] || die "$stem RM09_PL_EXTENTS missing"
  extent_value() { sed -n "s/.*\\<$1=\\([^ ]*\\).*/\\1/p" <<<"$extent_summary"; }
  for check in \
    "qid:$qid" "expectation_enabled:1" "expected_groups:$groups" "actual_groups:$groups" \
    "expected_N960:$expected_n960" "actual_N960:$expected_n960" \
    "expected_N1008:$expected_n1008" "actual_N1008:$expected_n1008" \
    "expected_N1024:$expected_n1024" "actual_N1024:$expected_n1024" \
    "expected_N1056:$expected_n1056" "actual_N1056:$expected_n1056" \
    "expected_N1120:0" "actual_N1120:0" \
    "expected_N240:$expected_n240" "actual_N240:$expected_n240" \
    "expected_N252:$expected_n252" "actual_N252:$expected_n252" \
    "expected_N256:$expected_n256" "actual_N256:$expected_n256" \
    "expected_N264:$expected_n264" "actual_N264:$expected_n264" \
    "expected_N280:0" "actual_N280:0" "matches_expected:1"; do
    local key="${check%%:*}" expected="${check#*:}" actual
    actual="$(extent_value "$key")"
    echo "$stem extent_check=$key actual=${actual:-MISSING} expected=$expected"
    [[ "$actual" == "$expected" ]] || die "$stem PL extent histogram mismatch: $key"
  done

  awk -v total="$expected_total_calls" -v pl_expected="$expected_calls" \
      -v n1008_expected="$expected_n1008" -v n1024_expected="$expected_n1024" \
      -v n1056_expected="$expected_n1056" -v n252_expected="$expected_n252" \
      -v n256_expected="$expected_n256" -v n264_expected="$expected_n264" \
      -v fallback_expected="$expected_fallbacks" -v groups="$groups" \
      -v vit252_expected="$expected_vit_n252" -v vit256_expected="$expected_vit_n256" \
      -v vit264_expected="$expected_vit_n264" -v mm63_expected="$expected_mm_n63" \
      -v mm64_expected="$expected_mm_n64" -v mm66_expected="$expected_mm_n66" '
    /^RM08_PL_CALL / {
      n++
      if ($0 ~ /status=PL([[:space:]]|$)/) {
        pl++
        if ($0 ~ /K=4304 M=1152 N=1008([[:space:]]|$)/) n1008++
        else if ($0 ~ /K=4304 M=1152 N=1024([[:space:]]|$)/) n1024++
        else if ($0 ~ /K=4304 M=1152 N=1056([[:space:]]|$)/) n1056++
        else if ($0 ~ /K=4304 M=1152 N=252([[:space:]]|$)/) n252++
        else if ($0 ~ /K=4304 M=1152 N=256([[:space:]]|$)/) n256++
        else if ($0 ~ /K=4304 M=1152 N=264([[:space:]]|$)/) n264++
        else bad++
      } else if ($0 ~ /status=CPU_FALLBACK([[:space:]]|$)/) {
        fallback++
        if ($0 !~ /layer=ffn_down status=CPU_FALLBACK reason=unmatched_merger / ||
            $0 !~ /dtype=f16\/f32\/f32 /) bad++
        if ($0 ~ /K=17216 M=1152 N=252 /) vit252++
        else if ($0 ~ /K=17216 M=1152 N=256 /) vit256++
        else if ($0 ~ /K=17216 M=1152 N=264 /) vit264++
        else if ($0 ~ /K=4608 M=1024 N=63 /) mm63++
        else if ($0 ~ /K=4608 M=1024 N=64 /) mm64++
        else if ($0 ~ /K=4608 M=1024 N=66 /) mm66++
        else bad++
      } else bad++
    }
    END {
      printf "individual_trace_lines=%d pl=%d N1008=%d N1024=%d N1056=%d N252=%d N256=%d N264=%d fallback=%d vit252=%d vit256=%d vit264=%d mm63=%d mm64=%d mm66=%d bad=%d\n", n, pl, n1008, n1024, n1056, n252, n256, n264, fallback, vit252, vit256, vit264, mm63, mm64, mm66, bad
      exit !(n == total && pl == pl_expected && n1008 == n1008_expected && n1024 == n1024_expected &&
             n1056 == n1056_expected && n252 == n252_expected && n256 == n256_expected &&
             n264 == n264_expected && fallback == fallback_expected &&
             vit252 == vit252_expected && vit256 == vit256_expected && vit264 == vit264_expected &&
             mm63 == mm63_expected && mm64 == mm64_expected && mm66 == mm66_expected && bad == 0)
    }
  ' "$trace" || die "$stem individual PL/fallback trace mismatch"
  awk -v groups="$groups" '
    /^RM08_PL_LAYER / {
      layers++
      if ($0 !~ ("expected=" groups " ") || $0 !~ ("calls=" groups " ") ||
          $0 !~ ("pl=" groups " ") || $0 !~ /cpu_fallback=0([[:space:]]|$)/) bad++
    }
    END { printf "layer_summary_lines=%d bad=%d\n", layers, bad; exit !(layers == 27 && bad == 0) }
  ' "$trace" || die "$stem per-layer summary mismatch"
  echo "$stem checks=PASS time=$time_log trace=$trace stdout=$stdout_log stderr=$stderr_log"
  unset RM08_FFN_DOWN_PL RM08_PL_EXPECTED_MEDIA_GROUPS RM08_PL_TRACE RM09_PL_EXPECTED_QID
}

run_request 38299 3 61715b8521ae5d6a \
  4365f84b5d2cbc5c740bafde088b1aeaf5c7b8326c8b9b5bfe2a529f9bc7a256 \
  3 $'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what is the last number to the right?\nAnswer:'
run_request 35419 7 004b75d1299e653c \
  f703a5ce6bbf7c1aa1dd11fda26a7a30323913d404d771d51deba387c840c5f6 \
  "SHERIFF'S" $'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: who is the car for?\nAnswer:'

echo "requests_complete=PASS qid38299_groups=3 qid35419_groups=7"
echo "evidence_dir=$run_dir"
