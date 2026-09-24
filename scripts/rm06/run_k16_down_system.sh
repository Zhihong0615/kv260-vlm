#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
export RM06_REPO_ROOT="$repo_root"
export RM06_K16_HLS_ROOT="${RM06_K16_HLS_ROOT:-$repo_root/experiments/rm06/reports/k16_ffn_down}"
export RM06_SYSTEM_ROOT="${RM06_SYSTEM_ROOT:-$repo_root/experiments/rm06/build/k16_down_system}"
mkdir -p "$RM06_SYSTEM_ROOT"
"$tool_root/Vivado/2024.2/bin/vivado" \
  -mode batch -source "$repo_root/scripts/rm06/run_k16_down_system.tcl" \
  -log "$RM06_SYSTEM_ROOT/vivado.log" -journal "$RM06_SYSTEM_ROOT/vivado.jou"
