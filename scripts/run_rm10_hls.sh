#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
variant="${RM10_VARIANT:?Set RM10_VARIANT to 1 (A), 2 (B), or 3 (C)}"
case "$variant" in
  1) candidate="A" ;;
  2) candidate="B" ;;
  3) candidate="C" ;;
  *) echo "RM10_VARIANT must be 1, 2, or 3" >&2; exit 2 ;;
esac

export RM10_SOURCE="${RM10_SOURCE:-$repo_root/experiments/rm10_hls/source}"
export RM10_HLS_ROOT="${RM10_HLS_ROOT:-/tmp/rm10-${candidate}-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
mkdir -p "$RM10_HLS_ROOT"
echo "RM10_VARIANT=$candidate"
echo "RM10_HLS_ROOT=$RM10_HLS_ROOT"
"$tool_root/Vitis_HLS/2024.2/bin/vitis_hls" \
  -f "$repo_root/scripts/run_rm10_hls.tcl" \
  -l "$RM10_HLS_ROOT/vitis_hls.log"
