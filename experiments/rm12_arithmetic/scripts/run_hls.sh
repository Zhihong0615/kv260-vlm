#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
variant="${RM12_VARIANT:?Set RM12_VARIANT to A or B}"
case "$variant" in
  A) kernel="$repo_root/experiments/rm12_arithmetic/source/kernel_a.cpp"; other_kernel="$repo_root/experiments/rm12_arithmetic/source/kernel_b.cpp"; top=fp16x32_mul_a ;;
  B) kernel="$repo_root/experiments/rm12_arithmetic/source/kernel_b.cpp"; other_kernel="$repo_root/experiments/rm12_arithmetic/source/kernel_a.cpp"; top=fp16x32_mul_b ;;
  *) echo "RM12_VARIANT must be A or B" >&2; exit 2 ;;
esac
export RM12_SOURCE="$repo_root/experiments/rm12_arithmetic/source"
export RM12_KERNEL="$kernel"
export RM12_OTHER_KERNEL="$other_kernel"
export RM12_TOP="$top"
export RM12_HLS_ROOT="${RM12_HLS_ROOT:-/tmp/rm12-arithmetic-$variant-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
mkdir -p "$RM12_HLS_ROOT"
echo "RM12_VARIANT=$variant"
echo "RM12_HLS_ROOT=$RM12_HLS_ROOT"
"$tool_root/Vitis_HLS/2024.2/bin/vitis_hls" \
  -f "$repo_root/experiments/rm12_arithmetic/scripts/run_hls.tcl" \
  -l "$RM12_HLS_ROOT/vitis_hls.log"
