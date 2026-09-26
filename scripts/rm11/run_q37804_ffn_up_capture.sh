#!/usr/bin/env bash
set -euo pipefail

stage_root="${RM11_BOARD_ROOT:-/home/ubuntu/kv260-vlm-p2-cpu}"
run_root="${RM11_RUN_ROOT:-/tmp/rm11-ffn-up-capture}"
result_root="$run_root/results"
mkdir -p "$result_root/tensors"

cli="$run_root/llama-mtmd-optrace"
[[ -x "$cli" ]] || { echo "missing executable: $cli" >&2; exit 2; }
model_path="${RM11_MODEL_PATH:-$stage_root/input/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf}"
mmproj_path="${RM11_MMPROJ_PATH:-$stage_root/input/mmproj-MiniCPM-V-4.6-f16.gguf}"
image_path="${RM11_IMAGE_PATH:-$stage_root/input/textvqa-dev50/58d543df7eab2bfc.jpg}"
[[ -s "$model_path" && -s "$mmproj_path" && -s "$image_path" ]] || {
  echo "model/mmproj/image input missing or empty" >&2
  exit 2
}

sha256sum -- "$model_path" "$mmproj_path" "$image_path" > "$result_root/input_sha256sums.txt"

export PHASEMAP_OPTRACE_PATH="$result_root/q37804_optrace.jsonl"
export RM11_CAPTURE_DIR="$result_root/tensors"
export RM11_CAPTURE_NAMES="ffn_up-0,ffn_up-13,ffn_up-26"
unset PHASEMAP_TARGET_OP_TIMING PHASEMAP_TARGET_OP_PREFIXES

/usr/bin/timeout --verbose --signal=TERM --kill-after=10s 3600s \
  /usr/bin/time -v -o "$result_root/resource.txt" \
  "$cli" \
  -m "$model_path" \
  --mmproj "$mmproj_path" \
  --image "$image_path" \
  -p "Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what letter does these athlete's school likely begin with?\nAnswer:" \
  -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 \
  --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4 \
  > "$result_root/stdout.log" \
  2> "$result_root/stderr.log"

for layer in 0 13 26; do
  for suffix in weight.f16 activation.f32 output.f32; do
    file="$result_root/tensors/ffn_up-$layer.$suffix"
    [[ -s "$file" ]] || { echo "missing capture: $file" >&2; exit 3; }
  done
done
[[ "$(grep -c '^RM11_TENSOR_CAPTURE_DONE name=ffn_up-' "$result_root/stderr.log")" -eq 3 ]] || {
  echo "expected exactly three completed FFN-up captures" >&2
  exit 4
}

(
  cd "$run_root"
  sha256sum build.json results/input_sha256sums.txt results/stdout.log results/stderr.log results/resource.txt \
    results/q37804_optrace.jsonl results/tensors/* > results/SHA256SUMS
)
echo "capture_complete=PASS result_root=$result_root"
