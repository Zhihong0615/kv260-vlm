#!/usr/bin/env bash
set -euo pipefail

app="kv260-rm07-bounded-k16"
base_app="k26-starter-kits"
install_dir="/lib/firmware/xilinx/$app"
image_sha_expected="3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f"
app_bin_sha="b8ba3e533b96e84f8cbb23acc8808146286671ccced979c9381f9afe9ddfbc60"
app_dtbo_sha="4fca210afb0258e7f67f6071a1d7d4c98681d60f847bfec5a3f00e0ab7c052d2"
app_json_sha="802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344"
rollback_seconds=1500

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run through sudo on the KV260: sudo bash $0 CLI MODEL MMPROJ IMAGE" >&2
  exit 2
fi
if [[ "$#" -ne 4 ]]; then
  echo "Usage: sudo bash $0 /path/to/llama-mtmd-cli MODEL.gguf MMPROJ.gguf 58d543df7eab2bfc.jpg" >&2
  exit 2
fi

cli="$(realpath -e -- "$1")"
model="$(realpath -e -- "$2")"
mmproj="$(realpath -e -- "$3")"
image="$(realpath -e -- "$4")"
[[ -x "$cli" && -f "$model" && -r "$model" && -f "$mmproj" && -r "$mmproj" && -f "$image" && -r "$image" ]]
[[ "$(basename -- "$cli")" == "llama-mtmd-cli" ]]
[[ "$(basename -- "$model")" == "MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf" ]]
[[ "$(basename -- "$mmproj")" == "mmproj-MiniCPM-V-4.6-f16.gguf" ]]
[[ "$(basename -- "$image")" == "58d543df7eab2bfc.jpg" ]]
[[ -x /usr/bin/time ]]
timeout_bin="$(command -v timeout)"
[[ -x "$timeout_bin" ]]

mkdir -p /home/ubuntu/kv260-vlm-p2-cpu/runs
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_dir="/home/ubuntu/kv260-vlm-p2-cpu/runs/rm08-vlm-q37804-$stamp"
mkdir -m 0750 -- "$run_dir"
exec > >(tee -a "$run_dir/driver.log") 2>&1

die() { echo "ERROR: $*" >&2; exit 1; }
snapshot() {
  local label="$1"
  echo "snapshot=$label utc=$(date -u +%FT%TZ)"
  grep -E '^(MemAvailable|CmaTotal|CmaFree):' /proc/meminfo || true
  echo "cpu0_scaling_cur_freq_kHz=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo UNKNOWN)"
  echo "fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
}
is_starter_active() {
  xmutil listapps 2>&1 | awk '$1 == "k26-starter-kits" && $NF ~ /^0,?$/ { found=1 } END { exit !found }'
}

echo "run_dir=$run_dir"
echo "host=$(hostname) utc=$(date -u +%FT%TZ)"
echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "cli=$cli cli_sha256=$(sha256sum "$cli" | awk '{print $1}')"
echo "model=$model model_sha256=$(sha256sum "$model" | awk '{print $1}')"
echo "mmproj=$mmproj mmproj_sha256=$(sha256sum "$mmproj" | awk '{print $1}')"
image_sha="$(sha256sum "$image" | awk '{print $1}')"
echo "image=$image image_sha256=$image_sha"
[[ "$image_sha" == "$image_sha_expected" ]] || die "QID 37804 image hash mismatch"

for item in \
  "$app_bin_sha  $install_dir/$app.bit.bin" \
  "$app_dtbo_sha  $install_dir/$app.dtbo" \
  "$app_json_sha  $install_dir/shell.json"; do
  read -r expected file <<<"$item"
  [[ -s "$file" ]] || die "missing installed RM07 app file: $file"
  printf '%s  %s\n' "$expected" "$file" | sha256sum -c -
done
[[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == "operating" ]] || die "FPGA manager is not operating"
is_starter_active || die "k26-starter-kits is not the active base app"
snapshot before_load

