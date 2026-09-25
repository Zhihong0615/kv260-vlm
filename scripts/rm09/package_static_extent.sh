#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
app_name="kv260-rm09-static-extent"
package_dir="$repo_root/experiments/rm09_static_extent/package/$app_name"
system_root="${RM09_SYSTEM_ROOT:?set RM09_SYSTEM_ROOT to the completed Vivado build directory}"
bit_file="${RM09_STATIC_EXTENT_BIT_FILE:-$system_root/${app_name//-/_}.runs/impl_1/${app_name//-/_}_wrapper.bit}"
tool_root="${XILINX_TOOLS_ROOT:-/home/zhiro/research/kv260-vlm/tools/Xilinx}"
bootgen="${BOOTGEN:-$tool_root/Vivado/2024.2/bin/bootgen}"
dtc="${DTC:-$tool_root/Vivado/2024.2/bin/dtc}"
source_dts="$package_dir/$app_name.dtsi"

test -s "$bit_file"
test -x "$bootgen"
test -x "$dtc"
mkdir -p "$package_dir"
cp "$repo_root/experiments/rm08/source/shell.json" "$package_dir/shell.json"
"$dtc" -@ -I dts -O dtb -o "$package_dir/$app_name.dtbo" "$source_dts"

bif_file="$(mktemp "$package_dir/.${app_name}.XXXXXX.bif")"
trap 'rm -f "$bif_file"' EXIT
printf 'all:\n{\n  [destination_device = pl] %s\n}\n' "$bit_file" > "$bif_file"
"$bootgen" -image "$bif_file" -arch zynqmp -o "$package_dir/$app_name.bit.bin" -w
(cd "$package_dir" && sha256sum \
  "$app_name.bit.bin" "$app_name.dtbo" "$app_name.dtsi" shell.json > SHA256SUMS)
(cd "$package_dir" && sha256sum -c SHA256SUMS)
printf 'RM09_PACKAGE_DIR=%s\n' "$package_dir"
