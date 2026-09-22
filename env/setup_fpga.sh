#!/usr/bin/env bash
# Source this file for FPGA work; it intentionally does not modify ~/.bashrc.

_fpga_project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

_fpga_settings="${FPGA_SETTINGS64:-}"
if [[ -z "$_fpga_settings" ]]; then
  for _candidate in \
    "$_fpga_project_root/tools/Xilinx/Vitis/2024.2/settings64.sh" \
    "$_fpga_project_root/tools/Xilinx/Vivado/2024.2/settings64.sh" \
    /tools/Xilinx/Vivado/2024.2/settings64.sh \
    /tools/Xilinx/Vitis/2024.2/settings64.sh \
    /opt/Xilinx/Vivado/2024.2/settings64.sh \
    /opt/Xilinx/Vitis/2024.2/settings64.sh; do
    if [[ -f "$_candidate" ]]; then
      _fpga_settings="$_candidate"
      break
    fi
  done
fi

if [[ -z "$_fpga_settings" || ! -f "$_fpga_settings" ]]; then
  echo "BLOCKED: Vivado/Vitis 2024.2 settings64.sh was not found." >&2
  echo "Set FPGA_SETTINGS64 to the verified 2024.2 settings64.sh and source again." >&2
  return 1 2>/dev/null || exit 1
fi

# shellcheck disable=SC1090
source "$_fpga_settings"
echo "FPGA environment loaded from $_fpga_settings"
vivado -version
vitis -version
vitis_hls -version

unset _fpga_project_root _fpga_settings _candidate
