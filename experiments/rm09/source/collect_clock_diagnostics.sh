#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this collector as root; it performs read-only clock/DT/kernel inspection." >&2
  exit 2
fi
if [[ "$#" != 1 || "$1" != /* ]]; then
  echo "Usage: sudo bash $0 /absolute/output/directory" >&2
  exit 2
fi

out="$1"
umask 022
mkdir -p -m 0755 -- "$out"
exec > >(tee "$out/clock-diagnostics.log") 2>&1

echo "diagnostics_begin_utc=$(date -u +%FT%TZ)"
echo "hostname=$(hostname)"
echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "kernel=$(uname -a)"
echo "fclk0_driver=$(readlink -f /sys/bus/platform/devices/fclk0/driver 2>/dev/null || echo UNKNOWN)"
echo "fclk0_of_node=$(readlink -f /sys/bus/platform/devices/fclk0/of_node 2>/dev/null || echo UNKNOWN)"
echo "fclk0_rate_hz=$(cat /sys/bus/platform/devices/fclk0/set_rate 2>/dev/null || echo UNKNOWN)"
echo "fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
echo "starter_and_rm07_app_state_begin"
xmutil listapps 2>&1 || true
echo "starter_and_rm07_app_state_end"

debugfs_mount="$(findmnt -rn -o TARGET,FSTYPE,OPTIONS --target /sys/kernel/debug 2>/dev/null || true)"
echo "debugfs_mount=${debugfs_mount:-UNAVAILABLE}"
if [[ -r /sys/kernel/debug/clk/clk_summary ]]; then
  echo "clk_summary_status=READABLE"
  cat /sys/kernel/debug/clk/clk_summary >"$out/clk_summary.txt"
  sed -n '1,240p' "$out/clk_summary.txt"
else
  echo "clk_summary_status=UNAVAILABLE"
fi

python3 - "$out/device-tree-clock-properties.txt" <<'PY'
import pathlib
import struct
import sys

output = pathlib.Path(sys.argv[1])
root = pathlib.Path('/sys/firmware/devicetree/base')
interesting = {'compatible', 'status', 'clocks', 'clock-names', 'clock-output-names',
               'assigned-clocks', 'assigned-clock-rates', 'assigned-clock-parents'}
with output.open('w', encoding='utf-8') as stream:
    for prop in root.rglob('*'):
        if not prop.is_file() or prop.name not in interesting:
            continue
        node = str(prop.parent)
        if prop.name in {'assigned-clocks', 'assigned-clock-rates', 'assigned-clock-parents'}:
            value = prop.read_bytes()
            cells = [struct.unpack('>I', value[i:i+4])[0] for i in range(0, len(value)-len(value)%4, 4)]
            decoded = ' '.join(f'0x{x:08x}' for x in cells)
        elif prop.name in {'clocks'}:
            value = prop.read_bytes()
            cells = [struct.unpack('>I', value[i:i+4])[0] for i in range(0, len(value)-len(value)%4, 4)]
            decoded = ' '.join(f'0x{x:08x}' for x in cells)
        else:
            decoded = prop.read_bytes().rstrip(b'\0').replace(b'\0', b',').decode('utf-8', 'backslashreplace')
        if prop.name.startswith('assigned-') or '/fclk' in node or node.endswith('/amba_pl') or 'xlnx,fclk' in decoded:
            stream.write(f'{node}/{prop.name}={decoded}\n')
PY
echo "device_tree_clock_properties_begin"
cat "$out/device-tree-clock-properties.txt"
echo "device_tree_clock_properties_end"

if command -v dtc >/dev/null 2>&1; then
  if dtc -q -I fs -O dts -o "$out/live-device-tree.dts" /sys/firmware/devicetree/base; then
    echo "dtc_status=PASS path=$out/live-device-tree.dts"
    rg -n -C 4 'fclk|assigned-clock|amba_pl' "$out/live-device-tree.dts" >"$out/live-device-tree-clock-nodes.txt" || true
    cat "$out/live-device-tree-clock-nodes.txt"
  else
    echo "dtc_status=FAILED"
  fi
else
  echo "dtc_status=NOT_INSTALLED"
fi

if dmesg -T >"$out/dmesg.txt" 2>"$out/dmesg.stderr"; then
  echo "dmesg_status=PASS path=$out/dmesg.txt"
  tail -n 240 "$out/dmesg.txt"
else
  echo "dmesg_status=FAILED"
  cat "$out/dmesg.stderr"
fi

if command -v journalctl >/dev/null 2>&1; then
  journalctl -k -b --no-pager >"$out/kernel-journal.txt" 2>"$out/kernel-journal.stderr" || true
  echo "kernel_journal_path=$out/kernel-journal.txt"
fi

echo "diagnostics_end_utc=$(date -u +%FT%TZ)"
echo "This collector only reads clock, device-tree, active-app, and kernel-log state."
