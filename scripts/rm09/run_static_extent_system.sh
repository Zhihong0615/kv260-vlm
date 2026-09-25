#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
base_root="${RM09_BASE_HARDWARE_ROOT:-/home/zhiro/.codex/worktrees/rm04-dynamic8-integration/kv260-vlm/vendor/kria-base-hardware}"
export RM09_REPO_ROOT="$repo_root"
export RM09_BASE_KV260_DIR="${RM09_BASE_KV260_DIR:-$base_root/k26_starter_kits/kv260}"
export RM09_STATIC_EXTENT_IP_REPO="${RM09_STATIC_EXTENT_IP_REPO:-${RM09_STATIC_EXTENT_HLS_ROOT:?set RM09_STATIC_EXTENT_HLS_ROOT}/project/solution1/impl/ip}"
export RM09_SYSTEM_ROOT="${RM09_SYSTEM_ROOT:-/tmp/rm09-static-board-system-$(date -u +%Y%m%dT%H%M%SZ)-$$}"

vivado_bin="$tool_root/Vivado/2024.2/bin/vivado"
test -x "$vivado_bin"
test -f "$RM09_BASE_KV260_DIR/scripts/config_bd.tcl"
test -f "$RM09_STATIC_EXTENT_IP_REPO/component.xml"
mkdir -p "$RM09_SYSTEM_ROOT"
echo "RM09_SYSTEM_ROOT=$RM09_SYSTEM_ROOT"
echo "RM09_STATIC_EXTENT_IP_REPO=$RM09_STATIC_EXTENT_IP_REPO"
echo "Vivado command: $vivado_bin -mode batch -source $repo_root/scripts/rm09/static_extent_system.tcl"
"$vivado_bin" -mode batch -source "$repo_root/scripts/rm09/static_extent_system.tcl" \
  -log "$RM09_SYSTEM_ROOT/vivado.log" -journal "$RM09_SYSTEM_ROOT/vivado.jou"
