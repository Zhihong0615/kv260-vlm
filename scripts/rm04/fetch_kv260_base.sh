#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
dest="$repo_root/vendor/kria-base-hardware"
url="https://github.com/Xilinx/kria-base-hardware.git"
revision="a722daa4536784a888693299eed46fb2ac0841a3"

if [[ -e "$dest" ]]; then
  echo "Refusing to replace existing path: $dest" >&2
  exit 1
fi

mkdir -p "$(dirname "$dest")"
git clone --filter=blob:none "$url" "$dest"
git -C "$dest" checkout --detach "$revision"
printf 'Checked out %s at %s\n' "$url" "$revision"
