#!/usr/bin/env bash
set -euo pipefail

# One bounded standalone probe. The exact .bit.bin SHA must be authorized by
# the Scheduler via RM11_FIRST_LOAD_AUTHORIZED_SHA before board state changes.
readonly app=kv260-rm11-unified-ffn
readonly deploy_dir=/tmp/rm11-ffn-up-capture
readonly package_source=$deploy_dir/package/$app
readonly install_dir=/lib/firmware/xilinx/$app
readonly tensor_dir=$deploy_dir/results/tensors
readonly bench=$deploy_dir/ffn_unified_bench
readonly identity=$deploy_dir/axilite_identity_probe
readonly restore_script=$deploy_dir/restore_starter_kit.sh
readonly app_bit_sha=72dfe46fbd27cc6a3dccf1defeaceef2e2939b9d7d4f679789ceae19a3657b81
readonly app_bin_sha=53894991503d8d2882dfddb1222f564994222902e03592a19ad23c7d027d7bc6
readonly app_dtbo_sha=11390e7257225582ed3c9788d03ba302327cc4927eb7b63b5a5900c8fc7fce24
readonly app_shell_sha=802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344
readonly bench_sha=b5932b15be19873ca6e7d5571e7111a7f0500d93aee2e8850393e8947060ee5e
readonly identity_sha=eaec93be87723d59f19d4d8d2e4cb3bcb94a9f44af87c695ac63ef17e06eaf5a
readonly restore_sha=8820113c2bab844ab9ba9f27f92eb502b1f1dc58a7f7c2ec919d1161c26b66e2
readonly capture_manifest_sha=07e2bddab0daa54ec33d5872114b9ff81b3bfe67b256db9ed9ece20e9b436095
readonly pool_bytes=1671168
readonly required_cma_kb=$(((pool_bytes + 1023) / 1024 + 8192))
readonly rollback_seconds=4200
readonly cpu_family_s=86.440139110

die() { echo "ERROR: $*" >&2; exit 1; }
sha256_of() { sha256sum "$1" | awk '{print $1}'; }
is_starter_active() {
  xmutil listapps 2>&1 | awk '$1 == "k26-starter-kits" && $NF ~ /^0,?$/ { found=1 } END { exit !found }'
}
is_candidate_active() {
  xmutil listapps 2>&1 | awk -v app="$app" '$1 == app && $NF ~ /^0,?$/ { found=1 } END { exit !found }'
}
snapshot() {
  echo "snapshot=$1 utc=$(date -u +%FT%TZ)"
  grep -E '^(MemAvailable|CmaTotal|CmaFree|SwapFree):' /proc/meminfo || true
  echo "fclk0=$(cat /sys/bus/platform/devices/fclk0/set_rate 2>/dev/null || echo UNKNOWN)"
  echo "fpga_manager=$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo UNKNOWN)"
}
require_cma() {
  local label="$1" free_kb
  free_kb=$(awk '$1 == "CmaFree:" { print $2 }' /proc/meminfo)
  [[ "$free_kb" =~ ^[0-9]+$ ]] || die "$label cannot read CmaFree"
  echo "cma_check=$label free_kB=$free_kb required_kB=$required_cma_kb pool_bytes=$pool_bytes"
  (( free_kb >= required_cma_kb )) || die "$label lacks bounded BO plus 8 MiB CMA margin"
}

[[ "$(id -u)" -eq 0 && "$#" -eq 0 ]] || { echo "Usage: sudo env RM11_FIRST_LOAD_AUTHORIZED_SHA=<exact-sha256> bash $0" >&2; exit 2; }
[[ "$(printenv RM11_FIRST_LOAD_AUTHORIZED_SHA 2>/dev/null || true)" == "$app_bin_sha" ]] || die "Scheduler has not authorized this exact .bit.bin SHA-256"
readonly capture_manifest=$deploy_dir/results/SHA256SUMS
[[ -r "$capture_manifest" && "$(sha256_of "$capture_manifest")" == "$capture_manifest_sha" ]] || die "board tensor manifest missing or changed"
(cd "$deploy_dir" && sha256sum -c results/SHA256SUMS) || die "board capture manifest check failed"
for pair in "$bench:$bench_sha" "$identity:$identity_sha" "$restore_script:$restore_sha"; do
  path=$(cut -d: -f1 <<<"$pair")
  expected=$(cut -d: -f2- <<<"$pair")
  [[ -r "$path" && "$(sha256_of "$path")" == "$expected" ]] || die "pinned board input missing or changed: $path"
