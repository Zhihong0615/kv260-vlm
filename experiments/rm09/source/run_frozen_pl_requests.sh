#!/usr/bin/env bash
set -euo pipefail

readonly base_app=k26-starter-kits
readonly app=kv260-rm07-bounded-k16
readonly board_root=/home/ubuntu/kv260-vlm-p2-cpu
readonly install_dir=/lib/firmware/xilinx/$app
readonly cli=$board_root/rm08-build-1a90d48/bin/llama-mtmd-cli
readonly cpu_lib=$board_root/rm08-build-1a90d48/bin/libggml-cpu.so.0.24.0
readonly cpu_lib_link=$board_root/rm08-build-1a90d48/bin/libggml-cpu.so.0
readonly model=$board_root/input/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf
readonly mmproj=$board_root/input/mmproj-MiniCPM-V-4.6-f16.gguf
readonly helper=$board_root/rm08-build-1a90d48/bin/rm08-ffn-down-helper-smoke
readonly tensor_dir=/tmp/rm08-deploy/tensors
readonly diagnostics_script=/tmp/rm09-clock-diagnostics.sh
readonly restore_script=/tmp/rm09-restore-starter-kit.sh
readonly cpu_pair_lock=/tmp/rm09-f16x/cpu-pair-active
readonly diagnostics_sha_expected=3f77d1b8cc7ba0ecce195aacce5c6e9d125d38bb3e7d48eb937895ad74586058
readonly restore_sha_expected=ef428ea3e9215897310cfeaa5d79a4be320005ac8bbd6655c8505f2a9abe7e23
readonly app_bin_sha=b8ba3e533b96e84f8cbb23acc8808146286671ccced979c9381f9afe9ddfbc60
readonly app_dtbo_sha=4fca210afb0258e7f67f6071a1d7d4c98681d60f847bfec5a3f00e0ab7c052d2
readonly app_json_sha=802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344
readonly cli_sha=73e4c8826a159e1bcf420b57cce20201353c611d57af15cdb6200f60ec5f00d0
readonly model_sha=8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773
readonly mmproj_sha=ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293
readonly cpu_lib_sha=7351973a8d004b7380f27dd0849aa4d2965e4c91b9f473d99696efb8cbf2a265
readonly route_ceiling_hz=187512000
readonly safe_rate_hz=100000000
readonly cli_timeout_seconds=1200
readonly rollback_seconds=3000

if [[ "$(id -u)" -ne 0 || "$#" -ne 0 ]]; then
  echo "Usage: sudo bash $0" >&2
  exit 2