trace="$run_dir/rm08_pl_trace.txt"
time_log="$run_dir/time-v.txt"
stdout_log="$run_dir/stdout.log"
stderr_log="$run_dir/stderr.log"
restore_log="$run_dir/restore.log"
restore_script="$run_dir/restore_starter_kit.sh"
rollback_unit="rm08-vlm-q37804-$stamp-rollback"
cat >"$restore_script" <<EOF
#!/usr/bin/env bash
set +e
exec >>"$restore_log" 2>&1
echo "watchdog_restore_begin utc=\$(date -u +%FT%TZ)"
xmutil unloadapp
xmutil loadapp "$base_app"
for i in \$(seq 1 120); do
  [[ -r /sys/class/fpga_manager/fpga0/state && \$(cat /sys/class/fpga_manager/fpga0/state) == operating ]] && break
  sleep 0.5
done
cat /sys/class/fpga_manager/fpga0/state 2>/dev/null
xmutil listapps
echo "watchdog_restore_end utc=\$(date -u +%FT%TZ)"
EOF
chmod 0700 "$restore_script"

restore_ok=0
timer_armed=0
finish() {
  local original_rc=$?
  local restore_rc=0
  trap - EXIT INT TERM
  set +e
  if [[ "$timer_armed" == 1 ]]; then
    echo "explicit_restore_begin utc=$(date -u +%FT%TZ)" | tee -a "$restore_log"
    xmutil unloadapp >>"$restore_log" 2>&1
    xmutil loadapp "$base_app" >>"$restore_log" 2>&1
    for _ in $(seq 1 120); do
      [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null)" == operating ]] && is_starter_active && break
      sleep 0.5
    done
    if [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null)" == operating ]] && is_starter_active; then
      restore_ok=1
      systemctl stop "$rollback_unit.timer" >/dev/null 2>&1
      systemctl stop "$rollback_unit.service" >/dev/null 2>&1
      systemctl reset-failed "$rollback_unit.timer" "$rollback_unit.service" >/dev/null 2>&1
      echo "starter_kit_restore=PASS"
    else
      restore_rc=1
      echo "starter_kit_restore=FAIL watchdog_timer_left_armed=1"
    fi
    snapshot after_restore
    echo "explicit_restore_end utc=$(date -u +%FT%TZ)" | tee -a "$restore_log"
  fi
  if [[ "$original_rc" -eq 0 && "$restore_rc" -ne 0 ]]; then original_rc=1; fi
  echo "run_exit_status=$original_rc starter_kit_restore=$([[ "$restore_ok" == 1 ]] && echo PASS || echo NOT_CONFIRMED)"
  exit "$original_rc"
}

# Arm rollback before touching the loaded fabric. If this script is killed,
# systemd restores the starter-kit after 1500 seconds.
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
systemd-run --quiet --unit="$rollback_unit" --on-active="${rollback_seconds}s" "$restore_script"
timer_armed=1
echo "rollback_timer=$rollback_unit.timer restore_after_seconds=$rollback_seconds"
xmutil unloadapp
xmutil loadapp "$app"

ready=0
for _ in $(seq 1 120); do
  if [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] &&
     grep -q '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name 2>/dev/null; then
    ready=1
    break
  fi
  sleep 0.5
done
[[ "$ready" == 1 ]] || die "RM07 HLS UIO did not become ready"
uio_name_file="$(grep -l '^vision_ffn_down_tile_0$' /sys/class/uio/uio*/name | head -n1)"
echo "hls_uio_name_file=$uio_name_file hls_uio_device=/dev/$(basename "$(dirname "$uio_name_file")")"
echo "hls_uio_device_name=$(cat "$uio_name_file")"
[[ "$(cat /sys/class/fpga_manager/fpga0/state)" == operating ]] || die "FPGA manager left operating state"
snapshot before_request

