#!/usr/bin/env bash
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_UNIT="kv260-amd-install-2024-2.service"

while systemctl --user is-active --quiet "$INSTALL_UNIT"; do
  sleep 30
done

install_result="$(systemctl --user show "$INSTALL_UNIT" --property=Result --value 2>/dev/null || true)"
install_status="$(systemctl --user show "$INSTALL_UNIT" --property=ExecMainStatus --value 2>/dev/null || true)"
if [[ "$install_result" != "success" || "$install_status" != "0" ]]; then
  echo "FAIL AMD installer unit: result=$install_result status=$install_status" >&2
  exit 1
fi

cd "$PROJECT_ROOT"
# shellcheck disable=SC1091
source env/setup_fpga.sh

host_status=0
hls_status=0
vivado_status=0

scripts/check_host_env.sh || host_status=$?
vitis_hls -f env/hls_smoke_test/run_hls.tcl || hls_status=$?
vivado -mode batch -source env/vivado_smoke_test/run_vivado.tcl || vivado_status=$?

printf 'POSTCHECK host=%s hls=%s vivado=%s\n' "$host_status" "$hls_status" "$vivado_status"
if [[ "$host_status" -ne 0 || "$hls_status" -ne 0 || "$vivado_status" -ne 0 ]]; then
  exit 1
fi

echo "AMD 2024.2 install and smoke tests: PASS"
