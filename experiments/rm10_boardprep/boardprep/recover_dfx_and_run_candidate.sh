#!/usr/bin/env bash
set -Eeuo pipefail

readonly starter=k26-starter-kits
readonly manager=/sys/class/fpga_manager/fpga0/state
readonly fclk=/sys/bus/platform/devices/fclk0/set_rate
readonly default_file=/etc/dfx-mgrd/default_firmware
readonly candidate=/tmp/rm10-boardprep/boardprep/run_candidate.sh
readonly log_dir=/tmp/rm10-boardprep
readonly stamp=$(date -u +%Y%m%dT%H%M%SZ)
readonly recovery_log=$log_dir/recovery-$stamp.log

die() { echo "RECOVERY_FAIL: $*" >&2; exit 1; }
is_starter_active() {
  awk -v app="$starter" '$1 == app && $NF ~ /^0,?$/ { found=1 } END { exit !found }'
}

[[ "$(id -u)" == 0 && "$#" == 0 ]] || die "run once as root with no arguments"
mkdir -p -- "$log_dir"
exec > >(tee -a "$recovery_log") 2>&1
echo "recovery_log=$recovery_log begin_utc=$(date -u +%FT%TZ)"

[[ -r "$default_file" ]] || die "default firmware config is unreadable"
[[ "$(tr -d '\r\n' < "$default_file")" == "$starter" ]] || die "default firmware is not $starter"
[[ -r "$manager" && "$(cat "$manager")" == operating ]] || die "FPGA manager is not operating"
[[ -r "$fclk" && "$(cat "$fclk")" == 99999999 ]] || die "FCLK0 is not 99,999,999 Hz"
systemctl is-active --quiet dfx-mgr.service || die "dfx-mgr.service is not active"
[[ -r "$candidate" ]] || die "guarded candidate runner is missing"
! pgrep -x llama-mtmd-cli >/dev/null 2>&1 || die "a VLM process is already active"
for process in apt apt-get dpkg; do
  ! pgrep -x "$process" >/dev/null 2>&1 || die "$process is already active"
done

apps=$(xmutil listapps 2>&1) || die "xmutil listapps failed before recovery: $apps"
printf '%s\n' "$apps"
printf '%s\n' "$apps" | is_starter_active || die "$starter is not active before recovery"

unload=$(xmutil unloadapp 2>&1) || die "xmutil unloadapp failed: $unload"
printf '%s\n' "$unload"
printf '%s\n' "$unload" | grep -Fq 'remove from slot 0 returns: 0 (Ok)' || die "starter unload was not confirmed"

systemctl restart dfx-mgr.service || die "dfx-mgr.service restart failed"
ready=0
for _ in $(seq 1 60); do
  apps=$(xmutil listapps 2>&1) || apps=
  if systemctl is-active --quiet dfx-mgr.service &&
     [[ "$(cat "$manager" 2>/dev/null || true)" == operating ]] &&
     [[ "$(cat "$fclk" 2>/dev/null || true)" == 99999999 ]] &&
     printf '%s\n' "$apps" | is_starter_active; then
    ready=1
    break
  fi
  sleep 1
done
printf '%s\n' "$apps"
[[ "$ready" == 1 ]] || die "autoloaded starter, FPGA manager, clock, or service did not verify"
echo "recovery=PASS starter=$starter fpga_manager=operating fclk0_hz=99999999 utc=$(date -u +%FT%TZ)"
echo "starting_guarded_candidate=$candidate"
exec bash "$candidate"
