#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
base_root="${RM13_BASE_HARDWARE_ROOT:-/home/zhiro/.codex/worktrees/rm04-dynamic8-integration/kv260-vlm/vendor/kria-base-hardware}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
source_sha="$(git rev-parse HEAD)"
run_root="${RM13_ROUTE_RUN_ROOT:-/tmp/rm13-w4a8-down-route-${timestamp}-${source_sha:0:8}}"
ip_repo="${RM13_IP_REPO:-$run_root/ip_repo}"
system_root="${RM13_SYSTEM_ROOT:-$run_root/full_system}"
evidence_root="${RM13_EVIDENCE_ROOT:-$repo_root/experiments/rm13/hardware/evidence/route-${timestamp}-${source_sha:0:8}}"
hls_project="${RM13_HLS_PROJECT:?set RM13_HLS_PROJECT to the frozen no-debug K=4304 PE8x16 HLS project}"

vivado_bin="$tool_root/Vivado/2024.2/bin/vivado"
vitis_hls_bin="$tool_root/Vitis_HLS/2024.2/bin/vitis_hls"
base_kv260_dir="${RM13_BASE_KV260_DIR:-$base_root/k26_starter_kits/kv260}"
test -x "$vivado_bin"
test -x "$vitis_hls_bin"
test -f "$base_kv260_dir/scripts/config_bd.tcl"
test -f "$hls_project/solution1/syn/report/rm13_w4a8_tile_csynth.rpt"
git diff --quiet HEAD -- experiments/rm13/hardware scripts/rm13 || {
  echo "RM13 source changed after commit; freeze it before routing" >&2
  exit 2
}

mkdir -p "$ip_repo" "$system_root" "$evidence_root"
export RM13_HLS_PROJECT="$hls_project"
export RM13_IP_OUTPUT="$ip_repo"
"$vitis_hls_bin" -f "$repo_root/scripts/rm13/export_ip.tcl" \
  -l "$run_root/export_ip.log"
for bundle in w ws x y; do
  if ! rg -q "m_axi_gmem_${bundle}" "$ip_repo/component.xml"; then
    echo "exported RM13 IP is missing m_axi_gmem_${bundle}" >&2
    exit 2
  fi
done
find "$ip_repo" -type f -print0 | sort -z | xargs -0 sha256sum \
  > "$evidence_root/ip_sha256.txt"
cp "$run_root/export_ip.log" "$evidence_root/export_ip.log"
cp "$hls_project/solution1/syn/report/rm13_w4a8_tile_csynth.rpt" \
  "$evidence_root/hls_csynth.rpt"

cat > "$evidence_root/route_run.txt" <<EOF
source_sha=$source_sha
source_branch=$(git branch --show-current)
hls_project=$hls_project
ip_repo=$ip_repo
system_root=$system_root
base_kv260_dir=$base_kv260_dir
target_clock_mhz=100
compiled_K=4304
compiled_tile_M=16
compiled_tile_N=16
integer_MAC_per_cycle=128
debug_outputs=0
board_load=not_performed
EOF
sha256sum "$ip_repo/component.xml" | tee "$system_root/ip_component.sha256"

export RM13_REPO_ROOT="$repo_root"
export RM13_BASE_KV260_DIR="$base_kv260_dir"
export RM13_IP_REPO="$ip_repo"
export RM13_SYSTEM_ROOT="$system_root"
set +e
"$vivado_bin" -mode batch -source "$repo_root/scripts/rm13/full_system.tcl" \
  -log "$system_root/vivado.log" -journal "$system_root/vivado.jou"
vivado_status=$?
set -e

for report in timing_post_route_setup.rpt timing_post_route_hold.rpt critical_paths_post_route.rpt \
  utilization_post_route.rpt clock_utilization_post_route.rpt route_status.rpt drc_post_route.rpt \
  methodology_post_route.rpt congestion_post_route.rpt; do
  [[ ! -f "$system_root/$report" ]] || cp "$system_root/$report" "$evidence_root/$report"
done
[[ ! -f "$system_root/vivado.log" ]] || cp "$system_root/vivado.log" "$evidence_root/vivado_log.txt"
if (( vivado_status != 0 )); then
  echo "Vivado failed status=$vivado_status; partial evidence at $evidence_root" >&2
  exit "$vivado_status"
fi

bit_file="$system_root/kv260_rm13_w4a8_down.runs/impl_1/kv260_rm13_w4a8_down_wrapper.bit"
xsa_file="$system_root/kv260_rm13_w4a8_down.xsa"
test -f "$bit_file" && test -f "$xsa_file"
sha256sum "$bit_file" "$xsa_file" > "$evidence_root/package_sha256.txt"
printf 'bitstream=%s\nxsa=%s\n' "$bit_file" "$xsa_file" \
  > "$evidence_root/package_paths.txt"
printf 'Vivado route completed; artifacts remain offline under %s\n' "$evidence_root"
