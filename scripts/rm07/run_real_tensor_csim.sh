#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
tensor_root="${RM07_TENSOR_ROOT:-$repo_root/experiments/rm04_system/local_tensors/rm06_ffn_down/q37804}"
report_root="${RM07_REAL_CSIM_ROOT:-$repo_root/experiments/rm07/reports/real_tensor_csim}"
source_dir="$repo_root/experiments/rm07/source/bounded_k16"
mkdir -p "$report_root"

run_one() {
  local layer="$1" n="$2" root
  root="$report_root/$layer"
  mkdir -p "$root"
  export RM07_CSIM_SOURCE="$source_dir"
  export RM07_CSIM_ROOT="$root"
  export RM07_WEIGHT="$tensor_root/$layer.weight.f16"
  export RM07_ACTIVATION="$tensor_root/$layer.activation.f32"
  export RM07_CPU_OUTPUT="$tensor_root/$layer.output.f32"
  export RM07_LAYER="$layer"
  export RM07_ACTIVE_N="$n"
  "$tool_root/Vitis_HLS/2024.2/bin/vitis_hls" \
    -f "$repo_root/scripts/rm07/real_tensor_csim.tcl" \
    -l "$root/vitis_hls.log"
}

case "${RM07_ONLY_LAYER:-all}" in
  ffn_down-0) run_one ffn_down-0 1120 ;;
  ffn_down-13) run_one ffn_down-13 280 ;;
  ffn_down-26) run_one ffn_down-26 280 ;;
  all)
    run_one ffn_down-0 1120
    run_one ffn_down-13 280
    run_one ffn_down-26 280
    ;;
  *) echo "unknown RM07_ONLY_LAYER=${RM07_ONLY_LAYER}" >&2; exit 2 ;;
esac
