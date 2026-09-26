#!/usr/bin/env bash
set -euo pipefail

# Run this only when the completed RM10 candidate request falls within ±5% of
# the historical 522.34 s RM08 result: 496.2–548.5 s.
readonly base_app=k26-starter-kits
readonly app=kv260-rm09-static-extent
readonly deploy_dir=/tmp/rm10-boardprep
readonly package_source=$deploy_dir/package/$app
readonly board_root=/home/ubuntu/kv260-vlm-p2-cpu
readonly install_dir=/lib/firmware/xilinx/$app
readonly runtime_root=$board_root/rm09-static-extent-build-22d96ed06be3
readonly cli=$runtime_root/bin/llama-mtmd-cli
readonly cpu_lib=$runtime_root/bin/libggml-cpu.so.0.24.0
readonly cpu_lib_link=$runtime_root/bin/libggml-cpu.so.0
readonly model=$board_root/input/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf
readonly mmproj=$board_root/input/mmproj-MiniCPM-V-4.6-f16.gguf
readonly image=$board_root/input/textvqa-dev50/58d543df7eab2bfc.jpg
readonly restore_script=$deploy_dir/boardprep/restore_starter_kit.sh
readonly runtime_manifest=$runtime_root/RM09_RUNTIME_ARTIFACTS.sha256
readonly package_manifest_sha=cae3a750941c191ba17f1c9cbfacaa5a5093ecc41eaa9a99f1ba1f00a0134a66
readonly app_bin_sha=819b088199ac4346c1eb9b7bb65ade42afe8f95eaeec02cca4bc6bdd2bb0d87b
readonly app_dtbo_sha=85fd0a2e2186886d8d52178c0934ba51585c37c28e5dd54a1c5536f2e506521e
readonly app_json_sha=802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344
readonly runtime_manifest_sha=e35e0b1ff5ae5c3630af49c20f5494dd5ce82753f33374b216c36ac1b1cb95a9
readonly cli_sha=6a45ea3647b1db19d06408441729681d19966af569040e4577b1410b803d7254
readonly cpu_lib_sha=b44c771488d7fa63e73d1ddf0f15427f1943000fc969d4fe4cd42102e1c777b7
readonly model_sha=8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773
readonly mmproj_sha=ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293
readonly image_sha=3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f
readonly restore_sha=ef428ea3e9215897310cfeaa5d79a4be320005ac8bbd6655c8505f2a9abe7e23
readonly cma_minimum_kb=9824
readonly route_ceiling_hz=100000000
readonly timeout_seconds=1200
readonly rollback_seconds=4200
die() { echo "ERROR: $*" >&2; exit 1; }
sha256_of() { sha256sum "$1" | awk '{print $1}'; }

