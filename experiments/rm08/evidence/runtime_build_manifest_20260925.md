# RM08 llama.cpp PL-hook build evidence — 2026-09-25

## Source and isolated board build

- Runtime repo: `/home/zhiro/.codex/worktrees/rm08-llama-ffn-down`
- Branch: `codex/rm08-ffn-down-pl`
- Final source HEAD: `c302d8e04be975cff747fedeef07a5877cf4b2c1`
- Included commits: `1a90d48` (hook and helper), `c5b0f09` (exit registration), `c302d8e` (XRT C API link)
- Board source copy: `/home/ubuntu/kv260-vlm-p2-cpu/rm08-runtime-src-1a90d48`
- Board build tree: `/home/ubuntu/kv260-vlm-p2-cpu/rm08-build-1a90d48`
- The frozen CPU baseline at `/home/ubuntu/kv260-vlm-p2-cpu/runtime-src` and `build-cpu` was not modified.
- Configure used AArch64, Release, shared libraries, OpenMP enabled, native CPU tuning disabled, tests/examples/server disabled, tools enabled, and `GGML_KV260_XRT=ON`.

Exact configure/build commands:

```sh
src=/home/ubuntu/kv260-vlm-p2-cpu/rm08-runtime-src-1a90d48
build=/home/ubuntu/kv260-vlm-p2-cpu/rm08-build-1a90d48
cmake -S "$src" -B "$build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
  -DGGML_NATIVE=OFF -DGGML_OPENMP=ON -DGGML_KV260_XRT=ON \
  -DGGML_CPU_KLEIDIAI=OFF -DGGML_BUILD_TESTS=OFF -DGGML_BUILD_EXAMPLES=OFF \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF \
  -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TOOLS=ON
cmake --build "$build" --target llama-mtmd-cli -j6
```

## Build and smoke results

- CMake configure: PASS (`runtime_build_config_20260925.log`)
- `llama-mtmd-cli` AArch64 compile/link: PASS, 75/75 Ninja actions (`runtime_build_20260925.log`)
- CLI `--help`: PASS, exit status 0, 370 lines (`runtime_mtmd_help_20260925.txt`)
- `ldd -r` for CLI and helper harness: no unresolved symbols; both resolve `libxrt_core.so.2` and `libxrt_coreutil.so.2`.
- XRT C API symbols are provided by `libxrt_core`, so CMake links `xrt_core`; `libxrt_core` brings in `xrt_coreutil`.
- Helper harness compiled successfully as AArch64, but was not executed. No bitstream was loaded and no VLM request was run in this build task.

Board artifact SHA-256:

```text
llama-mtmd-cli                   73e4c8826a159e1bcf420b57cce20201353c611d57af15cdb6200f60ec5f00d0
libggml-cpu.so.0.24.0            7b1b4e11740d62769af5451e9b5f5534d622694261a813760291c00eb8fb6978
rm08-ffn-down-helper-smoke       c18b90b8a1f94b16135b015ffc45181396cb80aa19af3b20ab82e6c036bd05ef
libxrt_core.so.2.13.0            d49e9682fccaed6d554b3ad39091ab2654e793bbcf816f4ad95a4314ad3dfbbe
kv260_ffn_down.c                 ddb4a9af159664e581414ead7e08a07f7eaf91bca3b6ccfa822fd03433c59622
ggml-cpu/CMakeLists.txt          60c87758b961694f3098cc8f9c4325e00afb9978638b90e5938520f0755e3103
```

## Next authorized helper validation command

After the scheduler loads RM07 using the established load/restore path, run the direct same-hook validation against the three staged real tensors. The `0` media-group setting disables the full-request 135-call expectation check for this standalone helper process.

```sh
sudo env RM08_FFN_DOWN_PL=1 RM08_PL_EXPECTED_MEDIA_GROUPS=0 \
  RM08_PL_TRACE=/tmp/rm08-helper-smoke.log \
  /home/ubuntu/kv260-vlm-p2-cpu/rm08-build-1a90d48/bin/rm08-ffn-down-helper-smoke \
  /tmp/rm08-deploy/tensors
```

The harness checks captured CPU output for `ffn_down-0` (N=1120), `ffn_down-13` (N=280), and `ffn_down-26` (N=280), reporting max absolute error, RMSE, and cosine similarity for each. This direct helper smoke exercises the XRT path, so it must only run while RM07 is loaded.
