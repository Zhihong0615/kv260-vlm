#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
tensor_dir="${1:?Usage: run_real_tensor_probe.sh TENSOR_DIR}"
build_dir="${RM12_HOST_BUILD_DIR:-/tmp/rm12-real-tensor-probe}"
mkdir -p "$build_dir"
g++ -std=c++17 -O2 -ffp-contract=off -fno-fast-math \
  -I"$repo_root/experiments/rm12_arithmetic/source" \
  -I"$tool_root/Vitis/2024.2/include" \
  "$repo_root/experiments/rm12_arithmetic/source/real_tensor_probe.cpp" \
  "$repo_root/experiments/rm12_arithmetic/source/kernel_a.cpp" \
  "$repo_root/experiments/rm12_arithmetic/source/kernel_b.cpp" \
  -o "$build_dir/real_tensor_probe"
"$build_dir/real_tensor_probe" "$tensor_dir"
