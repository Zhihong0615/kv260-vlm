#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_dts="$repo_root/experiments/rm09/overlay_pl0_187m5.dtsi"
package_dir="$repo_root/experiments/rm09/package/kv260-rm07-bounded-k16-pl0-187m5"
dtc="${DTC:-/home/zhiro/research/kv260-vlm/tools/Xilinx/Vivado/2024.2/bin/dtc}"

test -f "$source_dts"
test -x "$dtc"
mkdir -p "$package_dir"
cp "$source_dts" "$package_dir/kv260-rm07-bounded-k16.dtsi"
cp "$repo_root/experiments/rm08/source/shell.json" "$package_dir/shell.json"
"$dtc" -@ -I dts -O dtb \
  -o "$package_dir/kv260-rm07-bounded-k16.dtbo" \
  "$package_dir/kv260-rm07-bounded-k16.dtsi"
(cd "$package_dir" && sha256sum \
  kv260-rm07-bounded-k16.dtbo \
  kv260-rm07-bounded-k16.dtsi \
  shell.json > SHA256SUMS)
cat "$package_dir/SHA256SUMS"
