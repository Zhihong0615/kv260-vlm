#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
export RM10_SOURCE="${RM10_SOURCE:-$repo_root/experiments/rm10_a_resource_aware/source}"
export RM10_HLS_ROOT="${RM10_HLS_ROOT:-/tmp/rm10-a-ra-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
mkdir -p "$RM10_HLS_ROOT"
echo "RM10_HLS_ROOT=$RM10_HLS_ROOT"
"$tool_root/Vitis_HLS/2024.2/bin/vitis_hls" \
  -f "$repo_root/scripts/run_rm10_a_ra.tcl" \
  -l "$RM10_HLS_ROOT/vitis_hls.log"
