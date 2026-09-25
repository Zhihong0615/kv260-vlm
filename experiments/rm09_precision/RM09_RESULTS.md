# RM09 precision checkpoint

## Decision

The local real-tensor gate keeps P0 as the control. P1 passes the sampled
`ffn_down-0` and `ffn_down-13` checks, but fails the RM08 limits at
`ffn_down-26`; P1 hardware synthesis remains deferred. P2 and P3 fail the
local gate on all three captured layers. P1 model-level quality is **UNKNOWN**
until the AArch64 same-binary P0/P1 request pair is run.

The RM08 local tensor limits used here are max absolute error ≤1e-3, RMSE
≤1e-4, and cosine ≥0.999. The captured reference is the corrected QID 37804
KV260 AArch64 CPU run, runtime SHA-256
`e019f99ff8c736f75785556438350d0fea8c05896cdf8adf044c60cacedbb34c`;
capture provenance and tensor checksums are in
[`../rm06/RM06_RESULTS.md`](../rm06/RM06_RESULTS.md).

| Layer | Candidate | Max abs | RMSE | Cosine | Gate |
|---|---|---:|---:|---:|---|
| 0 | P0 F16W×F32X→F32 | 1.1444e-5 | 1.8043e-7 | 0.999999999999816 | pass |
| 0 | P1 F16W×F16X→F32 | 9.8038e-4 | 5.7335e-6 | 0.999999999957155 | pass |
| 13 | P0 F16W×F32X→F32 | 1.9893e-6 | 1.0814e-7 | 0.999999999999797 | pass |
| 13 | P1 F16W×F16X→F32 | 1.9893e-6 | 1.0814e-7 | 0.999999999999797 | pass |
| 26 | P0 F16W×F32X→F32 | 3.0518e-4 | 5.3198e-6 | 0.999999999999931 | pass |
| 26 | P1 F16W×F16X→F32 | 5.2887e-2 | 1.2637e-3 | 0.999999998539487 | **fail** |

P1 at layer 26 misses both max-absolute-error and RMSE limits. Its cosine is
still 0.9999999985, so this local failure does not establish a model-quality
collapse. Among reference outputs with `abs(ref) >= 1e-4`, P1 relative-error
q50/q90/q99 are 0.0105% / 0.0711% / 0.7522%; the maximum is 24.84%. Four of
322,560 reference elements are below the denominator cutoff; their absolute
error RMSE/max are 1.2993e-4 / 1.8385e-4. The full per-layer distribution and
near-zero statistics are in [`results/precision_metrics.csv`](results/precision_metrics.csv).

The activation inputs show measured layer differences. For F16 round-trip,
layer 0 changes 25/4,820,480 values (0.000519%; X abs max 18.299), layer 13
changes 0/1,205,120 (X abs max 5.020), and layer 26 changes 29,705/1,205,120
(2.4649%; X abs max 167.697). Layer 26 X abs q99 is 36.226 and round-trip
RMSE is 0.001495. This is an observed explanation for the larger local P1
error, not an architecture claim.

P2 BF16 W/X and P3 F16 product with interleaved F16 accumulation fail the same
limits on all three layers. Their layer-26 max abs/RMSE are 0.39209/0.01006
and 0.49173/0.01109, respectively. No P1/P2/P3 HLS synthesis or route was
run. The existing P0 RM07 route remains the control: HLS compute-loop II=5,
52 inferred FP32 multipliers, 184 DSP, 73,995 LUT, 60,445 FF, 54 BRAM18, 40
URAM, estimated Fmax 265.32 MHz; the routed system used 66,603 LUT, 67,541 FF,
12,936/14,640 CLB sites, 18.5 BRAM tiles, and 40 URAM at 187.512 MHz. See
[`../rm07/RM07_RESULTS.md`](../rm07/RM07_RESULTS.md) for the full report.

## Host request and dispatch limitation

The x86 host QID 37804 baseline and the opt-in candidate both returned `G`.
The candidate log has exactly 135 target operations (five calls for each
`ffn_down-0..26`). This is only a hook smoke test: the x86 CPU fallback already
rounds F32 X into F16 scratch for this F16 weight type, so its baseline is
already P1-like. It is not a P0/P1 quality comparison against the captured
board CPU path. The actual x86 trace is in
[`results/model_q37804/f16x.log`](results/model_q37804/f16x.log); model,
mmproj, and image hashes match the frozen QID 37804 inputs.

