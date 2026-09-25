# RM08 OpenMP fallback race diagnosis and fix

Date: 2026-09-25

## Diagnosis

The stalled PID 190661 was not waiting for stdin. The captured stack is inside
`mtmd_batch_encode` / `clip_encode`, with the main thread in
`tinyBLAS<4,6,4>::gemm` through `llamafile_sgemm` and
`ggml_compute_forward_mul_mat`. Three worker threads were asleep in libgomp
futex waits. The board's `time` and per-thread CPU times were unchanged across
the later snapshots. See `live_stall_gdb_190661_20260925.txt`.

The RM08 hook used `threadpool->current_chunk` both for its shared handled
status and for ggml CPU matmul's chunk scheduling. On an offload fallback,
thread 0 could read zero after the first barrier and enter CPU MUL_MAT. That
code resets `current_chunk` before its own barrier. A slower worker could then
read the new nonzero value and return from the node, leaving thread 0 waiting
at the CPU matmul barrier. The observed tinyBLAS/libgomp stack matches this
race.

Commit `8ec4e6181f632399444fdba18c5faf421736f646` snapshots the handled status
into a thread-local value after the first barrier, then adds a second barrier
before any worker branches into either PL return or CPU fallback. Thus no
worker can read `current_chunk` after CPU MUL_MAT reuses it.

Commit `7c9c15992ff6df6d6fa10636b430e170a3dd2934` corrects full-request
expectations: 135 numbered PL calls (35 N=1120, 100 N=280), plus five each of
the exact ViT merger (`K=17216/M=1152/N=280`) and mm.down
(`K=4608/M=1024/N=70`) CPU fallbacks, for 145 matching-name calls. The summary
adds `expected_vit_merger_cpu` / `vit_merger_cpu` and
`expected_mm_down_cpu` / `mm_down_cpu` fields; `expected_merger_cpu` / `merger_cpu`
now count both fallback shapes.

## Verification

- Board-side incremental AArch64 build: PASS, 13/13 Ninja actions.
- `llama-mtmd-cli --help`: PASS, 370 lines.
- `ldd -r llama-mtmd-cli`: no unresolved symbols.
- A tiny CPU-only ggml graph ran 20 times with four threads. Each iteration
  executed an unnumbered `ffn_down` MUL_MAT that fell back to CPU, followed by
  another F16 x F32 MUL_MAT. `timeout 20s` exited 0; output was finite
  (`0.00419746`) and there were 20 fallback trace lines.
- The smoke used a deliberately unsupported small shape, so it did not call
  XRT, allocate DMA BOs, load a bitstream, or interact with the live VLM PID.

## Board artifacts

The hook is in `libggml-cpu.so.0.24.0`; the CLI executable is unchanged.

- CLI: `/home/ubuntu/kv260-vlm-p2-cpu/rm08-build-1a90d48/bin/llama-mtmd-cli`
- CLI SHA-256: `73e4c8826a159e1bcf420b57cce20201353c611d57af15cdb6200f60ec5f00d0`
- Updated library SHA-256: `7351973a8d004b7380f27dd0849aa4d2965e4c91b9f473d99696efb8cbf2a265`
- Previous CLI and library were preserved under
  `/home/ubuntu/kv260-vlm-p2-cpu/rm08-old-artifacts-1a90d48/`. The old library
  SHA-256 is `7b1b4e11740d62769af5451e9b5f5534d622694261a813760291c00eb8fb6978`.
- The incremental build source copy is
  `/home/ubuntu/kv260-vlm-p2-cpu/rm08-runtime-src-1a90d48`; its
  `RM08_SOURCE_COMMIT.txt` records commit `7c9c159...` and the two changed C
  files match the committed source hashes.

The old full-build evidence remains intact; the new incremental build log,
fallback smoke source/trace, and GDB stack are saved alongside this file.
The live process was not restarted or signaled, and no bitstream operation was
performed during this diagnostic/fix task.