done
[[ -x "$bench" && -x "$identity" && -x "$restore_script" ]] || die "pinned board executable is not executable"
[[ -s "$package_source/$app.bit" && "$(sha256_of "$package_source/$app.bit")" == "$app_bit_sha" ]] || die "routed .bit missing or changed"
[[ -s "$package_source/$app.bit.bin" && "$(sha256_of "$package_source/$app.bit.bin")" == "$app_bin_sha" ]] || die "Bootgen .bit.bin missing or changed"
[[ -s "$package_source/$app.dtbo" && "$(sha256_of "$package_source/$app.dtbo")" == "$app_dtbo_sha" ]] || die "overlay missing or changed"
[[ -s "$package_source/shell.json" && "$(sha256_of "$package_source/shell.json")" == "$app_shell_sha" ]] || die "shell.json missing or changed"
(cd "$package_source" && sha256sum -c SHA256SUMS) || die "RM11 package manifest check failed"
for layer in 0 13 26; do
  for suffix in weight.f16 activation.f32 output.f32; do
    [[ -s "$tensor_dir/ffn_up-$layer.$suffix" ]] || die "missing board tensor ffn_up-$layer.$suffix"
  done
done
[[ -z "$(pgrep -x llama-mtmd-optrace || true)" ]] || die "capture process is active"
[[ -z "$(pgrep -x llama-mtmd-cli || true)" ]] || die "llama CLI is active"
[[ -z "$(pgrep -x dpkg || true)$(pgrep -x apt-get || true)" ]] || die "package management is active"
[[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] || die "FPGA manager is not operating"
is_starter_active || die "k26-starter-kits must be active on entry"
[[ "$(cat /sys/bus/platform/devices/fclk0/set_rate 2>/dev/null || true)" == 99999999 ]] || die "FCLK0 must be 99,999,999 Hz on entry"
require_cma before_rm11_load

umask 022
mkdir -p "$deploy_dir/runs"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
run_dir=$deploy_dir/runs/rm11-ffn-up-$stamp
mkdir -m 0755 -- "$run_dir"
exec > >(tee -a "$run_dir/driver.log") 2>&1
echo "run_dir=$run_dir utc=$(date -u +%FT%TZ) boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "app=$app bit_sha256=$app_bit_sha bit_bin_sha256=$app_bin_sha dtbo_sha256=$app_dtbo_sha shell_sha256=$app_shell_sha"
echo "first_load_authorization_sha256=$(printenv RM11_FIRST_LOAD_AUTHORIZED_SHA) rollback_s=$rollback_seconds"
echo "bench_sha256=$(sha256_of "$bench") identity_sha256=$(sha256_of "$identity") capture_manifest_sha256=$(sha256_of "$capture_manifest")"
echo "model_sha256=8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773 mmproj_sha256=ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293 image_sha256=3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f"
snapshot before_rm11

readonly restore_log=$run_dir/restore.log
readonly rollback_unit=rm11-ffn-up-$stamp-rollback
restore_ok=0
timer_armed=0
package_installed_by_script=0
finish() {
  local original_rc=$? restore_rc=0
  trap - EXIT INT TERM
  set +e
  if [[ "$timer_armed" == 1 ]]; then
    echo "explicit_restore_begin utc=$(date -u +%FT%TZ)"
    bash "$restore_script" "$restore_log"
    restore_rc=$?
    if (( restore_rc == 0 )); then
      restore_ok=1
      if [[ "$package_installed_by_script" == 1 ]]; then
        rm -f -- "$install_dir/$app.bit.bin" "$install_dir/$app.dtbo" "$install_dir/shell.json"
        rmdir -- "$install_dir"
        if (( $? == 0 )); then echo "rm11_package_cleanup=PASS"; else restore_rc=1; echo "rm11_package_cleanup=FAIL"; fi
      fi
      systemctl stop "$rollback_unit.timer" >/dev/null 2>&1
      systemctl stop "$rollback_unit.service" >/dev/null 2>&1
      systemctl reset-failed "$rollback_unit.timer" "$rollback_unit.service" >/dev/null 2>&1
      echo "starter_kit_restore=PASS"
    else
      echo "starter_kit_restore=FAIL watchdog_timer_left_armed=1"
    fi
    snapshot after_restore
    echo "explicit_restore_end utc=$(date -u +%FT%TZ)"
  fi
  if [[ "$original_rc" -eq 0 && "$restore_rc" -ne 0 ]]; then original_rc=1; fi
  echo "run_exit_status=$original_rc starter_kit_restore=$([[ "$restore_ok" == 1 ]] && echo PASS || echo NOT_CONFIRMED)"
  exit "$original_rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

systemd-run --quiet --unit="$rollback_unit" --on-active=4200s "$restore_script" "$restore_log" || die "could not arm starter-kit rollback timer"
systemctl is-active --quiet "$rollback_unit.timer" || die "rollback timer is not active; no app state changed"
timer_armed=1
echo "rollback_timer=$rollback_unit.timer timer_state=active restore_after_seconds=$rollback_seconds"
if [[ -e "$install_dir" ]]; then
  [[ -s "$install_dir/$app.bit.bin" && "$(sha256_of "$install_dir/$app.bit.bin")" == "$app_bin_sha" ]] || die "existing app image differs from authorized hash"
  [[ -s "$install_dir/$app.dtbo" && "$(sha256_of "$install_dir/$app.dtbo")" == "$app_dtbo_sha" ]] || die "existing app overlay differs from package"
  [[ -s "$install_dir/shell.json" && "$(sha256_of "$install_dir/shell.json")" == "$app_shell_sha" ]] || die "existing app metadata differs from package"
else
  install -d -m 0755 -- "$install_dir"
  install -m 0644 -- "$package_source/$app.bit.bin" "$install_dir/$app.bit.bin"
  install -m 0644 -- "$package_source/$app.dtbo" "$install_dir/$app.dtbo"
  install -m 0644 -- "$package_source/shell.json" "$install_dir/shell.json"
  package_installed_by_script=1
fi

snapshot before_app_unload
xmutil unloadapp
for _ in $(seq 1 120); do
  if ! grep -q '^vision_ffn_unified_tile_0$' /sys/class/uio/uio*/name 2>/dev/null; then break; fi
  sleep 0.5
done
! grep -q '^vision_ffn_unified_tile_0$' /sys/class/uio/uio*/name 2>/dev/null || die "RM11 UIO remains after unload"
xmutil loadapp "$app"
ready=0
for _ in $(seq 1 120); do
  if [[ "$(cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true)" == operating ]] &&
     grep -q '^vision_ffn_unified_tile_0$' /sys/class/uio/uio*/name 2>/dev/null &&
     grep -q '^axi_perf_mon_0$' /sys/class/uio/uio*/name 2>/dev/null && is_candidate_active; then
    ready=1
    break
  fi
  sleep 0.5
done
[[ "$ready" == 1 ]] || die "RM11 HLS/APM UIOs did not become ready"
active_fclk0_hz=$(cat /sys/bus/platform/devices/fclk0/set_rate)
(( active_fclk0_hz >= 99000000 && active_fclk0_hz <= 101000000 && active_fclk0_hz <= 100000000 )) || die "RM11 PL0 exceeds routed 100 MHz"
snapshot rm11_loaded
require_cma after_rm11_load
"$identity" | tee "$run_dir/axilite_identity.log" || die "AXI-Lite identity/ABI probe failed"
grep -Fq 'RM11_HLS_IDENTITY ' "$run_dir/axilite_identity.log" || die "HLS identity was not verified"
grep -Fq 'RM11_APM_IDENTITY ' "$run_dir/axilite_identity.log" || die "APM identity was not verified"
grep -Fq 'RM11_AXILITE_INVALID_TASK ret=-4 expected=-4 dma_pointer_used=0 PASS' "$run_dir/axilite_identity.log" || die "invalid-task ABI differs"

run_tensor() {
  local layer="$1" k="$2" m="$3" n="$4" stage="$5" compute="$6"
  local out=$run_dir/$layer.log time_log=$run_dir/$layer-time-v.txt
  require_cma "$layer-before-DMA"
  echo "standalone_begin layer=$layer K/M/N=$k/$m/$n expected_stage_compute=$stage/$compute utc=$(date -u +%FT%TZ)"
  /usr/bin/time -v -o "$time_log" /usr/bin/timeout --signal=TERM --kill-after=10s 120s \
    "$bench" "$tensor_dir/$layer.weight.f16" "$tensor_dir/$layer.activation.f32" \
      "$tensor_dir/$layer.output.f32" "$layer" "$k" "$m" "$n" 1 >"$out" 2>&1 || die "$layer standalone run failed"
  cat "$out"
  grep -Fq 'CALL=1 ' "$out" || die "$layer per-call metrics missing"
  grep -Fq "commands=$stage/$compute " "$out" || die "$layer stage/compute command counts mismatch"
  local total_line max_abs rmse cosine
  total_line=$(grep -F 'TOTAL calls=1 ' "$out" | tail -n1)
  [[ -n "$total_line" ]] || die "$layer total-call metrics missing"
  max_abs=$(sed -n 's/.* max_abs=\([^ ]*\).*/\1/p' <<<"$total_line")
  rmse=$(sed -n 's/.* RMSE=\([^ ]*\).*/\1/p' <<<"$total_line")
  cosine=$(sed -n 's/.* cosine=\([^ ]*\).*/\1/p' <<<"$total_line")
  awk -v a="$max_abs" -v r="$rmse" -v c="$cosine" 'BEGIN { exit !(a+0 <= 1e-3 && r+0 <= 1e-4 && c+0 >= 0.999) }' || die "$layer numeric gate failed"
  echo "standalone_numeric_gate=PASS layer=$layer max_abs=$max_abs RMSE=$rmse cosine=$cosine time_log=$time_log"
  snapshot "$layer-after-DMA"
}

run_tensor ffn_up-0 1152 4304 1120 35 1190
run_tensor ffn_up-13 1152 4304 280 9 306
run_tensor ffn_up-26 1152 4304 280 9 306

metric() {
  local layer="$1" key="$2"
  sed -n "s/.* $key=\([^ ]*\).*/\1/p" "$run_dir/$layer.log" | tail -n1
}
up0_wall=$(metric ffn_up-0 wall_ms)
up13_wall=$(metric ffn_up-13 wall_ms)
up26_wall=$(metric ffn_up-26 wall_ms)
up0_kernel=$(metric ffn_up-0 hls_wait_ms)
up13_kernel=$(metric ffn_up-13 hls_wait_ms)
up26_kernel=$(metric ffn_up-26 hls_wait_ms)
awk -v a="$up0_wall" -v b="$up13_wall" -v c="$up26_wall" \
    -v d="$up0_kernel" -v e="$up13_kernel" -v f="$up26_kernel" -v cpu="$cpu_family_s" \
    'BEGIN { pl=(35*a+50*(b+c))/1000; kernel=(35*d+50*(e+f))/1000;
      printf "representative_call_projection calls=135 CPU_family_s=%.6f PL_total_call_s=%.6f PL_kernel_s=%.6f estimated_speedup=%.4f\n",
      cpu, pl, kernel, cpu/pl }'
snapshot before_restore
echo "rm11_ffn_up_standalone=PASS evidence_dir=$run_dir"