prompt=$'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what letter does these athlete\x27s school likely begin with?\nAnswer:'
printf '%s\n' "frozen_prompt=$(printf '%q' "$prompt")"
echo "cli_timeout_seconds=1200 timeout_kill_after_seconds=10"
printf '%s\n' "cli_args=-m $model --mmproj $mmproj --image $image -p <frozen-prompt> -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4"
: >"$trace"
export RM08_FFN_DOWN_PL=1
export RM08_PL_EXPECTED_MEDIA_GROUPS=5
export RM08_PL_TRACE="$trace"
request_start="$(date -u +%FT%TZ)"
echo "request_begin_utc=$request_start"
set +e
/usr/bin/time -v -o "$time_log" \
  "$timeout_bin" --signal=TERM --kill-after=10s 1200s \
  "$cli" -m "$model" --mmproj "$mmproj" --image "$image" -p "$prompt" \
  -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 \
  --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4 \
  >"$stdout_log" 2>"$stderr_log"
request_rc=$?
set -e
echo "request_end_utc=$(date -u +%FT%TZ) request_exit_code=$request_rc"
snapshot after_request_before_restore
[[ -s "$time_log" ]] || die "GNU time did not produce resource data"
[[ -s "$stdout_log" ]] || die "CLI stdout is empty"
answer="$(awk 'NF { sub(/\r$/, ""); last=$0 } END { print last }' "$stdout_log")"
echo "last_nonempty_stdout_line=$answer"

summary="$(grep '^RM08_PL_SUMMARY ' "$trace" | tail -n1 || true)"
[[ -n "$summary" ]] || die "RM08_PL_SUMMARY missing; PL dispatch was not proven"
value() { sed -n "s/.*\<$1=\([^ ]*\).*/\1/p" <<<"$summary"; }
for check in \
  "expected_calls:135" "expected_total_calls:140" "actual_calls:140" \
  "expected_PL:135" "actual_PL:135" "cpu_fallbacks:5" \
  "expected_N1120:35" "actual_N1120:35" "expected_N280:100" "actual_N280:100" \
  "expected_merger_cpu:5" "merger_cpu:5" "matches_expected:1" "media_groups:5"; do
  key="${check%%:*}"; expected="${check#*:}"; actual="$(value "$key")"
  echo "trace_check=$key actual=${actual:-MISSING} expected=$expected"
  [[ "$actual" == "$expected" ]] || die "PL trace mismatch at $key"
done
[[ "$(value expectation_enabled)" == 1 ]] || die "runtime dispatch expectation is not enabled"

awk '
  /^RM08_PL_CALL / {
    total++
    if ($0 ~ /status=PL([[:space:]]|$)/) {
      pl++
      if ($0 ~ /N=1120([[:space:]]|$)/) wide++
      else if ($0 ~ /N=280([[:space:]]|$)/) narrow++
      else badshape++
    } else if ($0 ~ /status=CPU_FALLBACK([[:space:]]|$)/) {
      fallback++
      if ($0 ~ /layer=ffn_down([[:space:]]|$)/ && $0 ~ /K=17216([[:space:]]|$)/) merger++
      else badfallback++
    }
  }
  END {
    printf "trace_lines=%d pl=%d n1120=%d n280=%d merger_fallbacks=%d\n", total, pl, wide, narrow, merger
    exit !(total == 140 && pl == 135 && wide == 35 && narrow == 100 && fallback == 5 && merger == 5 && !badshape && !badfallback)
  }
' "$trace" || die "individual PL/fallback trace lines do not match the expected request"
awk '
  /^RM08_PL_LAYER / {
    layers++
    if ($0 !~ /expected=5([[:space:]]|$)/ || $0 !~ /calls=5([[:space:]]|$)/ ||
        $0 !~ /pl=5([[:space:]]|$)/ || $0 !~ /cpu_fallback=0([[:space:]]|$)/) bad++
  }
  END { printf "layer_summary_lines=%d bad=%d\n", layers, bad; exit !(layers == 27 && !bad) }
' "$trace" || die "per-layer call counts do not match the 27-layer request"
[[ "$request_rc" -eq 0 ]] || die "QID 37804 CLI returned $request_rc"
[[ "$answer" == "G" ]] || die "final answer differs from frozen QID 37804 answer G"
echo "integrated_q37804_checks=PASS"
echo "evidence_dir=$run_dir"
