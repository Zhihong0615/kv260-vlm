#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
export RM06_K16_SOURCE="$repo_root/experiments/rm06/source/k16_down"
export RM06_K16_HLS_ROOT="${RM06_K16_HLS_ROOT:-$repo_root/experiments/rm06/reports/k16_ffn_down}"
mkdir -p "$RM06_K16_HLS_ROOT"
"$tool_root/Vitis_HLS/2024.2/bin/vitis_hls" \
  -f "$repo_root/scripts/rm06/run_k16_down_hls.tcl" \
  -l "$RM06_K16_HLS_ROOT/vitis_hls.log"
