#!/usr/bin/env bash
set -euo pipefail

bin=/tmp/rm09-f16x/bin
model=/home/ubuntu/kv260-vlm-p2-cpu/input/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf
mmproj=/home/ubuntu/kv260-vlm-p2-cpu/input/mmproj-MiniCPM-V-4.6-f16.gguf
image=/home/ubuntu/kv260-vlm-p2-cpu/input/textvqa-dev50/58d543df7eab2bfc.jpg
run_root=/home/ubuntu/kv260-vlm-p2-cpu/runs
stamp=$(date -u +%Y%m%dT%H%M%SZ)
run_dir="$run_root/rm09-q37804-p0-p1-$stamp"

check_sha() {
    local expected=$1 path=$2 actual
    actual=$(sha256sum "$path" | awk '{print $1}')
    if [[ "$actual" != "$expected" ]]; then
        echo "SHA-256 mismatch: $path expected=$expected actual=$actual" >&2
        exit 1
    fi
}

check_sha 9da96349e42cc9ee3d8ee25fe2d98795bf87905cbc538a1bc9710cdc284f4317 "$bin/llama-mtmd-cli"
check_sha c7c1348ce81369d20d6fadba2ec0b296e3458ce9853a176c5baaffa0c8f20f53 "$bin/libggml-base.so.0.24.0"
check_sha ca9eb48e96d5c57b92b4910a0e599ba61aeb88fb4cb2b7c10096a1a8e2e22619 "$bin/libggml-cpu.so.0.24.0"
check_sha 98d5ece92590e605b3045332a860f795ff6f6ea5dfb394a78105be314e4f1e74 "$bin/libggml.so.0.24.0"
check_sha 36c40242a061fcfdb3e50f508e707d9a8e568328c792201df14522dce8e85a18 "$bin/libllama-common.so.0.4.1"
check_sha a133474fb4f35e02674b569f86515b2ec1efb2c0eda584e00fcf5fcc71553160 "$bin/libllama.so.0.4.1"
check_sha 355739b8e578f66acf32a4d4f55de92c6d1c90b379f4911cd5333d69a7652d7f "$bin/libmtmd.so.0.4.1"
check_sha 8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773 "$model"
check_sha ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293 "$mmproj"
check_sha 3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f "$image"

mkdir -m 0755 -- "$run_dir"
meta="$run_dir/run_meta.txt"
prompt=$'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what letter does these athlete\x27s school likely begin with?\nAnswer:'
args=(
    -m "$model" --mmproj "$mmproj" --image "$image" -p "$prompt"
    -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0
    --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4
)

snapshot() {
    echo "snapshot=$1 utc=$(date -u +%FT%TZ)"
    grep -E '^(MemAvailable|CmaTotal|CmaFree):' /proc/meminfo || true
    echo "cpu0_scaling_cur_freq_kHz=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo UNKNOWN)"
    echo "fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
}

{
    echo "run_dir=$run_dir"
    echo "host=$(hostname) boot_id=$(cat /proc/sys/kernel/random/boot_id)"
    echo "cli_sha256=$(sha256sum "$bin/llama-mtmd-cli" | awk '{print $1}')"
    echo "model_sha256=$(sha256sum "$model" | awk '{print $1}')"
    echo "mmproj_sha256=$(sha256sum "$mmproj" | awk '{print $1}')"
    echo "image_sha256=$(sha256sum "$image" | awk '{print $1}')"
    snapshot before_p0
} > "$meta"

run_case() {
    local mode=$1 log="$run_dir/$1.log" rc
    echo "run_begin mode=$mode utc=$(date -u +%FT%TZ)" >> "$meta"
    if [[ "$mode" == p0 ]]; then
        if env -u RM09_F16X_SIM -u RM08_FFN_DOWN_PL LD_LIBRARY_PATH="$bin" \
            /usr/bin/time -v /usr/bin/timeout --signal=TERM --kill-after=10s 1200s \
            "$bin/llama-mtmd-cli" "${args[@]}" > "$log" 2>&1; then
            rc=0
        else
            rc=$?
        fi
    else
        if env -u RM08_FFN_DOWN_PL RM09_F16X_SIM=1 LD_LIBRARY_PATH="$bin" \
            /usr/bin/time -v /usr/bin/timeout --signal=TERM --kill-after=10s 1200s \
            "$bin/llama-mtmd-cli" "${args[@]}" > "$log" 2>&1; then
            rc=0
        else
            rc=$?
        fi
    fi
    echo "run_end mode=$mode exit=$rc utc=$(date -u +%FT%TZ) log=$log" >> "$meta"
    snapshot "after_$mode" >> "$meta"
    [[ "$rc" -eq 0 ]] || { echo "$mode request failed; see $log" >&2; exit "$rc"; }
}

run_case p0
run_case p1

if grep -q '^RM09_F16X_APPLIED ' "$run_dir/p0.log"; then
    echo "P0 control unexpectedly contains F16X markers" >&2
    exit 1
fi

trace_count=$(grep -c '^RM09_F16X_APPLIED ' "$run_dir/p1.log" || true)
[[ "$trace_count" -eq 135 ]] || { echo "expected 135 P1 markers, got $trace_count" >&2; exit 1; }
for layer in $(seq 0 26); do
    layer_count=$(grep -c "^RM09_F16X_APPLIED layer=$layer " "$run_dir/p1.log" || true)
    [[ "$layer_count" -eq 5 ]] || { echo "layer $layer expected 5 P1 markers, got $layer_count" >&2; exit 1; }
done

echo "P1 trace validated: 135 calls, five per numbered layer." | tee -a "$meta"
echo "P0 log: $run_dir/p0.log"
echo "P1 log: $run_dir/p1.log"
echo "Run metadata: $meta"
