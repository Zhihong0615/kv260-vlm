#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
export RM07_REPO_ROOT="$repo_root"
export RM07_HLS_ROOT="${RM07_HLS_ROOT:-$repo_root/experiments/rm07/reports/bounded_k16_hls}"
export RM07_SYSTEM_ROOT="${RM07_SYSTEM_ROOT:-$repo_root/experiments/rm07/build/bounded_k16_system}"
mkdir -p "$RM07_SYSTEM_ROOT"
"$tool_root/Vivado/2024.2/bin/vivado" \
  -mode batch -source "$repo_root/scripts/rm07/run_system.tcl" \
  -log "$RM07_SYSTEM_ROOT/vivado.log" -journal "$RM07_SYSTEM_ROOT/vivado.jou"