fi
for script_and_sha in "$diagnostics_script:$diagnostics_sha_expected" "$restore_script:$restore_sha_expected"; do
  path="${script_and_sha%%:*}"
  expected="${script_and_sha##*:}"
  [[ -r "$path" && "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || {
    echo "Missing or changed board helper script: $path" >&2
    exit 2
  }
done
[[ -x "$cli" && -x "$helper" && -x /usr/bin/time && -x "$(command -v timeout)" ]]
if [[ -e "$cpu_pair_lock" ]]; then
  echo "ERROR: RM09 CPU-only P0/P1 pair is active; refusing an overlapping PL app load" >&2
  exit 1
fi
[[ "$(sha256sum "$cli" | awk '{print $1}')" == "$cli_sha" ]]
[[ "$(sha256sum "$model" | awk '{print $1}')" == "$model_sha" ]]
[[ "$(sha256sum "$mmproj" | awk '{print $1}')" == "$mmproj_sha" ]]
[[ -r "$cpu_lib" && "$(readlink -f "$cpu_lib_link")" == "$cpu_lib" ]]
[[ "$(sha256sum "$cpu_lib" | awk '{print $1}')" == "$cpu_lib_sha" ]]
ldd "$cli" | awk -v library="$cpu_lib_link" '$1 == "libggml-cpu.so.0" && $3 == library { found=1 } END { exit !found }' || die "llama-mtmd-cli does not resolve the frozen CPU library"
for layer in 0 13 26; do
  for suffix in weight.f16 activation.f32 output.f32; do
    [[ -s "$tensor_dir/ffn_down-$layer.$suffix" ]]
  done
done

is_starter_active() {
  xmutil listapps 2>&1 | awk '$1 == "k26-starter-kits" && $NF ~ /^0,?$/ { found=1 } END { exit !found }'
}
is_rm07_active() {
  xmutil listapps 2>&1 | awk '$1 == "kv260-rm07-bounded-k16" && $NF ~ /^0,?$/ { found=1 } END { exit !found }'
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
die() { echo "ERROR: $*" >&2; exit 1; }

[[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] || die "FPGA manager is not operating"
is_starter_active || die "starter-kit must be active at entry"
[[ "$(cat /sys/bus/platform/devices/fclk0/set_rate)" == 99999999 ]] || die "FCLK0 must be at the measured 100MHz readback"
[[ -z "$(pgrep -x llama-mtmd-cli || true)" ]] || die "another llama-mtmd-cli is active"

umask 022
mkdir -p "$board_root/runs"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_dir="$board_root/runs/rm09-pl-q38299-q35419-$stamp"
mkdir -m 0755 -- "$run_dir"
exec > >(tee -a "$run_dir/driver.log") 2>&1

echo "run_dir=$run_dir"
echo "host=$(hostname) utc=$(date -u +%FT%TZ) boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "runtime=$cli cli_sha256=$cli_sha model_sha256=$model_sha mmproj_sha256=$mmproj_sha"
echo "runtime_cpu_library=$cpu_lib runtime_cpu_library_sha256=$cpu_lib_sha ldd_resolution=$(ldd "$cli" | awk '$1 == "libggml-cpu.so.0" { print $0 }')"
echo "rm07_bit_bin_sha256=$app_bin_sha route_ceiling_hz=$route_ceiling_hz safe_requested_hz=$safe_rate_hz"
snapshot before_clock_diagnostics
bash "$diagnostics_script" "$run_dir/clock-diagnostics-before-load"
snapshot after_clock_diagnostics

for item in "$app_bin_sha $install_dir/$app.bit.bin" "$app_dtbo_sha $install_dir/$app.dtbo" "$app_json_sha $install_dir/shell.json"; do
  read -r expected file <<<"$item"
  [[ -s "$file" ]] || die "missing installed RM07 artifact: $file"
  printf '%s  %s\n' "$expected" "$file" | sha256sum -c -
done

restore_log="$run_dir/restore.log"
rollback_unit="rm09-pl-q38299-q35419-$stamp-rollback"
restore_ok=0
timer_armed=0
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
snapshot before_app_unload
xmutil unloadapp
for _ in $(seq 1 120); do
  if ! grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null; then break; fi
  sleep 0.5
done
! grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null || die "RM07 UIO remains after unload"

# Starter-kit is unloaded before the only clock write.  This remains at the
# observed 100MHz point and below the 187.512MHz route ceiling.
echo "$safe_rate_hz" > /sys/bus/platform/devices/fclk0/set_rate
safe_readback="$(cat /sys/bus/platform/devices/fclk0/set_rate)"
echo "requested_safe_fclk0_hz=$safe_rate_hz actual_fclk0_hz=$safe_readback"
(( safe_readback >= 99000000 && safe_readback <= 101000000 && safe_readback <= route_ceiling_hz )) || die "FCLK0 readback left the safe 100MHz band"

xmutil loadapp "$app"
ready=0
for _ in $(seq 1 120); do
  if [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] &&
     grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null && is_rm07_active; then
    ready=1
    break
  fi
  sleep 0.5
done
[[ "$ready" == 1 ]] || die "RM07 HLS UIO did not become ready"
snapshot rm07_loaded
active_fclk0_hz="$(cat /sys/bus/platform/devices/fclk0/set_rate)"
echo "active_fclk0_hz=$active_fclk0_hz"
(( active_fclk0_hz >= 99000000 && active_fclk0_hz <= 101000000 && active_fclk0_hz <= route_ceiling_hz )) || die "RM07 did not remain at safe 100MHz FCLK0 after load"
echo "hls_uio_name=$(grep -h '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name | head -n1)"

run_helper() {
  local stem="$1"
  local trace="$run_dir/$stem-helper-trace.txt"
  local logfile="$run_dir/$stem-helper.log"
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
  local expected_n1120=$((7 * groups))
  local expected_n280=$((20 * groups))
  local expected_fallbacks=$((2 * groups))
  echo "request=$stem media_groups=$groups expected_PL_calls=27x$groups=$expected_calls expected_total_calls=$expected_total_calls expected_N1120=$expected_n1120 expected_N280=$expected_n280 expected_fallbacks=$expected_fallbacks threads=4 batch_threads=4"
  echo "image_id=$image_id image_sha256=$image_sha expected_answer=$(printf '%q' "$answer_expected")"
  echo "frozen_prompt=$(printf '%q' "$prompt")"
  echo "cli_args=-m $model --mmproj $mmproj --image $image -p <frozen-prompt> -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4"
  : >"$trace"
  export RM08_FFN_DOWN_PL=1
  export RM08_PL_EXPECTED_MEDIA_GROUPS="$groups"
  export RM08_PL_TRACE="$trace"
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

  awk -v total="$expected_total_calls" -v pl_expected="$expected_calls" \
      -v wide_expected="$expected_n1120" -v narrow_expected="$expected_n280" \
      -v fallback_expected="$expected_fallbacks" -v groups="$groups" '
    /^RM08_PL_CALL / {
      n++
      if ($0 ~ /status=PL([[:space:]]|$)/) {
        pl++
        if ($0 ~ /K=4304 M=1152 N=1120([[:space:]]|$)/) wide++
        else if ($0 ~ /K=4304 M=1152 N=280([[:space:]]|$)/) narrow++
        else bad++
      } else if ($0 ~ /status=CPU_FALLBACK([[:space:]]|$)/) {
        fallback++
        if ($0 ~ /layer=ffn_down status=CPU_FALLBACK reason=unmatched_merger K=17216 M=1152 N=280 /) vit++
        else if ($0 ~ /layer=ffn_down status=CPU_FALLBACK reason=unmatched_merger K=4608 M=1024 N=70 /) mm++
        else bad++
      } else bad++
    }
    END {
      printf "individual_trace_lines=%d pl=%d wide=%d narrow=%d fallback=%d vit_merger=%d mm_down=%d bad=%d\n", n, pl, wide, narrow, fallback, vit, mm, bad
      exit !(n == total && pl == pl_expected && wide == wide_expected && narrow == narrow_expected &&
             fallback == fallback_expected && vit == groups && mm == groups && bad == 0)
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
  unset RM08_FFN_DOWN_PL RM08_PL_EXPECTED_MEDIA_GROUPS RM08_PL_TRACE
}

run_request 38299 3 61715b8521ae5d6a \
  4365f84b5d2cbc5c740bafde088b1aeaf5c7b8326c8b9b5bfe2a529f9bc7a256 \
  3 $'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what is the last number to the right?\nAnswer:'
run_request 35419 7 004b75d1299e653c \
  f703a5ce6bbf7c1aa1dd11fda26a7a30323913d404d771d51deba387c840c5f6 \
  "SHERIFF'S" $'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: who is the car for?\nAnswer:'

echo "requests_complete=PASS qid38299_groups=3 qid35419_groups=7"
echo "evidence_dir=$run_dir"
