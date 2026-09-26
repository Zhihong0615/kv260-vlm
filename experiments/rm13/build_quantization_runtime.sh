#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ $# -ne 2 ]]; then
    printf 'Usage: %s CLEAN_LLAMA_CPP_SOURCE_DIR BUILD_DIR\n' "$0" >&2
    exit 2
fi
runtime_source="$(cd "$1" && pwd)"
build_dir="$2"
if [[ "$build_dir" != /* ]]; then
    build_dir="$(pwd)/$build_dir"
fi

expected_commit="7ab4ee7baad2d920464cbacfad4f4b07cf111fd2"
actual_commit="$(git -C "$runtime_source" rev-parse HEAD)"
if [[ "$actual_commit" != "$expected_commit" ]]; then
    printf 'Expected llama.cpp commit %s, got %s\n' "$expected_commit" "$actual_commit" >&2
    exit 1
fi
if ! git -C "$runtime_source" diff --quiet || ! git -C "$runtime_source" diff --cached --quiet; then
    printf 'Source tree must be clean before applying the recorded patch\n' >&2
    exit 1
fi
git -C "$runtime_source" apply --check "$repo_root/experiments/rm13/quantization_runtime.patch"
git -C "$runtime_source" apply "$repo_root/experiments/rm13/quantization_runtime.patch"

tools_setup="$repo_root/../../kv260-vlm/env/setup_host_tools.sh"
if [[ -f "$tools_setup" ]]; then
    # shellcheck disable=SC1090
    source "$tools_setup"
fi

cmake -S "$runtime_source" -B "$build_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DGGML_NATIVE=OFF \
    -DGGML_OPENMP=ON \
    -DGGML_CUDA=OFF \
    -DLLAMA_BUILD_TOOLS=ON \
    -DLLAMA_BUILD_SERVER=OFF \
    -DLLAMA_BUILD_TESTS=OFF \
    -DCMAKE_C_FLAGS=-ffp-contract=off \
    -DCMAKE_CXX_FLAGS=-ffp-contract=off
cmake --build "$build_dir" --target llama-mtmd-cli -j"${BUILD_JOBS:-8}"
