#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
export RM11_SOURCE="${RM11_SOURCE:-$repo_root/experiments/rm11_unified_ffn/source}"
export RM11_HLS_ROOT="${RM11_HLS_ROOT:-/tmp/rm11-unified-hls}"
mkdir -p "$RM11_HLS_ROOT"
echo "RM11_SOURCE=$RM11_SOURCE"
echo "RM11_HLS_ROOT=$RM11_HLS_ROOT"
"$tool_root/Vitis_HLS/2024.2/bin/vitis_hls" \
  -f "$repo_root/scripts/rm11/run_unified_hls.tcl" \
  -l "$RM11_HLS_ROOT/vitis_hls.log"
