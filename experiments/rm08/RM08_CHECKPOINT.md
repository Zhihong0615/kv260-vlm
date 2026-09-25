# RM08 checkpoint — 2026-09-25

## Pause point

The user asked to pause after the first real PL run because the terminal output
was too large to copy. Logs were retrieved directly over SSH and saved locally;
no further board operation is needed to preserve this checkpoint.

## Current decision and measured result

- First RM07 K16 flat-app load, UIO mapping, AXI-Lite invalid-task probe,
  unload, and starter-kit restore: **PASS**.
- Actual PL/APM clock: **99.999 MHz**. The prior 187.512 MHz figure is routed
  timing capacity, not the board clock during this run.
- Three real tensor single calls (N=1120 layer 0; N=280 layers 13 and 26)
  passed numerical thresholds. Calls took 1.653 s, 0.415 s, and 0.416 s wall.
- Five-call totals: 8.223 s (N=1120), 2.082 s (N=280).
- Representative 135-call replay: **99.013 s total** including host packing,
  sync, submit, and unpack; 86.535 s HLS wait, 11.047 s packing, 0.162 s sync,
  0.041 s submit, 1.186 s unpack. This reused layer-0 data for the 35 wide
  calls and layer-13 data for the 100 narrow calls; it did not replay 27 unique
  layer payloads.
- CPU family baseline: 250.124 s. Measured replay ratio: **2.526×**.
- Bounded XRT BO pool: 1,671,168 bytes (1.594 MiB, 408 CMA pages); lowest
  runner-sampled CmaFree: 514,100 kB. APM counted 22.539 GB of PL reads+writes.
- Standalone gate: **`GO_VLM_INTEGRATION`**. Amdahl estimate is 517.239 s for
  QID 37804, but this is not a measured VLM latency.
- No PS+PL MiniCPM-V inference, generated answer, 135 unique layer dispatch,
  actual fallback count, or full-request latency has been measured yet.

## Board state at pause

Latest direct SSH snapshot after benchmark (2026-09-25 02:45:58 UTC): boot ID
`2a931c48-99ad-4a3f-b3e1-f42634597098`; FPGA manager `operating`; RM07 UIO
absent; starter-kit restore is recorded PASS; `MemAvailable=3,289,892 kB`,
`CmaTotal=1,024,000 kB`, `CmaFree=528,768 kB`. RM07 app files remain installed
on writable root. No boot firmware, QSPI, boot files, or SD image were changed.

## Evidence and worktrees

- Results: [`RM08_RESULTS.md`](RM08_RESULTS.md)
- Recovery notes: [`recovery_cheatsheet.md`](recovery_cheatsheet.md)
- Board readiness: [`evidence/board_readiness_latest_20260925.txt`](evidence/board_readiness_latest_20260925.txt)
- Raw load/smoke log SHA-256: `18f07c28e8d57500291d65cd86bcd40366d4f2202481b5d718019d8245361890`
- Raw benchmark log SHA-256: `da5aea7b894a6e1e355a58b3d9cb08d4fa15da97a0927c68a37d61c65dcd9273`
- Research repo worktree: `/home/zhiro/.codex/worktrees/rm04-dynamic8-integration/kv260-vlm`, branch `codex/rm08-first-pl-bringup`.
- Runtime integration worktree: `/home/zhiro/.codex/worktrees/rm08-llama-ffn-down`, branch `codex/rm08-ffn-down-pl`, pinned at `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`; clean at checkpoint. No runtime code changes have been made.

## Resume from here

1. Finish the RM08 runtime interception in the dedicated llama.cpp worktree.
   Only route exact transformer `ffn_down-{0..26}` F16×F32→F32 contiguous
   shapes (`K=4304`, `N=1120` for layers 0–6; `N=280` for layers 7–26).
   Keep merger `K=17216` and unmatched shapes on CPU with explicit counts.
2. Build in a separate board-side source/build directory; do not overwrite the
   frozen CPU baseline. Verify backend dispatch and output correctness before
   timing a VLM request.
3. Run QID 37804 once with PL enabled and capture expected/actual PL calls,
   shape counts, CPU fallbacks, wall time, and answer. Compare against the
   668.35 s CPU baseline and 517.239 s Amdahl estimate; report residual.
4. Recheck board readiness immediately before loading the app. The tested
   smoke/restore path passed, but do not assume the app is currently loaded.

At the pause point the research report has uncommitted RM08 edits; raw logs are
ignored by the repository's `*.log` rule and must be force-added if included in
the milestone commit. The separate runtime worktree is untouched.
