#!/usr/bin/env bash
set -euo pipefail

readonly target="/etc/sudoers.d/90-kv260-xmutil-listapps"
candidate="$(mktemp /tmp/kv260-xmutil-sudoers.XXXXXX)"
trap 'rm -f -- "$candidate"' EXIT

if [[ "$(id -un)" != "ubuntu" ]]; then
  echo "FAIL: this rule is intentionally scoped to the ubuntu account" >&2
  exit 1
fi
if [[ "$(command -v xmutil)" != "/usr/bin/xmutil" ]]; then
  echo "FAIL: expected xmutil at /usr/bin/xmutil" >&2
  exit 1
fi
if [[ ! -x /usr/sbin/visudo ]]; then
  echo "FAIL: /usr/sbin/visudo is unavailable" >&2
  exit 1
fi

printf '%s\n' 'ubuntu ALL=(root) NOPASSWD: /usr/bin/xmutil listapps' >"$candidate"
chmod 0600 "$candidate"
/usr/sbin/visudo -cf "$candidate"

# This is the only interactive privilege step. The password is read by sudo
# from the board terminal and is never passed through a file or command line.
sudo -v
if sudo test -e "$target" && ! sudo cmp -s "$candidate" "$target"; then
  echo "FAIL: $target already exists with different content; refusing to overwrite it" >&2
  exit 1
fi
sudo /usr/bin/install -o root -g root -m 0440 "$candidate" "$target"
sudo /usr/sbin/visudo -cf "$target"
sudo /usr/bin/stat -c 'SUDOERS=%U:%G %a %n' "$target"

# Drop the password timestamp before proving that only the exact read-only
# command is passwordless. Parse the complete sudo listing because `sudo -l
# command` also exits zero for commands that are permitted only with a
# password; its return code alone does not prove NOPASSWD access.
sudo -k
listapps_output="$(sudo -n /usr/bin/xmutil listapps)"
if [[ -z "${listapps_output//[[:space:]]/}" ]]; then
  echo "FAIL: xmutil listapps returned no application-list output" >&2
  exit 1
fi
printf '%s\n' "$listapps_output"

sudo_listing="$(sudo -n -l)"
nopasswd_xmutil_lines="$(grep -E 'NOPASSWD:[[:space:]]*/usr/bin/xmutil([[:space:]]|$)' <<<"$sudo_listing" || true)"
if [[ "$nopasswd_xmutil_lines" != *'NOPASSWD: /usr/bin/xmutil listapps'* ]]; then
  echo "FAIL: exact listapps NOPASSWD rule is not active" >&2
  exit 1
fi
if [[ "$(wc -l <<<"$nopasswd_xmutil_lines")" -ne 1 ]]; then
  echo "FAIL: an additional passwordless xmutil rule is active" >&2
  printf '%s\n' "$nopasswd_xmutil_lines" >&2
  exit 1
fi

echo "PASS: passwordless sudo is limited to /usr/bin/xmutil listapps"
