#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/kv260-vlm-p2-cpu
mkdir -p /tmp/rm04-tensor-capture/results
export PHASEMAP_OPTRACE_PATH=/tmp/rm04-tensor-capture/results/q37804_optrace.jsonl
export PHASEMAP_TARGET_OP_TIMING=1
export PHASEMAP_TARGET_PHASE=vision_encoder
export PHASEMAP_TARGET_OP_NAME=ffn_up-0
export PHASEMAP_TARGET_PREDECESSOR_NAME=ffn_inp_normed-0
export RM04_CAPTURE_BASE=/tmp/rm04-tensor-capture/results/q37804
export RM04_CAPTURE_ORDINAL=0
/usr/bin/timeout --verbose --signal=TERM --kill-after=10s 3600s \
  /usr/bin/time -v -o /tmp/rm04-tensor-capture/results/resource.txt \
  /tmp/rm04-tensor-capture/llama-mtmd-optrace \
  -m /home/ubuntu/kv260-vlm-p2-cpu/input/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf \
  --mmproj /home/ubuntu/kv260-vlm-p2-cpu/input/mmproj-MiniCPM-V-4.6-f16.gguf \
  --image /home/ubuntu/kv260-vlm-p2-cpu/input/textvqa-dev50/58d543df7eab2bfc.jpg \
  -p "Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what letter does these athlete's school likely begin with?\nAnswer:" \
  -t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 \
  --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4 \
  > /tmp/rm04-tensor-capture/results/stdout.log \
  2> /tmp/rm04-tensor-capture/results/stderr.log
