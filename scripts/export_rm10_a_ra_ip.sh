#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
export RM10_HLS_PROJECT="${RM10_HLS_PROJECT:-/tmp/rm10-a-ra-fixed4-20260926T000000Z/project}"
export RM10_IP_OUTPUT="${RM10_IP_OUTPUT:-$repo_root/experiments/rm10_a_resource_aware/artifacts/ip}"
mkdir -p "$RM10_IP_OUTPUT"
"$tool_root/Vitis_HLS/2024.2/bin/vitis_hls" \
  -f "$repo_root/scripts/export_rm10_a_ra_ip.tcl" \
  -l "$RM10_IP_OUTPUT/export.log"
