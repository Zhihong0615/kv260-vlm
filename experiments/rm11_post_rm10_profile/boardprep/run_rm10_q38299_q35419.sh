#!/usr/bin/env bash
set -euo pipefail

# RM10 A revision: same frozen RM09 runtime/AXI ABI, routed PL0 at 100 MHz.
# Reuses the authorized routed RM10 bitstream and frozen RM09 runtime.
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
readonly identity_source=$deploy_dir/boardprep/axilite_probe.c
readonly diagnostics_script=$deploy_dir/boardprep/collect_clock_diagnostics.sh
readonly restore_script=$deploy_dir/boardprep/restore_starter_kit.sh
readonly cpu_pair_lock=/tmp/rm09-f16x/cpu-pair-active

# Route-owned artifact identities are pinned below; no build or bitstream change occurs here.
readonly app_bit_source_sha=18ba853551f85ce1814332eacd370264696a93423fbf5a408e028b307c18ac23
readonly app_bin_sha=722387cc80b345f0b7b29bdffe61911707cf12c5c25e42867d339b4a0c6fb5d7
readonly app_dtbo_sha=8d689efec80db0cb800fd71848bbfde2277b0e492333a01ddba6b606414d3b2b
readonly app_json_sha=802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344
readonly runtime_manifest_sha=e35e0b1ff5ae5c3630af49c20f5494dd5ce82753f33374b216c36ac1b1cb95a9
readonly cli_sha=6a45ea3647b1db19d06408441729681d19966af569040e4577b1410b803d7254
readonly cpu_lib_sha=b44c771488d7fa63e73d1ddf0f15427f1943000fc969d4fe4cd42102e1c777b7
readonly model_sha=8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773
readonly mmproj_sha=ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293
readonly diagnostics_sha=3f77d1b8cc7ba0ecce195aacce5c6e9d125d38bb3e7d48eb937895ad74586058
readonly restore_sha=ef428ea3e9215897310cfeaa5d79a4be320005ac8bbd6655c8505f2a9abe7e23
readonly route_source_commit=3602eafa7de5cee187b79f8e28c186a19f6f6133
readonly route_source_sha=31a7b26f9bf28c0ad57892184ed30b42126162111fe4c4bda82aa7847754319a
readonly route_ip_zip_sha=b54c4ac0a15dc4501c3d1d470eeb2664fe9e2e60cf0d9ba7a0cfd9fdcca82e6b
readonly ip_component_sha=fae7fde4af5b3f5a1237d5e7717ea97622a9a8c6107ba96c97bfe6bb19feda56
readonly route_xsa_sha=a85ff605c6e5dbe52a4e413ce38499b70d6c1bc857509ff5433d1f03f5934e0b
readonly route_ceiling_hz=100000000
readonly bounded_pool_bytes=1671168
readonly cma_margin_kb=8192
readonly cma_minimum_kb=$(((bounded_pool_bytes + 1023) / 1024 + cma_margin_kb))
readonly request_timeout_seconds=1200
readonly rollback_seconds=4200

die() { echo "ERROR: $*" >&2; exit 1; }
sha256_of() { sha256sum "$1" | awk '{print $1}'; }

[[ "$app_bit_source_sha" =~ ^[0-9a-f]{64}$ && "$app_bin_sha" =~ ^[0-9a-f]{64}$ ]] || die "route image hashes are pending; no app operation allowed"
[[ "$route_source_commit" =~ ^[0-9a-f]{7,40}$ && "$route_source_sha" =~ ^[0-9a-f]{64}$ && "$route_ip_zip_sha" =~ ^[0-9a-f]{64}$ && "$ip_component_sha" =~ ^[0-9a-f]{64}$ && "$route_xsa_sha" =~ ^[0-9a-f]{64}$ ]] || die "corrected route source/IP/XSA identity is pending; no app operation allowed"
if [[ "$(id -u)" -ne 0 || "$#" -ne 0 ]]; then
  echo "Usage: sudo bash $0" >&2
  exit 2
