#!/usr/bin/env bash
set -euo pipefail

readonly project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly board_script="$project_root/scripts/configure_kv260_xmutil_sudo_on_board.sh"
readonly ssh_host="${KV260_SSH_HOST:-kria}"

remote_path="$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$ssh_host" \
  'mktemp /tmp/configure-kv260-xmutil-sudo.XXXXXX.sh')"
remote_path="${remote_path//$'\r'/}"
if [[ ! "$remote_path" =~ ^/tmp/configure-kv260-xmutil-sudo\.[A-Za-z0-9]+\.sh$ ]]; then
  echo "FAIL: board returned an unexpected temporary path: $remote_path" >&2
  exit 1
fi

cleanup() {
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$ssh_host" \
    "rm -f -- '$remote_path'" >/dev/null 2>&1 || true
}
trap cleanup EXIT

scp -q "$board_script" "$ssh_host:$remote_path"
ssh -tt -o ConnectTimeout=5 "$ssh_host" "bash '$remote_path'"
