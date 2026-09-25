#!/usr/bin/env bash
set -euo pipefail

mode=${1:?usage: run_q37804.sh baseline|f16x}
case "$mode" in
    baseline)
        run_env=(env -u RM09_F16X_SIM -u RM08_FFN_DOWN_PL)
        ;;
    f16x)
        run_env=(env -u RM08_FFN_DOWN_PL RM09_F16X_SIM=1)
        ;;
    *)
        echo "unknown mode: $mode" >&2
        exit 2
        ;;
esac

runtime=/home/zhiro/.codex/worktrees/rm09-p1-software/build-rm09/bin/llama-mtmd-cli
model=/home/zhiro/research/kv260-vlm/models/gguf/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf
mmproj=/home/zhiro/research/kv260-vlm/models/gguf/mmproj-MiniCPM-V-4.6-f16.gguf
image=/home/zhiro/research/kv260-vlm/datasets/textvqa_v0.5.1_dev_50_seed20260923/images/58d543df7eab2bfc.jpg
outdir=$(cd "$(dirname "$0")" && pwd)

printf '%q ' "${run_env[@]}" "$runtime" \
    -m "$model" --mmproj "$mmproj" --image "$image" \
    -p $'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what letter does these athlete\x27s school likely begin with?\nAnswer:' \
    -t 8 -tb 8 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 \
    --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4
printf '\n'

"${run_env[@]}" /usr/bin/time -v "$runtime" \
    -m "$model" --mmproj "$mmproj" --image "$image" \
    -p $'Answer the following question based only on the image. Give a short, direct answer.\nQuestion: what letter does these athlete\x27s school likely begin with?\nAnswer:' \
    -t 8 -tb 8 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 \
    --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4 \
    > "$outdir/$mode.log" 2>&1
