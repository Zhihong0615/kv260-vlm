#!/usr/bin/env bash
set -euo pipefail

readonly board_root=/home/ubuntu/kv260-vlm-p2-cpu
readonly cli="$board_root/rm08-build-1a90d48/bin/llama-mtmd-cli"
readonly model="$board_root/input/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf"
readonly mmproj="$board_root/input/mmproj-MiniCPM-V-4.6-f16.gguf"
readonly model_sha=8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773
readonly mmproj_sha=ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293
readonly cli_sha=73e4c8826a159e1bcf420b57cce20201353c611d57af15cdb6200f60ec5f00d0
readonly max_seconds=1500

if [[ "$#" != 1 ]]; then
  echo "Usage: bash $0 38299|35419" >&2
  exit 2
fi

case "$1" in
  38299)
    qid=38299
    media_groups=3
    image_id=61715b8521ae5d6a
    image_sha=4365f84b5d2cbc5c740bafde088b1aeaf5c7b8326c8b9b5bfe2a529f9bc7a256
    expected_answer=3
    prompt=$'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what is the last number to the right?\nAnswer:'
    ;;
  35419)
    qid=35419
    media_groups=7
    image_id=004b75d1299e653c
    image_sha=f703a5ce6bbf7c1aa1dd11fda26a7a30323913d404d771d51deba387c840c5f6
    expected_answer="SHERIFF'S"
    prompt=$'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: who is the car for?\nAnswer:'
    ;;
  *)
    echo "Unsupported QID: $1" >&2
    exit 2
    ;;
esac

readonly image="$board_root/input/textvqa-dev50/$image_id.jpg"
for file in "$cli" "$model" "$mmproj" "$image"; do
  [[ -r "$file" ]] || { echo "Missing input: $file" >&2; exit 2; }
done
[[ -x "$cli" && -x /usr/bin/time && -x "$(command -v timeout)" ]]
[[ "$(sha256sum "$cli" | awk '{print $1}')" == "$cli_sha" ]]
[[ "$(sha256sum "$model" | awk '{print $1}')" == "$model_sha" ]]
[[ "$(sha256sum "$mmproj" | awk '{print $1}')" == "$mmproj_sha" ]]
[[ "$(sha256sum "$image" | awk '{print $1}')" == "$image_sha" ]]

starter_state="$(sudo -n xmutil listapps 2>&1)" || {
  echo "Cannot verify starter-kit state without sudo: $starter_state" >&2
  exit 2
}
awk '$1 == "k26-starter-kits" && $NF ~ /^0,?$/ { found=1 } END { exit !found }' <<<"$starter_state" || {
  echo "starter-kit is not active; refusing CPU request" >&2
  exit 2
}
[[ "$(cat /sys/class/fpga_manager/fpga0/state)" == operating ]]
[[ "$(cat /sys/bus/platform/devices/fclk0/set_rate)" == 99999999 ]]
[[ -z "$(pgrep -x llama-mtmd-cli || true)" ]] || {
  echo "another llama-mtmd-cli is already running" >&2
  exit 2
}

umask 027
mkdir -p "$board_root/runs"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_dir="$board_root/runs/rm09-cpu-q${qid}-$stamp"
mkdir -m 0750 -- "$run_dir"
exec > >(tee -a "$run_dir/driver.log") 2>&1

snapshot() {
  local label="$1"
  echo "snapshot=$label utc=$(date -u +%FT%TZ)"
  grep -E '^(MemAvailable|CmaTotal|CmaFree|SwapFree):' /proc/meminfo || true
  echo "loadavg=$(cat /proc/loadavg)"
  echo "cpu0_scaling_cur_freq_kHz=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo UNKNOWN)"
  echo "fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
  echo "fclk0=$(cat /sys/bus/platform/devices/fclk0/set_rate 2>/dev/null || echo UNKNOWN)"
}

echo "run_dir=$run_dir"
echo "run_id=rm09-cpu-q${qid}-$stamp qid=$qid image_id=$image_id media_groups=$media_groups threads=4 batch_threads=4"
echo "host=$(hostname) utc=$(date -u +%FT%TZ) boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "cli=$cli cli_sha256=$cli_sha"
echo "model=$model model_sha256=$model_sha"
echo "mmproj=$mmproj mmproj_sha256=$mmproj_sha"
echo "image=$image image_sha256=$image_sha bytes=$(stat -c %s "$image")"
echo "expected_frozen_answer=$(printf '%q' "$expected_answer")"
snapshot before_request
echo "prompt=$(printf '%q' "$prompt")"
echo "cmd=$cli -m $model --mmproj $mmproj --image $image -p <frozen-prompt> -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4"
echo "environment=RM08_FFN_DOWN_PL unset; CPU-only flags --device none -ngl 0"
snapshot_before="$(date -u +%FT%TZ)"
echo "request_begin_utc=$snapshot_before"
set +e
env -u RM08_FFN_DOWN_PL -u RM08_PL_TRACE -u RM08_PL_EXPECTED_MEDIA_GROUPS \
  /usr/bin/time -v -o "$run_dir/time-v.txt" \
  "$(command -v timeout)" --signal=TERM --kill-after=15s "${max_seconds}s" \
  "$cli" -m "$model" --mmproj "$mmproj" --image "$image" -p "$prompt" \
  -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 \
  --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4 \
  </dev/null >"$run_dir/stdout.log" 2>"$run_dir/stderr.log"
request_rc=$?
set -e
echo "request_end_utc=$(date -u +%FT%TZ) request_exit_code=$request_rc"
snapshot after_request
answer="$(awk 'NF { sub(/\r$/, ""); last=$0 } END { print last }' "$run_dir/stdout.log")"
echo "last_nonempty_stdout_line=$(printf '%q' "$answer")"
echo "request_wall_seconds=$(sed -n 's/^\s*Elapsed (wall clock) time (h:mm:ss or m:ss): //p' "$run_dir/time-v.txt" | head -n1)"
echo "peak_rss_kib=$(sed -n 's/^\s*Maximum resident set size (kbytes): //p' "$run_dir/time-v.txt" | head -n1)"
echo "answer_matches_frozen=$([[ "$answer" == "$expected_answer" ]] && echo PASS || echo FAIL)"
echo "board_run_dir=$run_dir"
[[ "$request_rc" == 0 && "$answer" == "$expected_answer" ]]
