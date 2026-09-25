#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
app_name="kv260-rm07-bounded-k16"
source_dir="$repo_root/experiments/rm08/source"
package_dir="$repo_root/experiments/rm08/package/$app_name"
bit_file="$repo_root/experiments/rm07/build/bounded_k16_system/kv260_rm07_bounded_k16.runs/impl_1/kv260_rm07_bounded_k16_wrapper.bit"
bootgen="${BOOTGEN:-/home/zhiro/research/kv260-vlm/tools/Xilinx/Vivado/2024.2/bin/bootgen}"
dtc="${DTC:-/home/zhiro/research/kv260-vlm/tools/Xilinx/Vivado/2024.2/bin/dtc}"

test -f "$bit_file"
test -x "$bootgen"
test -x "$dtc"
mkdir -p "$package_dir"

expected_bit_sha="1d537918b45bc9a53afb290beecda379918b7fd1a14374d6b5173358d8291942"
actual_bit_sha="$(sha256sum "$bit_file" | awk '{print $1}')"
if [[ "$actual_bit_sha" != "$expected_bit_sha" ]]; then
  printf 'unexpected RM07 bitstream SHA256: %s\n' "$actual_bit_sha" >&2
  exit 2
fi

cp "$source_dir/shell.json" "$package_dir/shell.json"
cp "$source_dir/axilite_smoke.c" "$package_dir/axilite_smoke.c"
cp "$source_dir/kv260-rm07-bounded-k16.dtsi" "$package_dir/kv260-rm07-bounded-k16.dtsi"
"$dtc" -@ -I dts -O dtb \
  -o "$package_dir/kv260-rm07-bounded-k16.dtbo" \
  "$source_dir/kv260-rm07-bounded-k16.dtsi"

bif_file="$package_dir/kv260-rm07-bounded-k16.bif"
printf 'all:\n{\n  [destination_device = pl] %s\n}\n' "$bit_file" > "$bif_file"
"$bootgen" -image "$bif_file" -arch zynqmp \
  -o "$package_dir/kv260-rm07-bounded-k16.bit.bin" -w
rm -f "$bif_file"

(cd "$package_dir" && sha256sum kv260-rm07-bounded-k16.bit.bin \
  kv260-rm07-bounded-k16.dtbo shell.json > SHA256SUMS)
printf 'Built %s\n' "$package_dir"
cat "$package_dir/SHA256SUMS"
