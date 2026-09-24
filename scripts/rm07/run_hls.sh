#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
export RM07_HLS_SOURCE="$repo_root/experiments/rm07/source/bounded_k16"
export RM07_HLS_ROOT="${RM07_HLS_ROOT:-$repo_root/experiments/rm07/reports/bounded_k16_hls}"
mkdir -p "$RM07_HLS_ROOT"
"$tool_root/Vitis_HLS/2024.2/bin/vitis_hls" \
  -f "$repo_root/scripts/rm07/hls.tcl" \
  -l "$RM07_HLS_ROOT/vitis_hls.log"