fi
[[ -r "$runtime_manifest" && "$(sha256_of "$runtime_manifest")" == "$runtime_manifest_sha" ]] || die "RM09 runtime manifest missing/changed"
(cd "$runtime_root" && sha256sum -c RM09_RUNTIME_ARTIFACTS.sha256) || die "RM09 runtime manifest check failed"
for pair in \
  "$cli:$cli_sha" "$cpu_lib:$cpu_lib_sha" "$model:$model_sha" "$mmproj:$mmproj_sha" \
  "$diagnostics_script:$diagnostics_sha" "$restore_script:$restore_sha"; do
  path=$(cut -d: -f1 <<<"$pair")
  expected=$(cut -d: -f2- <<<"$pair")
  [[ -r "$path" && "$(sha256_of "$path")" == "$expected" ]] || die "missing/changed pinned input: $path"
done
[[ -x "$cli" && -x /usr/bin/time && -x "$(command -v timeout)" ]]
[[ "$(readlink -f "$cpu_lib_link")" == "$cpu_lib" && "$(sha256_of "$cpu_lib_link")" == "$cpu_lib_sha" ]] || die "RM09 CPU-library symlink/identity mismatch"
LD_LIBRARY_PATH="$runtime_root/bin" ldd "$cli" | awk -v library="$cpu_lib_link" '$1 == "libggml-cpu.so.0" && $3 == library { found=1 } END { exit !found }' || die "CLI does not resolve the pinned RM09 CPU library"
[[ "$(sha256_of "$model")" == "$model_sha" && "$(sha256_of "$mmproj")" == "$mmproj_sha" ]] || die "model identity mismatch"
[[ -z "$(pgrep -x llama-mtmd-cli || true)" ]] || die "another llama-mtmd-cli is active"
[[ ! -e "$cpu_pair_lock" ]] || die "RM09 CPU-only paired run is active"
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
run_dir=$board_root/runs/rm10-a-ra-q38299-q35419-$stamp
mkdir -m 0755 -- "$run_dir"
exec > >(tee -a "$run_dir/driver.log") 2>&1
echo "run_dir=$run_dir"
echo "host=$(hostname) utc=$(date -u +%FT%TZ) boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "rm10_source_commit=$route_source_commit source_sha256=$route_source_sha ip_component_sha256=$ip_component_sha ip_zip_sha256=$route_ip_zip_sha xsa_sha256=$route_xsa_sha"
echo "rm10_bit_sha256=$app_bit_source_sha bit_bin_sha256=$app_bin_sha dtbo_sha256=$app_dtbo_sha shell_json_sha256=$app_json_sha"
echo "runtime=RM09 CLI_sha256=$cli_sha CPU_library_sha256=$cpu_lib_sha runtime_manifest_sha256=$runtime_manifest_sha"
echo "model_sha256=$model_sha mmproj_sha256=$mmproj_sha"
echo "request_timeout_s=$request_timeout_seconds rollback_s=$rollback_seconds"
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

