#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ $# -ne 2 ]]; then
  echo "usage: $0 TENSOR_DIR OUTPUT_CSV" >&2
  exit 2
fi
tensor_dir="$1"
output_csv="$2"
mkdir -p "$(dirname "$output_csv")"
compiler="${CXX:-g++}"
build_dir="${TMPDIR:-/tmp}/rm09-precision"
mkdir -p "$build_dir"
binary="$build_dir/precision_probe"
"$compiler" -std=c++17 -O3 -march=native -ffp-contract=off -fopenmp \
  "$repo_root/experiments/rm09_precision/precision_probe.cpp" -o "$binary"
OMP_NUM_THREADS="${OMP_NUM_THREADS:-24}" "$binary" "$tensor_dir" >"$output_csv"
