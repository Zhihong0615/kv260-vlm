#!/usr/bin/env bash
set -euo pipefail

pid="${1:?usage: diagnose_stall.sh LLAMA_PID}"
[[ "$(id -u)" -eq 0 ]]
[[ -r "/proc/$pid/status" ]]
[[ "$(cat "/proc/$pid/comm")" == "llama-mtmd-cli" ]]

out="/tmp/rm08-vlm-stall-${pid}-$(date -u +%Y%m%dT%H%M%SZ).txt"
{
  date -u
  ps -L -p "$pid" -o tid,stat,time,wchan:28,comm
  gdb -q -nx -batch -p "$pid" -ex 'set pagination off' -ex 'thread apply all bt 16' -ex detach || echo "gdb_exit_status=$?"
} >"$out" 2>&1
chmod 0644 "$out"
echo "diagnostic=$out"
