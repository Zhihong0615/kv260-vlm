#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: run_numeric_probe_a_ra.sh TENSOR_DIR OUTPUT_DIR" >&2
  exit 2
fi
source_dir="$(cd "$(dirname "$0")" && pwd)"
tensor_dir="$1"
output_dir="$2"
mkdir -p "$output_dir"
g++ -std=c++17 -O3 -fno-fast-math -ffp-contract=off -fopenmp \
  "$source_dir/reduction_probe_a_ra.cpp" -o "$output_dir/reduction_probe_a_ra"
"$output_dir/reduction_probe_a_ra" "$tensor_dir" "$output_dir" 2> "$output_dir/run.log"
