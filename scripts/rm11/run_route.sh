#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
base_root="${RM11_BASE_HARDWARE_ROOT:-/home/zhiro/.codex/worktrees/rm04-dynamic8-integration/kv260-vlm/vendor/kria-base-hardware}"
export RM11_REPO_ROOT="$repo_root"
export RM11_BASE_KV260_DIR="${RM11_BASE_KV260_DIR:-$base_root/k26_starter_kits/kv260}"
export RM11_IP_REPO="${RM11_IP_REPO:?set RM11_IP_REPO to the exported RM11 IP package directory}"
export RM11_SYSTEM_ROOT="${RM11_SYSTEM_ROOT:-$repo_root/experiments/rm11_unified_ffn/build/full_system}"
export RM11_EVIDENCE_ROOT="${RM11_EVIDENCE_ROOT:-$repo_root/experiments/rm11_unified_ffn/evidence/full_system}"

vivado_bin="$tool_root/Vivado/2024.2/bin/vivado"
test -x "$vivado_bin"
test -f "$RM11_BASE_KV260_DIR/scripts/config_bd.tcl"
test -f "$RM11_IP_REPO/component.xml"
mkdir -p "$RM11_SYSTEM_ROOT" "$RM11_EVIDENCE_ROOT"
find "$RM11_IP_REPO" -type f -print0 | sort -z | xargs -0 sha256sum > "$RM11_EVIDENCE_ROOT/ip_sha256.txt"
sha256sum "$RM11_IP_REPO/component.xml" | tee "$RM11_SYSTEM_ROOT/ip_component.sha256"

set +e
"$vivado_bin" -mode batch -source "$repo_root/scripts/rm11/full_system.tcl" \
  -log "$RM11_SYSTEM_ROOT/vivado.log" -journal "$RM11_SYSTEM_ROOT/vivado.jou"
vivado_status=$?
set -e

for report in timing_post_route_setup.rpt timing_post_route_hold.rpt critical_paths_post_route.rpt \
  utilization_post_route.rpt clock_utilization_post_route.rpt route_status.rpt drc_post_route.rpt \
  methodology_post_route.rpt congestion_post_route.rpt; do
  [[ ! -f "$RM11_SYSTEM_ROOT/$report" ]] || cp "$RM11_SYSTEM_ROOT/$report" "$RM11_EVIDENCE_ROOT/$report"
done
[[ ! -f "$RM11_SYSTEM_ROOT/vivado.log" ]] || cp "$RM11_SYSTEM_ROOT/vivado.log" "$RM11_EVIDENCE_ROOT/vivado_log.txt"
if (( vivado_status != 0 )); then
  echo "Vivado failed status=$vivado_status; partial outputs retained under $RM11_EVIDENCE_ROOT" >&2
  exit "$vivado_status"
fi

project_name=kv260_rm11_unified_ffn
bit_file="$RM11_SYSTEM_ROOT/${project_name}.runs/impl_1/${project_name}_wrapper.bit"
xsa_file="$RM11_SYSTEM_ROOT/${project_name}.xsa"
test -f "$bit_file" && test -f "$xsa_file"
sha256sum "$bit_file" "$xsa_file" > "$RM11_EVIDENCE_ROOT/package_sha256.txt"
printf 'bitstream=%s\nxsa=%s\n' "$bit_file" "$xsa_file" > "$RM11_EVIDENCE_ROOT/package_paths.txt"
echo "Vivado route completed; package paths and reports are under $RM11_EVIDENCE_ROOT"
