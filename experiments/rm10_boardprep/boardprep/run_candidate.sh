#!/usr/bin/env bash
set -euo pipefail

# RM10 A revision: same frozen RM09 runtime/AXI ABI, routed PL0 at 100 MHz.
# Invocation refuses until the exact route-owned .bit.bin SHA is filled below.
readonly base_app=k26-starter-kits
readonly app=kv260-rm10-a-ra
readonly deploy_dir=/tmp/rm10-boardprep
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
readonly image=$board_root/input/textvqa-dev50/58d543df7eab2bfc.jpg
readonly bench=/tmp/rm08-deploy/ffn_down_bench
readonly tensor_dir=/tmp/rm08-deploy/tensors
readonly identity_source=$deploy_dir/boardprep/axilite_probe.c
readonly diagnostics_script=$deploy_dir/boardprep/collect_clock_diagnostics.sh
readonly restore_script=$deploy_dir/boardprep/restore_starter_kit.sh
readonly tensor_manifest=$deploy_dir/boardprep/real_tensor_hashes.sha256
readonly cpu_pair_lock=/tmp/rm09-f16x/cpu-pair-active

# These identity fields stay pending until recurrence validation and the
# corrected route complete. Never reuse the provisional first-route image.
readonly app_bit_source_sha=__RM10_CORRECTED_ROUTE_BIT_SHA_PENDING__
readonly app_bin_sha=__RM10_CORRECTED_ROUTE_BIT_BIN_SHA_PENDING__
readonly app_dtbo_sha=8d689efec80db0cb800fd71848bbfde2277b0e492333a01ddba6b606414d3b2b
readonly app_json_sha=802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344
readonly runtime_manifest_sha=e35e0b1ff5ae5c3630af49c20f5494dd5ce82753f33374b216c36ac1b1cb95a9
readonly cli_sha=6a45ea3647b1db19d06408441729681d19966af569040e4577b1410b803d7254
readonly cpu_lib_sha=b44c771488d7fa63e73d1ddf0f15427f1943000fc969d4fe4cd42102e1c777b7
readonly model_sha=8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773
readonly mmproj_sha=ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293
readonly image_sha_expected=3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f
readonly bench_sha=c687a693d20a95c81787754aa07b49f51e3cf868116f8652aa22f6d4f30ac914
readonly diagnostics_sha=3f77d1b8cc7ba0ecce195aacce5c6e9d125d38bb3e7d48eb937895ad74586058
readonly restore_sha=ef428ea3e9215897310cfeaa5d79a4be320005ac8bbd6655c8505f2a9abe7e23
readonly tensor_manifest_sha=fb842b9f72f2c079b78868d293eaa77d2cc4a44e351a92d4f70be580b6f0109d
readonly route_source_commit=__RM10_CORRECTED_SOURCE_COMMIT_PENDING__
readonly route_ip_zip_sha=__RM10_CORRECTED_IP_ZIP_SHA_PENDING__
readonly route_xsa_sha=__RM10_CORRECTED_XSA_SHA_PENDING__
readonly route_ceiling_hz=100000000
readonly bounded_pool_bytes=1671168
readonly cma_margin_kb=8192
readonly cma_minimum_kb=$(((bounded_pool_bytes + 1023) / 1024 + cma_margin_kb))
readonly request_timeout_seconds=1200
readonly rollback_seconds=4200

die() { echo "ERROR: $*" >&2; exit 1; }
sha256_of() { sha256sum "$1" | awk '{print $1}'; }

[[ "$app_bit_source_sha" =~ ^[0-9a-f]{64}$ && "$app_bin_sha" =~ ^[0-9a-f]{64}$ ]] || die "route image hashes are pending; no app operation allowed"
[[ "$route_source_commit" =~ ^[0-9a-f]{7,40}$ && "$route_ip_zip_sha" =~ ^[0-9a-f]{64}$ && "$route_xsa_sha" =~ ^[0-9a-f]{64}$ ]] || die "corrected route source/IP/XSA identity is pending; no app operation allowed"
if [[ "$(id -u)" -ne 0 || "$#" -ne 0 ]]; then
  echo "Usage: sudo bash $0" >&2
  exit 2
