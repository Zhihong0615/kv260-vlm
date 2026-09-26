#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
app=kv260-rm11-unified-ffn
package_dir="$repo_root/experiments/rm11_unified_ffn/package/$app"
system_root="${RM11_SYSTEM_ROOT:-$repo_root/experiments/rm11_unified_ffn/build/full_system}"
bit_file="$system_root/kv260_rm11_unified_ffn.runs/impl_1/kv260_rm11_unified_ffn_wrapper.bit"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
bootgen="${BOOTGEN:-$tool_root/Vivado/2024.2/bin/bootgen}"
dtc="${DTC:-$tool_root/Vivado/2024.2/bin/dtc}"
bif="$package_dir/$app.bif"

test -s "$bit_file" && test -x "$bootgen" && test -x "$dtc"
cp "$bit_file" "$package_dir/$app.bit"
"$dtc" -@ -I dts -O dtb -o "$package_dir/$app.dtbo" "$package_dir/$app.dtsi"
printf 'all:\n{\n  [destination_device = pl] %s\n}\n' "$package_dir/$app.bit" > "$bif"
"$bootgen" -image "$bif" -arch zynqmp -o "$package_dir/$app.bit.bin" -w
(cd "$package_dir" && sha256sum "$app.bit" "$app.bit.bin" "$app.dtbo" "$app.dtsi" shell.json > SHA256SUMS)
(cd "$package_dir" && sha256sum -c SHA256SUMS)
printf 'RM11_PACKAGE_DIR=%s\n' "$package_dir"
