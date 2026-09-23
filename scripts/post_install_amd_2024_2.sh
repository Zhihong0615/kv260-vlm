#!/usr/bin/env bash
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_UNIT="kv260-amd-install-2024-2.service"

while systemctl --user is-active --quiet "$INSTALL_UNIT"; do
  sleep 30
done

install_load_state="$(systemctl --user show "$INSTALL_UNIT" --property=LoadState --value 2>/dev/null || true)"
if [[ -n "$install_load_state" && "$install_load_state" != "not-found" ]]; then
  install_result="$(systemctl --user show "$INSTALL_UNIT" --property=Result --value 2>/dev/null || true)"
  install_status="$(systemctl --user show "$INSTALL_UNIT" --property=ExecMainStatus --value 2>/dev/null || true)"
  if [[ "$install_result" != "success" || "$install_status" != "0" ]]; then
    echo "FAIL AMD installer unit: result=$install_result status=$install_status" >&2
    exit 1
  fi
elif [[ ! -r "$PROJECT_ROOT/tools/Xilinx/Vitis/2024.2/settings64.sh" ]]; then
  echo "FAIL AMD installer unit is unavailable and Vitis 2024.2 is not installed" >&2
  exit 1
fi

cd "$PROJECT_ROOT"
# shellcheck disable=SC1091
source env/setup_fpga.sh

host_status=0
hls_status=0
vivado_status=0
model_status=0
hash_status=0
kv260_status=0

scripts/check_host_env.sh || host_status=$?
vitis_hls -f env/hls_smoke_test/run_hls.tcl || hls_status=$?
vivado -mode batch -source env/vivado_smoke_test/run_vivado.tcl || vivado_status=$?
scripts/check_model_env.sh || model_status=$?
sha256sum -c models/SHA256SUMS || hash_status=$?
scripts/check_kv260_env.sh || kv260_status=$?

printf 'POSTCHECK host=%s hls=%s vivado=%s model=%s hashes=%s kv260=%s\n' \
  "$host_status" "$hls_status" "$vivado_status" "$model_status" "$hash_status" "$kv260_status"
if [[ "$host_status" -ne 0 || "$hls_status" -ne 0 || "$vivado_status" -ne 0 \
  || "$model_status" -ne 0 || "$hash_status" -ne 0 || "$kv260_status" -ne 0 ]]; then
  exit 1
fi

echo "AMD 2024.2 install and full environment acceptance: PASS"
