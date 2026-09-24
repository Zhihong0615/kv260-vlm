#!/usr/bin/env bash
set -euo pipefail

stage_root="${RM06_BOARD_ROOT:-/home/ubuntu/kv260-vlm-p2-cpu}"
run_root="${RM06_RUN_ROOT:-/tmp/rm06-ffn-down-capture-sync}"
mkdir -p "$run_root/results"

export PHASEMAP_OPTRACE_PATH="$run_root/results/q37804_optrace.jsonl"
export RM06_CAPTURE_DIR="$run_root/results/tensors"
export RM06_CAPTURE_NAMES="ffn_down-0,ffn_down-13,ffn_down-26"
mkdir -p "$RM06_CAPTURE_DIR"
unset PHASEMAP_TARGET_OP_TIMING PHASEMAP_TARGET_OP_PREFIXES

/usr/bin/timeout --verbose --signal=TERM --kill-after=10s 3600s \
  /usr/bin/time -v -o "$run_root/results/resource.txt" \
  "$run_root/llama-mtmd-optrace" \
  -m "$stage_root/input/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf" \
  --mmproj "$stage_root/input/mmproj-MiniCPM-V-4.6-f16.gguf" \
  --image "$stage_root/input/textvqa-dev50/58d543df7eab2bfc.jpg" \
  -p "Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what letter does these athlete's school likely begin with?\nAnswer:" \
  -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 \
  --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4 \
  > "$run_root/results/stdout.log" \
  2> "$run_root/results/stderr.log"
