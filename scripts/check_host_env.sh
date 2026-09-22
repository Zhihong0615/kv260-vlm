#!/usr/bin/env bash
set -u

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failures=0

if [[ -f "$PROJECT_ROOT/env/setup_host_tools.sh" ]]; then
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/env/setup_host_tools.sh" >/dev/null
fi

pass() { printf 'PASS %-24s %s\n' "$1" "$2"; }
fail() { printf 'FAIL %-24s %s\n' "$1" "$2"; failures=$((failures + 1)); }

if grep -q '^ID=ubuntu' /etc/os-release; then pass OS "$(. /etc/os-release; printf '%s' "$PRETTY_NAME")"; else fail OS "not Ubuntu"; fi

if command -v python3 >/dev/null 2>&1; then pass Python "$(python3 --version 2>&1)"; else fail Python "python3 missing"; fi
if command -v git >/dev/null 2>&1; then pass Git "$(git --version)"; else fail Git "git missing"; fi
if command -v cmake >/dev/null 2>&1; then pass CMake "$(cmake --version | head -n 1)"; else fail CMake "cmake missing"; fi
if command -v ninja >/dev/null 2>&1; then pass Ninja "$(ninja --version)"; else fail Ninja "ninja missing"; fi
if command -v ccache >/dev/null 2>&1; then pass ccache "$(ccache --version | head -n 1)"; else fail ccache "ccache missing"; fi

if command -v vivado >/dev/null 2>&1; then
  vivado_version="$(vivado -version 2>&1 | head -n 1)"
  if grep -q '2024\.2' <<<"$vivado_version"; then pass Vivado "$vivado_version"; else fail Vivado "$vivado_version (expected 2024.2)"; fi
else
  fail Vivado "not found; source env/setup_fpga.sh after installation"
fi

if command -v vitis >/dev/null 2>&1; then
  vitis_version="$(vitis -version 2>&1 | head -n 1)"
  if grep -q '2024\.2' <<<"$vitis_version"; then pass Vitis "$vitis_version"; else fail Vitis "$vitis_version (expected 2024.2)"; fi
else
  fail Vitis "not found; source env/setup_fpga.sh after installation"
fi

if command -v vitis_hls >/dev/null 2>&1; then
  hls_version="$(vitis_hls -version 2>&1 | head -n 1)"
  if grep -q '2024\.2' <<<"$hls_version"; then pass Vitis_HLS "$hls_version"; else fail Vitis_HLS "$hls_version (expected 2024.2)"; fi
else
  fail Vitis_HLS "not found; source env/setup_fpga.sh after installation"
fi

if [[ -d "$PROJECT_ROOT/runtime/llama.cpp/.git" ]]; then
  llama_commit="$(git -C "$PROJECT_ROOT/runtime/llama.cpp" rev-parse HEAD 2>/dev/null || true)"
  if [[ -n "$llama_commit" ]]; then pass llama.cpp "$llama_commit"; else fail llama.cpp "git checkout unreadable"; fi
else
  fail llama.cpp "checkout missing"
fi

for llama_binary in llama-cli llama-server llama-mtmd-cli; do
  llama_path="$PROJECT_ROOT/runtime/llama.cpp/build/bin/$llama_binary"
  if [[ -x "$llama_path" ]] && "$llama_path" --help >/dev/null 2>&1; then
    pass "$llama_binary" "build/help check passed"
  else
    fail "$llama_binary" "build or --help check failed"
  fi
done

if command -v vivado >/dev/null 2>&1; then
  device_output="$(vivado -mode batch -nolog -nojournal -notrace -tempDir "$PROJECT_ROOT/work/vivado-device-check" -source /dev/stdin <<'TCL' 2>&1
set parts [get_parts *xck26*]
puts "K26_PART_COUNT=[llength $parts]"
exit
TCL
  )"
  if grep -q 'K26_PART_COUNT=[1-9][0-9]*' <<<"$device_output"; then pass K26_device "device database contains xck26"; else fail K26_device "xck26 not found"; fi
else
  fail K26_device "Vivado unavailable"
fi

if command -v vivado >/dev/null 2>&1; then
  board_output="$(vivado -mode batch -nolog -nojournal -notrace -tempDir "$PROJECT_ROOT/work/vivado-board-check" -source /dev/stdin <<'TCL' 2>&1
set boards [get_board_parts *kv260*]
puts "KV260_BOARD_COUNT=[llength $boards]"
exit
TCL
  )"
  if grep -q 'KV260_BOARD_COUNT=[1-9][0-9]*' <<<"$board_output"; then pass KV260_board "board part found"; else fail KV260_board "board part not found"; fi
else
  fail KV260_board "Vivado unavailable"
fi

if [[ "$failures" -eq 0 ]]; then
  echo "Host environment: PASS"
  exit 0
fi
echo "Host environment: FAIL ($failures check(s))"
exit 1
