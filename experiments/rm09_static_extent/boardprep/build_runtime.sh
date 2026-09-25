#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == 0 ]]; then
  echo "Build as the board's ubuntu user; do not use sudo." >&2
  exit 2
fi

readonly board_root=/home/ubuntu/kv260-vlm-p2-cpu
readonly rm08_runtime_commit=7c9c15992ff6df6d6fa10636b430e170a3dd2934
readonly extent_patch_sha=22d96ed06be3b8d6c2dd8f841785fdd90981932fe0c3754189dfe710493dc32d
readonly runtime_id="${extent_patch_sha:0:12}"
readonly stage_root="${RM09_STAGE_ROOT:-/tmp/rm09-static-extent}"
readonly runtime_patch_dir="$stage_root/runtime"
readonly runtime_base="${RM09_RM08_SOURCE:-$board_root/rm08-runtime-src-1a90d48}"
readonly extent_patch="$runtime_patch_dir/runtime_dispatch.patch"
readonly source_root="$board_root/rm09-static-extent-runtime-src-$runtime_id"
readonly runtime_root="$board_root/rm09-static-extent-build-$runtime_id"
readonly cli="$runtime_root/bin/llama-mtmd-cli"
readonly helper="$runtime_root/bin/rm08-ffn-down-helper-smoke"
readonly build_jobs="${RM09_BUILD_JOBS:-4}"
readonly source_id="$source_root/RM09_SOURCE_ID.txt"

die() { echo "ERROR: $*" >&2; exit 1; }
sha256_of() { sha256sum "$1" | awk '{print $1}'; }

[[ -d "$runtime_base" && -r "$runtime_base/RM08_SOURCE_COMMIT.txt" ]] || die "missing frozen RM08 runtime source copy: $runtime_base"
[[ -f "$extent_patch" ]] || die "RM09 runtime patch is missing from $runtime_patch_dir"
[[ "$(sha256_of "$extent_patch")" == "$extent_patch_sha" ]] || die "RM09 runtime patch hash mismatch"
[[ "$(cat "$runtime_base/RM08_SOURCE_COMMIT.txt")" == "$rm08_runtime_commit" ]] || die "runtime base is not the frozen RM08 source commit $rm08_runtime_commit"
[[ "$build_jobs" =~ ^[1-4]$ ]] || die "RM09_BUILD_JOBS must be from 1 to 4 on this board"
if [[ ! -e "$source_root" && ! -e "$runtime_root" ]]; then
  cp -a -- "$runtime_base" "$source_root"
  (cd "$source_root" && git apply --check "$extent_patch" && git apply "$extent_patch") || die "RM09 runtime patch did not apply cleanly"
  printf 'RM09_BASE_RUNTIME_COMMIT=%s\nRM09_EXTENT_PATCH_SHA256=%s\n' \
    "$rm08_runtime_commit" "$extent_patch_sha" >"$source_id"
elif [[ -d "$source_root" && -d "$runtime_root" && -r "$source_id" ]]; then
  grep -Fxq "RM09_BASE_RUNTIME_COMMIT=$rm08_runtime_commit" "$source_id" || die "existing RM09 source has a different base commit"
  grep -Fxq "RM09_EXTENT_PATCH_SHA256=$extent_patch_sha" "$source_id" || die "existing RM09 source has a different patch hash"
else
  die "incomplete RM09 source/build pair; refusing to overwrite"
fi

if [[ ! -r "$runtime_root/CMakeCache.txt" ]]; then
  cmake -S "$source_root" -B "$runtime_root" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
    -DGGML_NATIVE=OFF -DGGML_OPENMP=ON -DGGML_KV260_XRT=ON \
    -DGGML_CPU_KLEIDIAI=OFF -DGGML_BUILD_TESTS=OFF -DGGML_BUILD_EXAMPLES=OFF \
    -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF \
    -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TOOLS=ON \
    >"$runtime_root-configure.log" 2>&1 || {
      cat "$runtime_root-configure.log" >&2
      die "CMake configure failed"
    }
fi
cmake --build "$runtime_root" --target llama-mtmd-cli rm08-ffn-down-helper-smoke -j"$build_jobs" \
  >"$runtime_root-build.log" 2>&1 || {
    cat "$runtime_root-build.log" >&2
    die "AArch64 runtime build failed"
  }

[[ -x "$cli" && -x "$helper" ]] || die "expected CLI/helper build outputs are missing"
env LD_LIBRARY_PATH="$runtime_root/bin" "$cli" --help >"$runtime_root-help.txt" 2>&1 || die "CLI --help failed"
for binary in "$cli" "$helper"; do
  ldd -r "$binary" >"$runtime_root-$(basename "$binary")-ldd-r.txt" 2>&1 || die "ldd -r failed for $binary"
  if grep -Eq 'not found|undefined symbol' "$runtime_root-$(basename "$binary")-ldd-r.txt"; then
    cat "$runtime_root-$(basename "$binary")-ldd-r.txt" >&2
    die "unresolved runtime dependency in $binary"
  fi
done
ldd "$cli" | awk -v library="$runtime_root/bin/libggml-cpu.so.0" \
  '$1 == "libggml-cpu.so.0" && $3 == library { found=1 } END { exit !found }' || \
  die "CLI does not resolve the patched CPU library from the RM09 build"

(cd "$runtime_root" && sha256sum \
  bin/llama-mtmd-cli \
  bin/libggml-cpu.so.0.24.0 \
  bin/libggml.so.0.24.0 \
  bin/libggml-base.so.0.24.0 \
  bin/libllama.so.0.4.1 \
  bin/libmtmd.so.0.4.1 \
  bin/libllama-common.so.0.4.1 \
  bin/rm08-ffn-down-helper-smoke > RM09_RUNTIME_ARTIFACTS.sha256)

printf 'RM09_RUNTIME_SOURCE=%s\n' "$source_root"
printf 'RM09_RUNTIME_BUILD=%s\n' "$runtime_root"
printf 'RM09_RUNTIME_SOURCE_COMMIT=%s\n' "$rm08_runtime_commit"
printf 'RM09_RUNTIME_PATCH_SHA256=%s\n' "$(sha256_of "$extent_patch")"
printf 'RM09_RUNTIME_MANIFEST_SHA256=%s\n' "$(sha256_of "$runtime_root/RM09_RUNTIME_ARTIFACTS.sha256")"
printf 'RM09_RUNTIME_ARTIFACTS=%s/RM09_RUNTIME_ARTIFACTS.sha256\n' "$runtime_root"