fi
[[ -r "$runtime_manifest" && "$(sha256_of "$runtime_manifest")" == "$runtime_manifest_sha" ]] || die "RM09 runtime manifest missing/changed"
(cd "$runtime_root" && sha256sum -c RM09_RUNTIME_ARTIFACTS.sha256) || die "RM09 runtime manifest check failed"
for pair in \
  "$cli:$cli_sha" "$cpu_lib:$cpu_lib_sha" "$model:$model_sha" "$mmproj:$mmproj_sha" \
  "$image:$image_sha_expected" "$diagnostics_script:$diagnostics_sha" \
  "$restore_script:$restore_sha" "$tensor_manifest:$tensor_manifest_sha"; do
  path=$(cut -d: -f1 <<<"$pair")
  expected=$(cut -d: -f2- <<<"$pair")
  [[ -r "$path" && "$(sha256_of "$path")" == "$expected" ]] || die "missing/changed pinned input: $path"
done
[[ -x "$cli" && -x "$bench" && -x /usr/bin/time && -x "$(command -v timeout)" ]]
[[ "$(readlink -f "$cpu_lib_link")" == "$cpu_lib" && "$(sha256_of "$cpu_lib_link")" == "$cpu_lib_sha" ]] || die "RM09 CPU-library symlink/identity mismatch"
LD_LIBRARY_PATH="$runtime_root/bin" ldd "$cli" | awk -v library="$cpu_lib_link" '$1 == "libggml-cpu.so.0" && $3 == library { found=1 } END { exit !found }' || die "CLI does not resolve the pinned RM09 CPU library"
[[ "$(sha256_of "$model")" == "$model_sha" && "$(sha256_of "$mmproj")" == "$mmproj_sha" ]] || die "model identity mismatch"
[[ "$(sha256_of "$image")" == "$image_sha_expected" ]] || die "QID37804 image identity mismatch"
[[ -z "$(pgrep -x llama-mtmd-cli || true)" ]] || die "another llama-mtmd-cli is active"
[[ ! -e "$cpu_pair_lock" ]] || die "RM09 CPU-only paired run is active"
for layer in 0 13 26; do
  for suffix in weight.f16 activation.f32 output.f32; do
    [[ -s "$tensor_dir/ffn_down-$layer.$suffix" ]] || die "missing real tensor ffn_down-$layer.$suffix"
  done
done
(cd "$tensor_dir" && sha256sum -c "$tensor_manifest") || die "QID37804 tensor payload checksum failure"
[[ -s "$package_source/$app.bit" && "$(sha256_of "$package_source/$app.bit")" == "$app_bit_source_sha" ]] || die "route .bit source missing/changed"
[[ -s "$package_source/$app.bit.bin" && "$(sha256_of "$package_source/$app.bit.bin")" == "$app_bin_sha" ]] || die "Bootgen .bit.bin missing/changed"
[[ -s "$package_source/$app.dtbo" && "$(sha256_of "$package_source/$app.dtbo")" == "$app_dtbo_sha" ]] || die "RM10 DTBO missing/changed"
[[ -s "$package_source/shell.json" && "$(sha256_of "$package_source/shell.json")" == "$app_json_sha" ]] || die "RM10 shell.json missing/changed"

is_starter_active() {
  xmutil listapps 2>&1 | awk '$1 == "k26-starter-kits" && $NF ~ /^0,?$/ { found=1 } END { exit !found }'
}
is_rm10_active() {
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
  free_kb=$(awk '$1 == "CmaFree:" { print $2 }' /proc/meminfo)
  [[ "$free_kb" =~ ^[0-9]+$ ]] || die "$stage cannot read CmaFree"
  echo "stage=$stage CmaFree_kB=$free_kb bounded_XRT_pool_bytes=$bounded_pool_bytes cma_margin_kB=$cma_margin_kb required_kB=$cma_minimum_kb"
  (( free_kb >= cma_minimum_kb )) || die "$stage failed the RM09 bounded BO plus 8 MiB CMA margin"
}

