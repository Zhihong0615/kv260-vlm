#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
export RM09_STATIC_EXTENT_SOURCE="$repo_root/experiments/rm09_static_extent/source"
if [[ -z "${RM09_STATIC_EXTENT_HLS_ROOT:-}" ]]; then
  export RM09_STATIC_EXTENT_HLS_ROOT="/tmp/rm09-static-extent-$(date -u +%Y%m%dT%H%M%SZ)-$$"
fi
mkdir -p "$RM09_STATIC_EXTENT_HLS_ROOT"
echo "RM09_STATIC_EXTENT_HLS_ROOT=$RM09_STATIC_EXTENT_HLS_ROOT"
"$tool_root/Vitis_HLS/2024.2/bin/vitis_hls" \
  -f "$repo_root/scripts/rm09/static_extent_hls.tcl" \
  -l "$RM09_STATIC_EXTENT_HLS_ROOT/vitis_hls.log"
