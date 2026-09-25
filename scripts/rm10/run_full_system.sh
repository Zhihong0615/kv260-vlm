#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
base_root="${RM10_BASE_HARDWARE_ROOT:-/home/zhiro/.codex/worktrees/rm04-dynamic8-integration/kv260-vlm/vendor/kria-base-hardware}"
export RM10_REPO_ROOT="$repo_root"
export RM10_BASE_KV260_DIR="${RM10_BASE_KV260_DIR:-$base_root/k26_starter_kits/kv260}"
export RM10_IP_REPO="${RM10_IP_REPO:?set RM10_IP_REPO to the frozen RM10 HLS exported IP repository}"
export RM10_SYSTEM_ROOT="${RM10_SYSTEM_ROOT:-$repo_root/experiments/rm10_route/build/full_system}"
export RM10_EVIDENCE_ROOT="${RM10_EVIDENCE_ROOT:-$repo_root/experiments/rm10_route/evidence/full_system}"

vivado_bin="$tool_root/Vivado/2024.2/bin/vivado"
test -x "$vivado_bin"
test -f "$RM10_BASE_KV260_DIR/scripts/config_bd.tcl"
test -f "$RM10_IP_REPO/component.xml"
mkdir -p "$RM10_SYSTEM_ROOT"
mkdir -p "$RM10_EVIDENCE_ROOT"
printf 'RM10_SYSTEM_ROOT=%s\nRM10_IP_REPO=%s\n' "$RM10_SYSTEM_ROOT" "$RM10_IP_REPO"
find "$RM10_IP_REPO" -type f -print0 | sort -z | xargs -0 sha256sum > "$RM10_EVIDENCE_ROOT/frozen_ip_sha256.txt"
sha256sum "$RM10_IP_REPO/component.xml" | tee "$RM10_SYSTEM_ROOT/ip_component.sha256"
set +e
"$vivado_bin" -mode batch -source "$repo_root/scripts/rm10/full_system.tcl" \
  -log "$RM10_SYSTEM_ROOT/vivado.log" -journal "$RM10_SYSTEM_ROOT/vivado.jou"
vivado_status=$?
set -e

for report in timing_post_route_setup.rpt timing_post_route_hold.rpt \
  critical_paths_post_route.rpt utilization_post_route.rpt \
  clock_utilization_post_route.rpt route_status.rpt drc_post_route.rpt \
  methodology_post_route.rpt congestion_post_route.rpt; do
  if [[ -f "$RM10_SYSTEM_ROOT/$report" ]]; then
    cp "$RM10_SYSTEM_ROOT/$report" "$RM10_EVIDENCE_ROOT/$report"
  fi
done
if [[ -f "$RM10_SYSTEM_ROOT/vivado.log" ]]; then
  cp "$RM10_SYSTEM_ROOT/vivado.log" "$RM10_EVIDENCE_ROOT/vivado_log.txt"
fi
if (( vivado_status != 0 )); then
  printf 'Vivado failed with status %s; partial logs/reports retained under %s\n' \
    "$vivado_status" "$RM10_EVIDENCE_ROOT" >&2
  exit "$vivado_status"
fi

project_name=kv260_rm10_recurrence_decoupled
bit_file="$RM10_SYSTEM_ROOT/${project_name}.runs/impl_1/${project_name}_wrapper.bit"
xsa_file="$RM10_SYSTEM_ROOT/${project_name}.xsa"
test -f "$bit_file"
test -f "$xsa_file"
sha256sum "$bit_file" "$xsa_file" > "$RM10_EVIDENCE_ROOT/package_sha256.txt"
printf 'bitstream=%s\nxsa=%s\n' "$bit_file" "$xsa_file" \
  > "$RM10_EVIDENCE_ROOT/package_paths.txt"
printf 'Vivado completed; result artifacts and reports are under %s\n' "$RM10_EVIDENCE_ROOT"
