#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
tensor_root="${RM06_TENSOR_ROOT:-$repo_root/experiments/rm04_system/local_tensors/rm06_ffn_down/q37804}"
report_root="${RM06_REAL_CSIM_ROOT:-$repo_root/experiments/rm06/reports/real_tensor_csim}"
base_source="$repo_root/experiments/rm06/source/k16_down"
mkdir -p "$report_root"

run_one() {
  local layer="$1" n="$2" source_dir root
  source_dir="$base_source"
  root="$report_root/$layer"
  mkdir -p "$root"
  if [[ "$n" == 280 ]]; then
    source_dir="$report_root/source_n280"
    mkdir -p "$source_dir"
    cp "$base_source/vision_gemm.cpp" "$base_source/tb_real_tensor_multitile.cpp" "$source_dir/"
    python3 - "$base_source/vision_gemm.hpp" "$source_dir/vision_gemm.hpp" <<'PY'
from pathlib import Path
import sys
src, dst = map(Path, sys.argv[1:])
s = src.read_text()
old = "static constexpr int VLM_N = 1120;   // image-token rows; other layers use N=280"
new = "static constexpr int VLM_N = 280;    // real middle/late FFN-down token extent"
if s.count(old) != 1:
    raise SystemExit("N=1120 source anchor not unique")
dst.write_text(s.replace(old, new))
PY
  fi
  export RM06_CSIM_SOURCE="$source_dir"
  export RM06_CSIM_ROOT="$root"
  export RM06_WEIGHT="$tensor_root/$layer.weight.f16"
  export RM06_ACTIVATION="$tensor_root/$layer.activation.f32"
  export RM06_CPU_OUTPUT="$tensor_root/$layer.output.f32"
  export RM06_LAYER="$layer"
  "$tool_root/Vitis_HLS/2024.2/bin/vitis_hls" \
    -f "$repo_root/scripts/rm06/run_k16_real_tensor_csim.tcl" \
    -l "$root/vitis_hls.log"
}

if [[ -n "${RM06_ONLY_LAYER:-}" ]]; then
  case "$RM06_ONLY_LAYER" in
    ffn_down-0) run_one ffn_down-0 1120 ;;
    ffn_down-13|ffn_down-26) run_one "$RM06_ONLY_LAYER" 280 ;;
    *) echo "unknown RM06_ONLY_LAYER=$RM06_ONLY_LAYER" >&2; exit 2 ;;
  esac
else
  run_one ffn_down-0 1120
  run_one ffn_down-13 280
  run_one ffn_down-26 280
fi
