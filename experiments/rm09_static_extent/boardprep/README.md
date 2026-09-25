# RM09 static extent board prep

This directory contains the staged board procedure for the single RM09 static
extent image routed at PL0=100 MHz. The scripts are prepared for review; this
task does not load the image or run either VLM request.

## Pinned design and runtime

- Route source commit: `2522fc2` (`codex/rm09-static-board`).
- Bitstream package app: `kv260-rm09-static-extent`.
- `kv260-rm09-static-extent.bit.bin` SHA-256:
  `819b088199ac4346c1eb9b7bb65ade42afe8f95eaeec02cca4bc6bdd2bb0d87b`.
- `kv260-rm09-static-extent.dtbo` SHA-256:
  `85fd0a2e2186886d8d52178c0934ba51585c37c28e5dd54a1c5536f2e506521e`.
- `shell.json` SHA-256:
  `802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344`.
- Package `SHA256SUMS` SHA-256:
  `cae3a750941c191ba17f1c9cbfacaa5a5093ecc41eaa9a99f1ba1f00a0134a66`.
- Runtime base source commit: `7c9c15992ff6df6d6fa10636b430e170a3dd2934`.
- `runtime_dispatch.patch` SHA-256:
  `22d96ed06be3b8d6c2dd8f841785fdd90981932fe0c3754189dfe710493dc32d`.
- RM09 identity uses UIO name `vision_ffn_down_tile_0`, compatible
  `xlnx,vision-ffn-down-tile-1.0`, AXI-Lite window `0xa0010000–0xa001ffff`,
  and invalid task return `-4`. There is no immutable IP-ID register.

The runtime patch admits the measured wide and narrow extents, tracks every
successful PL extent, requires the frozen QID histogram, and counts the two
unmatched merger fallbacks per media group. The guarded runner also checks each
per-call record, all 27 layer counters, output answer, runtime artifact manifest,
and pinned route package before accepting evidence.

Before load and again immediately before each real tensor/VLM DMA, the runner
requires the exact 1,671,168-byte page-rounded RM09 XRT BO pool plus an 8 MiB
CMA margin (9,824 KiB total). The RM08 board run observed `CmaFree` as low as
13 MiB, so the guard leaves that known operating point available. The runtime
still validates each XRT BO allocation and the strict PL/fallback counters;
allocation failure falls back and causes the guarded request to fail into the
starter-kit restoration path.

## Tensor evidence and required correctness check

The existing real tensor bundle covers only layer 0/N1120 and layers 13 and
26/N280. Those three frozen tensors remain checked by the standalone helper.
There are no captured real tensors for the new N1008, N1024, N1056, N252, N256,
or N264 extents. Therefore QID38299 and QID35419 require full VLM output
comparisons; the runner pins the images, prompts, deterministic decode settings,
and expected answers (`3` and `SHERIFF'S`).

Expected per-request PL histograms:

- QID38299, 3 media groups: `N1024=14`, `N1056=7`, `N256=40`, `N264=20`;
  unmatched merger fallback calls: 6 total (3 ViT merger, 3 MM down).
- QID35419, 7 media groups: `N1008=49`, `N252=140`;
  unmatched merger fallback calls: 14 total (7 ViT merger, 7 MM down).

The runner validates fallback input shapes/dtypes too: QID38299 uses ViT N256
twice and N264 once, plus MM N64 twice and N66 once; QID35419 uses ViT N252
and MM N63 seven times each.

## Staging and guarded board invocation

Build the runtime on the board as `ubuntu`, without sudo:

```sh
ssh kria 'bash /tmp/rm09-static-extent/runtime/build_runtime.sh'
```

Before a board run, copy this `boardprep` directory, the pinned route package,
and the RM08 restore/diagnostics helpers to the matching paths under
`/tmp/rm09-static-extent/`. Fill the four runtime SHA placeholders in
`run_board_experiment.sh` from the completed runtime build. Review those hashes
and the worktree commit before loading. The only privileged invocation is:

```sh
sudo bash /tmp/rm09-static-extent/boardprep/run_board_experiment.sh
```

That guarded command checks the starter image and 100 MHz FCLK at entry, arms
the 4200-second RM08-proven restore timer before changing the app, checks the
UIO/APM identity and AXI-Lite invalid-task result, runs the frozen real-tensor
helper and both pinned VLM requests, then restores the starter image and removes
the staged package if it installed it. A failed explicit restore leaves the
timer armed. This task stops before that privileged command.