run_request() {
  local qid="$1" groups="$2" image_id="$3" image_sha="$4" expected_answer="$5" prompt="$6"
  local stem="q$qid" image="$board_root/input/textvqa-dev50/$image_id.jpg"
  local trace="$run_dir/$stem-pl-trace.txt" time_log="$run_dir/$stem-time-v.txt"
  local stdout_log="$run_dir/$stem-stdout.log" stderr_log="$run_dir/$stem-stderr.log"
  local expected_pl=$((27 * groups)) expected_total=$((29 * groups)) expected_fallback=$((2 * groups))
  local exp_n1008=0 exp_n1024=0 exp_n1056=0 exp_n252=0 exp_n256=0 exp_n264=0
  local exp_vit252=0 exp_vit256=0 exp_vit264=0 exp_mm63=0 exp_mm64=0 exp_mm66=0
  case "$qid" in
    38299)
      exp_n1024=14 exp_n1056=7 exp_n256=40 exp_n264=20
      exp_vit256=2 exp_vit264=1 exp_mm64=2 exp_mm66=1
      ;;
    35419)
      exp_n1008=49 exp_n252=140
      exp_vit252=7 exp_mm63=7
      ;;
    *) die "unsupported RM10 request QID $qid" ;;
  esac
  [[ -r "$image" && "$(sha256_of "$image")" == "$image_sha" ]] || die "$stem frozen input image missing/changed"
  require_cma_for_dma "$stem-before-VLM-DMA"
  : >"$trace"
  export LD_LIBRARY_PATH="$runtime_root/bin:$(printenv LD_LIBRARY_PATH 2>/dev/null || true)"
  export RM08_FFN_DOWN_PL=1 RM08_PL_EXPECTED_MEDIA_GROUPS="$groups" RM08_PL_TRACE="$trace"
  export RM09_PL_EXPECTED_QID="$qid"
  echo "request=$stem image=$image image_sha256=$image_sha expected_answer=$(printf '%q' "$expected_answer") media_groups=$groups"
  echo "prompt=$(printf '%q' "$prompt")"
  echo "args=-m $model --mmproj $mmproj --image $image -p <frozen-prompt> -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4"
  local rc=0
  /usr/bin/time -v -o "$time_log" "$(command -v timeout)" --signal=TERM --kill-after=10s "$request_timeout_seconds"s \
    "$cli" -m "$model" --mmproj "$mmproj" --image "$image" -p "$prompt" \
    -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 \
    --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4 \
    </dev/null >"$stdout_log" 2>"$stderr_log" || rc=$?
  snapshot "$stem-after-request"
  [[ "$rc" -eq 0 && -s "$time_log" && -s "$stdout_log" && -s "$stderr_log" ]] || die "$stem CLI failed/incomplete"
  local answer
  answer=$(awk 'NF { sub(/\r$/, ""); last=$0 } END { print last }' "$stdout_log")
  [[ "$answer" == "$expected_answer" ]] || die "$stem answer differs from frozen output"
  echo "$stem answer=$(printf '%q' "$answer") expected=$(printf '%q' "$expected_answer")"
  local summary
  summary=$(grep '^RM08_PL_SUMMARY ' "$trace" | tail -n1 || true)
  [[ -n "$summary" ]] || die "$stem RM08_PL_SUMMARY missing"
  value() { awk -v key="$1" '{ for (i=1;i<=NF;++i) { split($i,pair,"="); if (pair[1]==key) { print pair[2]; exit } } }' <<<"$summary"; }
  for check in \
    "expected_calls:$expected_pl" "expected_total_calls:$expected_total" "actual_calls:$expected_total" \
    "expected_PL:$expected_pl" "actual_PL:$expected_pl" "cpu_fallbacks:$expected_fallback" \
    "expected_merger_cpu:$expected_fallback" "merger_cpu:$expected_fallback" \
    "expected_vit_merger_cpu:$groups" "vit_merger_cpu:$groups" \
    "expected_mm_down_cpu:$groups" "mm_down_cpu:$groups" "matches_expected:1" "media_groups:$groups"; do
    local key="${check%%:*}" expected="${check#*:}" actual
    actual=$(value "$key")
    [[ "$actual" == "$expected" ]] || die "$stem PL summary mismatch $key got=${actual:-MISSING} expected=$expected"
  done
  [[ "$(value expectation_enabled)" == 1 ]] || die "$stem dispatch expectation disabled"
  local ext
  ext=$(grep '^RM09_PL_EXTENTS ' "$trace" | tail -n1 || true)
  [[ -n "$ext" ]] || die "$stem RM09_PL_EXTENTS missing"
  ext_value() { awk -v key="$1" '{for(i=1;i<=NF;++i){split($i,pair,"=");if(pair[1]==key){print pair[2];exit}}}' <<<"$ext"; }
  for check in "qid:$qid" "expectation_enabled:1" "expected_groups:$groups" "actual_groups:$groups" \
    "expected_N1008:$exp_n1008" "actual_N1008:$exp_n1008" \
    "expected_N1024:$exp_n1024" "actual_N1024:$exp_n1024" \
    "expected_N1056:$exp_n1056" "actual_N1056:$exp_n1056" \
    "expected_N252:$exp_n252" "actual_N252:$exp_n252" \
    "expected_N256:$exp_n256" "actual_N256:$exp_n256" \
    "expected_N264:$exp_n264" "actual_N264:$exp_n264" "matches_expected:1"; do
    local key="${check%%:*}" expected="${check#*:}" actual
    actual=$(ext_value "$key")
    [[ "$actual" == "$expected" ]] || die "$stem PL extent mismatch $key got=${actual:-MISSING} expected=$expected"
  done
  awk -v total="$expected_total" -v pl_expected="$expected_pl" \
      -v n1008_expected="$exp_n1008" -v n1024_expected="$exp_n1024" -v n1056_expected="$exp_n1056" \
      -v n252_expected="$exp_n252" -v n256_expected="$exp_n256" -v n264_expected="$exp_n264" \
      -v fallback_expected="$expected_fallback" -v vit252_expected="$exp_vit252" \
      -v vit256_expected="$exp_vit256" -v vit264_expected="$exp_vit264" \
      -v mm63_expected="$exp_mm63" -v mm64_expected="$exp_mm64" -v mm66_expected="$exp_mm66" '
    /^RM08_PL_CALL / {
      calls++
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
      printf "calls=%d PL=%d N1008=%d N1024=%d N1056=%d N252=%d N256=%d N264=%d fallback=%d ViT252=%d ViT256=%d ViT264=%d MM63=%d MM64=%d MM66=%d bad=%d\n", calls,pl,n1008,n1024,n1056,n252,n256,n264,fallback,vit252,vit256,vit264,mm63,mm64,mm66,bad
      exit !(calls==total && pl==pl_expected && fallback==fallback_expected &&
             n1008==n1008_expected && n1024==n1024_expected && n1056==n1056_expected &&
             n252==n252_expected && n256==n256_expected && n264==n264_expected &&
             vit252==vit252_expected && vit256==vit256_expected && vit264==vit264_expected &&
             mm63==mm63_expected && mm64==mm64_expected && mm66==mm66_expected && bad==0)
    }
  ' "$trace" || die "$stem per-call PL/merger histogram mismatch"
  awk -v groups="$groups" '/^RM08_PL_LAYER / { layers++; if ($0 !~ ("expected=" groups " ") || $0 !~ ("calls=" groups " ") || $0 !~ ("pl=" groups " ") || $0 !~ /cpu_fallback=0([[:space:]]|$)/) bad++ } END {exit !(layers==27 && bad==0)}' "$trace" || die "$stem per-layer PL coverage mismatch"
  echo "$stem=PASS wall_log=$time_log trace=$trace stdout=$stdout_log stderr=$stderr_log"
  unset RM08_FFN_DOWN_PL RM08_PL_EXPECTED_MEDIA_GROUPS RM08_PL_TRACE RM09_PL_EXPECTED_QID
}

run_request 38299 3 61715b8521ae5d6a \
  4365f84b5d2cbc5c740bafde088b1aeaf5c7b8326c8b9b5bfe2a529f9bc7a256 \
  3 $'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what is the last number to the right?\nAnswer:'
run_request 35419 7 004b75d1299e653c \
  f703a5ce6bbf7c1aa1dd11fda26a7a30323913d404d771d51deba387c840c5f6 \
  "SHERIFF'S" $'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: who is the car for?\nAnswer:'

echo "rm10_multi_request_board_run=PASS qid38299_groups=3 qid35419_groups=7 evidence_dir=$run_dir"
snapshot before_restore