[[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] || die "FPGA manager is not operating"
is_starter_active || die "k26-starter-kits must be active on entry"
[[ "$(cat /sys/bus/platform/devices/fclk0/set_rate 2>/dev/null || true)" == 99999999 ]] || die "FCLK0 must read 99,999,999 Hz at entry"
require_cma_for_dma before_RM10_load
if [[ -e "$install_dir" ]]; then
  for pair in "$app_bin_sha:$install_dir/$app.bit.bin" "$app_dtbo_sha:$install_dir/$app.dtbo" "$app_json_sha:$install_dir/shell.json"; do
    expected=$(cut -d: -f1 <<<"$pair")
    path=$(cut -d: -f2- <<<"$pair")
    [[ -s "$path" && "$(sha256_of "$path")" == "$expected" ]] || die "existing RM10 install differs from pinned package: $path"
  done
  package_preinstalled=1
else
  package_preinstalled=0
fi

umask 022
mkdir -p "$board_root/runs"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
run_dir=$board_root/runs/rm10-a-ra-q37804-$stamp
mkdir -m 0755 -- "$run_dir"
exec > >(tee -a "$run_dir/driver.log") 2>&1
echo "run_dir=$run_dir"
echo "host=$(hostname) utc=$(date -u +%FT%TZ) boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "rm10_source_commit=$route_source_commit ip_zip_sha256=$route_ip_zip_sha xsa_sha256=$route_xsa_sha"
echo "rm10_bit_sha256=$app_bit_source_sha bit_bin_sha256=$app_bin_sha dtbo_sha256=$app_dtbo_sha shell_json_sha256=$app_json_sha"
echo "runtime=RM09 CLI_sha256=$cli_sha CPU_library_sha256=$cpu_lib_sha runtime_manifest_sha256=$runtime_manifest_sha"
echo "model_sha256=$model_sha mmproj_sha256=$mmproj_sha image_sha256=$image_sha_expected"
echo "standalone_bench_sha256=$(sha256_of "$bench") request_timeout_s=$request_timeout_seconds rollback_s=$rollback_seconds"
snapshot before_clock_diagnostics
bash "$diagnostics_script" "$run_dir/clock-diagnostics-before-load"
snapshot after_clock_diagnostics

readonly restore_log=$run_dir/restore.log
readonly rollback_unit=rm10-a-ra-$stamp-rollback
restore_ok=0
timer_armed=0
package_installed_by_script=0
finish() {
  local original_rc=$? restore_rc=0
  trap - EXIT INT TERM
  set +e
  if [[ "$timer_armed" == 1 ]]; then
    echo "explicit_restore_begin utc=$(date -u +%FT%TZ)"
    bash "$restore_script" "$restore_log"
    restore_rc=$?
    if (( restore_rc == 0 )); then
      restore_ok=1
      if [[ "$package_installed_by_script" == 1 ]]; then
        rm -f -- "$install_dir/$app.bit.bin" "$install_dir/$app.dtbo" "$install_dir/shell.json" && rmdir -- "$install_dir"
        if (( $? == 0 )); then echo "rm10_package_cleanup=PASS"; else restore_rc=1; echo "rm10_package_cleanup=FAIL"; fi
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

systemd-run --quiet --unit="$rollback_unit" --on-active="$rollback_seconds"s "$restore_script" "$restore_log" || die "could not create RM09-known-good rollback timer"
systemctl is-active --quiet "$rollback_unit.timer" || die "rollback timer is not active; no app state changed"
timer_armed=1
echo "rollback_timer=$rollback_unit.timer timer_state=active restore_after_seconds=$rollback_seconds"
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
     grep -q '^axi_perf_mon_0$' /sys/class/uio/uio*/name 2>/dev/null && is_rm10_active; then
    ready=1
    break
  fi
  sleep 0.5
done
[[ "$ready" == 1 ]] || die "RM10 HLS/APM UIOs did not become ready"
snapshot rm10_loaded
active_fclk0_hz=$(cat /sys/bus/platform/devices/fclk0/set_rate)
(( active_fclk0_hz >= 99000000 && active_fclk0_hz <= 101000000 && active_fclk0_hz <= route_ceiling_hz )) || die "RM10 PL0 readback exceeds routed 100 MHz"
echo "active_fclk0_hz=$active_fclk0_hz"
require_cma_for_dma after_RM10_load
gcc -O2 -Wall -Wextra -Werror "$identity_source" -o "$run_dir/rm10-axilite-identity-probe" || die "could not build AXI-Lite identity probe"
"$run_dir/rm10-axilite-identity-probe" | tee "$run_dir/axilite-identity-probe.log" || die "AXI-Lite identity probe failed"
grep -Fq 'AXI_LITE_ABI_PROBE=0xfffffffc (-4) expected=-4 PASS' "$run_dir/axilite-identity-probe.log" || die "AXI-Lite invalid-task return differs from RM09 ABI"

run_tensor() {
  local layer="$1" n="$2" stage="$3" compute="$4" stem=tensor-$1
  local out=$run_dir/$stem.log time_log=$run_dir/$stem-time-v.txt
  require_cma_for_dma "$stem-before-DMA"
  echo "standalone_begin layer=ffn_down-$layer N=$n expected_stage_commands=$stage expected_compute_commands=$compute utc=$(date -u +%FT%TZ)"
  /usr/bin/time -v -o "$time_log" "$(command -v timeout)" --signal=TERM --kill-after=10s 120s \
    "$bench" "$tensor_dir/ffn_down-$layer.weight.f16" \
      "$tensor_dir/ffn_down-$layer.activation.f32" "$tensor_dir/ffn_down-$layer.output.f32" \
      "ffn_down-$layer" "$n" 1 >"$out" 2>&1 || die "$stem standalone run failed"
  cat "$out"
  grep -Fq "CALL=1 N=$n " "$out" || die "$stem per-call metrics missing"
  grep -Fq "commands=$stage/$compute " "$out" || die "$stem stage/compute command counts mismatch"
  local total_line max_abs rmse cosine
  total_line=$(grep -F "TOTAL calls=1 N=$n " "$out" | tail -n1)
  [[ -n "$total_line" ]] || die "$stem total metrics missing"
  max_abs=$(sed -n 's/.* max_abs=\([^ ]*\).*/\1/p' <<<"$total_line")
  rmse=$(sed -n 's/.* RMSE=\([^ ]*\).*/\1/p' <<<"$total_line")
  cosine=$(sed -n 's/.* cosine=\([^ ]*\).*/\1/p' <<<"$total_line")
  awk -v a="$max_abs" -v r="$rmse" -v c="$cosine" 'BEGIN { exit !(a+0 <= 1e-3 && r+0 <= 1e-4 && c+0 >= 0.999) }' || die "$stem frozen numeric gate failed"
  echo "standalone_numeric_gate=PASS layer=ffn_down-$layer max_abs=$max_abs RMSE=$rmse cosine=$cosine time_log=$time_log"
  snapshot "$stem-after-DMA"
}
run_tensor 0 1120 35 315
run_tensor 13 280 9 81
run_tensor 26 280 9 81

readonly trace=$run_dir/q37804-pl-trace.txt
readonly time_log=$run_dir/q37804-time-v.txt
readonly stdout_log=$run_dir/q37804-stdout.log
readonly stderr_log=$run_dir/q37804-stderr.log
require_cma_for_dma q37804-before-VLM-DMA
: >"$trace"
unset RM09_PL_EXPECTED_QID
export LD_LIBRARY_PATH="$runtime_root/bin:$(printenv LD_LIBRARY_PATH 2>/dev/null || true)"
export RM08_FFN_DOWN_PL=1 RM08_PL_EXPECTED_MEDIA_GROUPS=5 RM08_PL_TRACE=$trace
prompt=$'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what letter does these athlete\x27s school likely begin with?\nAnswer:'
echo "q37804_prompt=$(printf '%q' "$prompt")"
echo "q37804_args=-m $model --mmproj $mmproj --image $image -p <frozen-prompt> -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4"
set +e
/usr/bin/time -v -o "$time_log" "$(command -v timeout)" --signal=TERM --kill-after=10s "$request_timeout_seconds"s \
  "$cli" -m "$model" --mmproj "$mmproj" --image "$image" -p "$prompt" \
  -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 \
  --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4 \
  </dev/null >"$stdout_log" 2>"$stderr_log"
request_rc=$?
set -e
snapshot q37804-after-request
[[ "$request_rc" -eq 0 && -s "$time_log" && -s "$stdout_log" ]] || die "QID37804 CLI failed or left incomplete evidence"
answer=$(awk 'NF { sub(/\r$/, ""); last=$0 } END { print last }' "$stdout_log")
echo "q37804_answer=$(printf '%q' "$answer")"
[[ "$answer" == G ]] || die "QID37804 answer differs from frozen answer G"
summary=$(grep '^RM08_PL_SUMMARY ' "$trace" | tail -n1 || true)
[[ -n "$summary" ]] || die "RM08_PL_SUMMARY missing"
value() { awk -v key="$1" '{ for (i=1; i<=NF; ++i) { split($i, pair, "="); if (pair[1] == key) { print pair[2]; exit } } }' <<<"$summary"; }
for check in \
  expected_calls:135 expected_total_calls:145 actual_calls:145 expected_PL:135 actual_PL:135 \
  cpu_fallbacks:10 expected_N1120:35 actual_N1120:35 expected_N280:100 actual_N280:100 \
  expected_merger_cpu:10 merger_cpu:10 expected_vit_merger_cpu:5 vit_merger_cpu:5 \
  expected_mm_down_cpu:5 mm_down_cpu:5 matches_expected:1 media_groups:5; do
  key=$(cut -d: -f1 <<<"$check")
  expected=$(cut -d: -f2- <<<"$check")
  actual=$(value "$key")
  if [[ -z "$actual" ]]; then actual=MISSING; fi
  echo "q37804_trace_check=$key actual=$actual expected=$expected"
  [[ "$actual" == "$expected" ]] || die "QID37804 PL summary mismatch at $key"
done
[[ "$(value expectation_enabled)" == 1 ]] || die "runtime dispatch expectation is disabled"
awk '
  /^RM08_PL_CALL / {
    total++
    if ($0 ~ /status=PL([[:space:]]|$)/) {
      pl++
      if ($0 ~ /K=4304 M=1152 N=1120([[:space:]]|$)/) wide++
      else if ($0 ~ /K=4304 M=1152 N=280([[:space:]]|$)/) narrow++
      else bad++
    } else if ($0 ~ /status=CPU_FALLBACK([[:space:]]|$)/) {
      fallback++
      if ($0 ~ /reason=unmatched_merger K=17216 M=1152 N=280 /) vit++
      else if ($0 ~ /reason=unmatched_merger K=4608 M=1024 N=70 /) mm++
      else bad++
    } else bad++
  }
  END {
    printf "trace_lines=%d PL=%d N1120=%d N280=%d CPU_FALLBACK=%d ViT_merger=%d MM_down=%d bad=%d\n", total, pl, wide, narrow, fallback, vit, mm, bad
    exit !(total==145 && pl==135 && wide==35 && narrow==100 && fallback==10 && vit==5 && mm==5 && bad==0)
  }
' "$trace" || die "QID37804 individual PL/fallback calls mismatch"
awk '
  /^RM08_PL_LAYER / {
    layers++
    if ($0 !~ /expected=5([[:space:]]|$)/ || $0 !~ /calls=5([[:space:]]|$)/ ||
        $0 !~ /pl=5([[:space:]]|$)/ || $0 !~ /cpu_fallback=0([[:space:]]|$)/) bad++
  }
  END { printf "layer_summary_lines=%d bad=%d\n", layers, bad; exit !(layers==27 && bad==0) }
' "$trace" || die "QID37804 per-layer summary mismatch"
echo "integrated_q37804_checks=PASS time_log=$time_log trace=$trace stdout=$stdout_log stderr=$stderr_log"
snapshot before_restore
echo "rm10_candidate_board_run=PASS evidence_dir=$run_dir"
