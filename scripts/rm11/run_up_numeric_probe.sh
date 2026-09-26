#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: run_up_numeric_probe.sh TENSOR_DIR OUTPUT_DIR" >&2
  exit 2
fi
repo_root="$(git rev-parse --show-toplevel)"
source_dir="$repo_root/experiments/rm11_unified_ffn/source"
tensor_dir="$1"
output_dir="$2"
mkdir -p "$output_dir"
g++ -std=c++17 -O3 -fno-fast-math -ffp-contract=off -fopenmp \
  "$source_dir/up_numeric_probe.cpp" -o "$output_dir/up_numeric_probe"
OMP_NUM_THREADS="${OMP_NUM_THREADS:-16}" \
  "$output_dir/up_numeric_probe" "$tensor_dir" "$output_dir" \
  2> "$output_dir/run.log"
cat "$output_dir/run.log"
