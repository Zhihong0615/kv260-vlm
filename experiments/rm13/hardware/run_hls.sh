#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
export RM13_SOURCE="$script_dir"
export RM13_K="${RM13_K:-4304}"
export RM13_DO_SYNTH="${RM13_DO_SYNTH:-0}"
export RM13_DO_CSIM="${RM13_DO_CSIM:-1}"
export RM13_DO_COSIM="${RM13_DO_COSIM:-0}"
export RM13_DEBUG_OUTPUTS="${RM13_DEBUG_OUTPUTS:-1}"
export RM13_TILE_M="${RM13_TILE_M:-16}"
export RM13_TILE_N="${RM13_TILE_N:-4}"
export RM13_PROCESSING_M="${RM13_PROCESSING_M:-4}"
export RM13_PROCESSING_N="${RM13_PROCESSING_N:-4}"
export RM13_HLS_ROOT="${RM13_HLS_ROOT:-/tmp/rm13-w4a8-k${RM13_K}-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
mkdir -p "$RM13_HLS_ROOT"
printf 'RM13_K=%s\nRM13_TILE_M=%s\nRM13_TILE_N=%s\nRM13_PROCESSING_M=%s\nRM13_PROCESSING_N=%s\nRM13_DO_CSIM=%s\nRM13_DO_SYNTH=%s\nRM13_DO_COSIM=%s\nRM13_DEBUG_OUTPUTS=%s\nRM13_HLS_ROOT=%s\n' \
  "$RM13_K" "$RM13_TILE_M" "$RM13_TILE_N" "$RM13_PROCESSING_M" "$RM13_PROCESSING_N" \
  "$RM13_DO_CSIM" "$RM13_DO_SYNTH" "$RM13_DO_COSIM" "$RM13_DEBUG_OUTPUTS" "$RM13_HLS_ROOT"
"$tool_root/Vitis_HLS/2024.2/bin/vitis_hls" \
  -f "$script_dir/run_hls.tcl" -l "$RM13_HLS_ROOT/vitis_hls.log"
printf 'RM13_HLS_LOG=%s\n' "$RM13_HLS_ROOT/vitis_hls.log"