[[ "$#" -eq 1 && "$1" == /* ]] || { echo "Usage: bash $0 RM10_CANDIDATE_RUN_DIR" >&2; exit 2; }
candidate_dir=$(realpath -e -- "$1")
case "$candidate_dir" in
  "$board_root"/runs/rm10-a-ra-q37804-*) ;;
  *) die "candidate path is outside the fixed RM10 run root" ;;
esac
candidate_time_log=$candidate_dir/q37804-time-v.txt
candidate_driver=$candidate_dir/driver.log
[[ -r "$candidate_time_log" && -r "$candidate_driver" ]] || die "candidate evidence missing"
grep -Fq 'rm10_candidate_board_run=PASS' "$candidate_driver" || die "RM10 candidate failed"
grep -Fq 'starter_kit_restore=PASS' "$candidate_driver" || die "candidate did not restore the starter app"
candidate_wall=$(awk -F': ' '/Elapsed \(wall clock\) time/ {
  n=split($2, t, ":"); if(n==2) s=t[1]*60+t[2]; else if(n==3) s=t[1]*3600+t[2]*60+t[3];
  printf "%.2f", s; found=1
} END { if(!found) exit 1 }' "$candidate_time_log") || die "candidate wall time cannot be read"
if ! awk -v w="$candidate_wall" 'BEGIN { exit !(w>=496.2 && w<=548.5) }'; then
  echo "conditional_static_control=SKIP candidate_wall_s=$candidate_wall historical_s=522.34 trigger=496.2..548.5"
  exit 0
fi
echo "conditional_static_control=RUN candidate_wall_s=$candidate_wall historical_s=522.34 trigger=496.2..548.5"
[[ "$(id -u)" -eq 0 ]] || die "trigger passed; run with sudo only after board owner approval"
[[ -r "$restore_script" && "$(sha256_of "$restore_script")" == "$restore_sha" ]] || die "RM09 restore helper changed"
[[ -r "$runtime_manifest" && "$(sha256_of "$runtime_manifest")" == "$runtime_manifest_sha" ]] || die "RM09 runtime manifest mismatch"
(cd "$runtime_root" && sha256sum -c RM09_RUNTIME_ARTIFACTS.sha256) || die "RM09 runtime manifest check failed"
for pair in "$cli:$cli_sha" "$cpu_lib:$cpu_lib_sha" "$model:$model_sha" "$mmproj:$mmproj_sha" "$image:$image_sha"; do
  path=$(cut -d: -f1 <<<"$pair"); expected=$(cut -d: -f2- <<<"$pair")
  [[ -r "$path" && "$(sha256_of "$path")" == "$expected" ]] || die "pinned input mismatch: $path"
done
[[ "$(readlink -f "$cpu_lib_link")" == "$cpu_lib" ]] || die "RM09 CPU library symlink mismatch"
LD_LIBRARY_PATH="$runtime_root/bin" ldd "$cli" | awk -v lib="$cpu_lib_link" '$1=="libggml-cpu.so.0" && $3==lib {ok=1} END {exit !ok}' || die "CLI CPU-library binding mismatch"
[[ -r "$package_source/SHA256SUMS" && "$(sha256_of "$package_source/SHA256SUMS")" == "$package_manifest_sha" ]] || die "RM09 package manifest mismatch"
(cd "$package_source" && sha256sum -c SHA256SUMS) || die "RM09 package checksum failure"
for pair in "$app_bin_sha:$package_source/$app.bit.bin" "$app_dtbo_sha:$package_source/$app.dtbo" "$app_json_sha:$package_source/shell.json"; do
  expected=$(cut -d: -f1 <<<"$pair"); path=$(cut -d: -f2- <<<"$pair")
  [[ -s "$path" && "$(sha256_of "$path")" == "$expected" ]] || die "RM09 static package mismatch: $path"
done

is_starter() { xmutil listapps 2>&1 | awk '$1=="k26-starter-kits" && $NF~/^0,?$/ {ok=1} END{exit !ok}'; }
is_baseline() { xmutil listapps 2>&1 | awk -v app="$app" '$1==app && $NF~/^0,?$/ {ok=1} END{exit !ok}'; }
snapshot() {
  echo "snapshot=$1 utc=$(date -u +%FT%TZ)"
  grep -E '^(MemAvailable|CmaTotal|CmaFree|SwapFree):' /proc/meminfo || true
  echo "fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
  echo "fclk0=$(cat /sys/bus/platform/devices/fclk0/set_rate 2>/dev/null || echo UNKNOWN)"
}
require_cma() {
  local got
  got=$(awk '$1=="CmaFree:" {print $2}' /proc/meminfo)
  [[ "$got" =~ ^[0-9]+$ ]] && ((got>=cma_minimum_kb)) || die "insufficient CMA before $1"
}
[[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] || die "FPGA manager is not operating"
is_starter || die "starter image must be active before control"
[[ "$(cat /sys/bus/platform/devices/fclk0/set_rate 2>/dev/null || true)" == 99999999 ]] || die "FCLK0 must be 99,999,999 Hz"
[[ -z "$(pgrep -x llama-mtmd-cli || true)" ]] || die "another CLI is active"
require_cma load
if [[ -e "$install_dir" ]]; then
  for pair in "$app_bin_sha:$install_dir/$app.bit.bin" "$app_dtbo_sha:$install_dir/$app.dtbo" "$app_json_sha:$install_dir/shell.json"; do
    expected=$(cut -d: -f1 <<<"$pair"); path=$(cut -d: -f2- <<<"$pair")
    [[ -s "$path" && "$(sha256_of "$path")" == "$expected" ]] || die "existing RM09 app differs: $path"
  done
  package_preinstalled=1
else
  package_preinstalled=0
fi

umask 022
mkdir -p "$board_root/runs"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
run_dir=$board_root/runs/rm10-rm09-static-q37804-$stamp
mkdir -m 0755 -- "$run_dir"
exec > >(tee -a "$run_dir/driver.log") 2>&1
echo "run_dir=$run_dir candidate_dir=$candidate_dir candidate_wall_s=$candidate_wall"
echo "static_baseline=RM09 app_bit_bin_sha256=$app_bin_sha dtbo_sha256=$app_dtbo_sha"
echo "runtime=RM09 CLI_sha256=$cli_sha CPU_library_sha256=$cpu_lib_sha"
echo "model_sha256=$model_sha mmproj_sha256=$mmproj_sha image_sha256=$image_sha"
snapshot before_load
readonly restore_log=$run_dir/restore.log
readonly rollback_unit=rm10-rm09-static-$stamp-rollback
timer_armed=0
restore_ok=0
package_installed_by_script=0
finish() {
  local rc=$? rrc=0
  trap - EXIT INT TERM
  set +e
  if [[ "$timer_armed" == 1 ]]; then
    bash "$restore_script" "$restore_log"
    rrc=$?
    if ((rrc==0)); then
      restore_ok=1
      if [[ "$package_installed_by_script" == 1 ]]; then
        rm -f -- "$install_dir/$app.bit.bin" "$install_dir/$app.dtbo" "$install_dir/shell.json" && rmdir -- "$install_dir"
        if (( $? != 0 )); then rrc=1; fi
      fi
      systemctl stop "$rollback_unit.timer" >/dev/null 2>&1
      systemctl stop "$rollback_unit.service" >/dev/null 2>&1
      systemctl reset-failed "$rollback_unit.timer" "$rollback_unit.service" >/dev/null 2>&1
    else
      echo "starter_kit_restore=FAIL watchdog_timer_left_armed=1"
    fi
    snapshot after_restore
  fi
  if [[ "$rc" -eq 0 && "$rrc" -ne 0 ]]; then rc=1; fi
  echo "run_exit_status=$rc starter_kit_restore=$([[ "$restore_ok" == 1 ]] && echo PASS || echo NOT_CONFIRMED)"
  exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
systemd-run --quiet --unit="$rollback_unit" --on-active="$rollback_seconds"s "$restore_script" "$restore_log" || die "cannot arm RM09-known restore timer"
systemctl is-active --quiet "$rollback_unit.timer" || die "restore timer is not active"
timer_armed=1
echo "rollback_timer=$rollback_unit.timer restore_after_seconds=$rollback_seconds"
if [[ "$package_preinstalled" == 0 ]]; then
  install -d -m 0755 -- "$install_dir"
  install -m 0644 -- "$package_source/$app.bit.bin" "$install_dir/$app.bit.bin"
  install -m 0644 -- "$package_source/$app.dtbo" "$install_dir/$app.dtbo"
  install -m 0644 -- "$package_source/shell.json" "$install_dir/shell.json"
  package_installed_by_script=1
fi
xmutil unloadapp
for _ in $(seq 1 120); do
  if ! grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null; then break; fi
  sleep 0.5
done
! grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null || die "previous HLS UIO remains"
xmutil loadapp "$app"
ready=0
for _ in $(seq 1 120); do
  if [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] &&
     grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null && is_baseline; then ready=1; break; fi
  sleep 0.5
done
[[ "$ready" == 1 ]] || die "RM09 baseline app not ready"
snapshot static_baseline_loaded
active_fclk=$(cat /sys/bus/platform/devices/fclk0/set_rate)
((active_fclk>=99000000 && active_fclk<=101000000 && active_fclk<=route_ceiling_hz)) || die "baseline FCLK exceeds 100 MHz"
require_cma q37804_DMA

readonly trace=$run_dir/q37804-pl-trace.txt
readonly time_log=$run_dir/q37804-time-v.txt
readonly stdout_log=$run_dir/q37804-stdout.log
readonly stderr_log=$run_dir/q37804-stderr.log
: >"$trace"
unset RM09_PL_EXPECTED_QID
export LD_LIBRARY_PATH="$runtime_root/bin:$(printenv LD_LIBRARY_PATH 2>/dev/null || true)"
export RM08_FFN_DOWN_PL=1 RM08_PL_EXPECTED_MEDIA_GROUPS=5 RM08_PL_TRACE=$trace
prompt=$'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what letter does these athlete\x27s school likely begin with?\nAnswer:'
set +e
/usr/bin/time -v -o "$time_log" "$(command -v timeout)" --signal=TERM --kill-after=10s "$timeout_seconds"s \
  "$cli" -m "$model" --mmproj "$mmproj" --image "$image" -p "$prompt" \
  -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 \
  --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4 \
  </dev/null >"$stdout_log" 2>"$stderr_log"
request_rc=$?
set -e
snapshot after_q37804
[[ "$request_rc" -eq 0 && -s "$time_log" && -s "$stdout_log" ]] || die "same-runtime static request failed"
answer=$(awk 'NF {sub(/\r$/, ""); last=$0} END {print last}' "$stdout_log")
[[ "$answer" == G ]] || die "same-runtime static output differs from G"
summary=$(grep '^RM08_PL_SUMMARY ' "$trace" | tail -n1 || true)
[[ -n "$summary" ]] || die "PL summary missing"
value() { awk -v key="$1" '{for(i=1;i<=NF;i++){split($i,p,"=");if(p[1]==key){print p[2];exit}}}' <<<"$summary"; }
[[ "$(value expectation_enabled)" == 1 ]] || die "runtime dispatch expectation is disabled"
for check in expected_calls:135 expected_total_calls:145 actual_calls:145 expected_PL:135 actual_PL:135 \
  cpu_fallbacks:10 expected_N1120:35 actual_N1120:35 expected_N280:100 actual_N280:100 \
  expected_merger_cpu:10 merger_cpu:10 expected_vit_merger_cpu:5 vit_merger_cpu:5 \
  expected_mm_down_cpu:5 mm_down_cpu:5 matches_expected:1 media_groups:5; do
  key=$(cut -d: -f1 <<<"$check"); expected=$(cut -d: -f2- <<<"$check"); got=$(value "$key")
  [[ "$got" == "$expected" ]] || die "same-runtime static summary mismatch at $key"
done
awk '
  /^RM08_PL_CALL / {
    total++
    if ($0~/status=PL([[:space:]]|$)/) {
      pl++
      if ($0~/K=4304 M=1152 N=1120([[:space:]]|$)/) wide++
      else if ($0~/K=4304 M=1152 N=280([[:space:]]|$)/) narrow++
      else bad++
    } else if ($0~/status=CPU_FALLBACK([[:space:]]|$)/) {
      fb++
      if ($0~/reason=unmatched_merger K=17216 M=1152 N=280 /) vit++
      else if ($0~/reason=unmatched_merger K=4608 M=1024 N=70 /) mm++
      else bad++
    } else bad++
  }
  END {exit !(total==145 && pl==135 && wide==35 && narrow==100 && fb==10 && vit==5 && mm==5 && bad==0)}
' "$trace" || die "same-runtime static per-call PL histogram mismatch"
awk '
  /^RM08_PL_LAYER / {
    layers++
    if ($0 !~ /expected=5([[:space:]]|$)/ || $0 !~ /calls=5([[:space:]]|$)/ ||
        $0 !~ /pl=5([[:space:]]|$)/ || $0 !~ /cpu_fallback=0([[:space:]]|$)/) bad++
  }
  END { exit !(layers==27 && bad==0) }
' "$trace" || die "same-runtime static per-layer summary mismatch"
snapshot before_restore
echo "same_runtime_static_q37804_control=PASS candidate_wall_s=$candidate_wall run_dir=$run_dir trace=$trace time_log=$time_log"