The CLI does not expose final vision embeddings or logits. Capturing those
would require extra runtime graph instrumentation and is outside this bounded
checkpoint. The prepared AArch64 request pair captures final answer, per-run
timing, resources, and the P1 trace; embedding/logit deltas remain UNKNOWN.

## Deferred AArch64 request pair

The runtime hook is committed in the separate llama.cpp worktree as
`eb09ee7bbcfdab1f8e31fa215c7e6c1965507135` on `codex/rm09-p1-software`.
[`runtime-hook.patch`](runtime-hook.patch) preserves the source diff. It is
opt-in with `RM09_F16X_SIM=1`, matches only canonical numbered
`ffn_down-0..26` F16W/F32X/F32Y contiguous operations of K=4304, M=1152, and
converts only a private X copy through F16 and back to F32 before the AArch64
llama-file F32 matmul. If that AArch64 path is unavailable, it aborts instead
of silently using another path. Each matched call logs one
`RM09_F16X_APPLIED` marker.

The CPU-only AArch64 build is from the RM08 runtime base plus this commit. It
uses generic AArch64/Armv8-A, Clang 21.1 via Zig cross tooling, llama-file ON,
OpenMP/CUDA/Vulkan OFF. This differs from the frozen RM08 build, so the
quality comparison must use the same binary for both runs. The stripped
transfer archive is `/tmp/rm09-f16x-aarch64-eb09ee7.tar.gz` (SHA-256
`c9f4184da002829edb0abae327822bb4896bef7d79332c132e6162c3851b9246`, 5.0 MB).
After owner coordination, it was copied as user `ubuntu` to
`/tmp/rm09-f16x/aarch64.tar.gz` and unpacked to `/tmp/rm09-f16x/bin`; the
runner is `/tmp/rm09-f16x/run_q37804_aarch64_cpu_pair.sh`. Archive, runner,
and all seven staged ELF hashes were verified. The board owner reported the
starter kit/FCLK0 idle before staging. No CLI, `xmutil`, FCLK, or FPGA action
was performed during staging.

Staged stripped payload hashes:

| File | SHA-256 |
|---|---|
| `llama-mtmd-cli` | `9da96349e42cc9ee3d8ee25fe2d98795bf87905cbc538a1bc9710cdc284f4317` |
| `libggml-base.so.0.24.0` | `c7c1348ce81369d20d6fadba2ec0b296e3458ce9853a176c5baaffa0c8f20f53` |
| `libggml-cpu.so.0.24.0` | `ca9eb48e96d5c57b92b4910a0e599ba61aeb88fb4cb2b7c10096a1a8e2e22619` |
| `libggml.so.0.24.0` | `98d5ece92590e605b3045332a860f795ff6f6ea5dfb394a78105be314e4f1e74` |
| `libllama-common.so.0.4.1` | `36c40242a061fcfdb3e50f508e707d9a8e568328c792201df14522dce8e85a18` |
| `libllama.so.0.4.1` | `a133474fb4f35e02674b569f86515b2ec1efb2c0eda584e00fcf5fcc71553160` |
| `libmtmd.so.0.4.1` | `355739b8e578f66acf32a4d4f55de92c6d1c90b379f4911cd5333d69a7652d7f` |

The unstripped build resides at
`/home/zhiro/.codex/worktrees/rm09-p1-software/build-rm09-aarch64-v2/bin`;
its CLI SHA-256 is `e3d89fd935dd9af7edb9765be9a4045c2a51d9197fcefcf3d938d7116f34ff88`.
The executable embeds that build directory in RUNPATH, so the board runner sets
`LD_LIBRARY_PATH=/tmp/rm09-f16x/bin` to load the staged copies.

Run `bash /tmp/rm09-f16x/run_q37804_aarch64_cpu_pair.sh` only after the board
owner releases it. The script first runs
P0 with `RM09_F16X_SIM` unset, then P1 with it enabled, with identical binary,
libraries, model, mmproj, image, seed, and four-thread settings. It stores
separate logs and requires five P1 trace calls per numbered layer (135 total).
The captured RM06 CPU request took 668 s; plan roughly 11 minutes per request
plus setup, with each invocation capped at 1,200 seconds. Actual duration may
differ because this cross build uses different compiler/build flags.
