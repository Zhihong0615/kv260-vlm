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

# AMD's generated settings scripts read optional environment variables such as
# PYTHONPATH without first checking whether they are defined.  Temporarily
# disable nounset so this project helper remains safe when sourced by scripts
# that use `set -u`, then restore the caller's original shell option.
_fpga_restore_nounset=0
case $- in
  *u*)
    _fpga_restore_nounset=1
    set +u
    ;;
esac

# shellcheck disable=SC1090
source "$_fpga_settings"
_fpga_source_status=$?

if [[ "$_fpga_restore_nounset" -eq 1 ]]; then
  set -u
fi
if [[ "$_fpga_source_status" -ne 0 ]]; then
  echo "BLOCKED: failed to load $_fpga_settings (status $_fpga_source_status)." >&2
  unset _fpga_project_root _fpga_settings _candidate _fpga_restore_nounset _fpga_source_status
  return 1 2>/dev/null || exit 1
fi

echo "FPGA environment loaded from $_fpga_settings"
vivado -version
vitis -v
vitis_hls -version

unset _fpga_project_root _fpga_settings _candidate _fpga_restore_nounset _fpga_source_status
