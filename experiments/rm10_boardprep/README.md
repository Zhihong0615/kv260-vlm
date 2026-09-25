# RM10 board-preparation package

This worktree contains a guarded board procedure for the corrected RM10 A route. The first route is explicitly invalid for board use: its dependence schedule showed the accumulator load at `ST_26` and store at `ST_35` despite a declared distance of five. The corrected candidate now passes numeric evaluation and RTL co-simulation; full implementation closed at 100 MHz with WNS `+3.563 ns`, WHS `+0.010 ns`, and no congestion windows above level 5. The already-known-good RM09 static-control `.bit.bin` is staged for a possible paired control but ignored by Git's `*.bin` rule; its pinned SHA is `819b088199ac4346c1eb9b7bb65ade42afe8f95eaeec02cca4bc6bdd2bb0d87b`.

## Frozen inputs

- Runtime: RM09 CLI `6a45ea3647b1db19d06408441729681d19966af569040e4577b1410b803d7254`, CPU library `b44c771488d7fa63e73d1ddf0f15427f1943000fc969d4fe4cd42102e1c777b7`, runtime manifest `e35e0b1ff5ae5c3630af49c20f5494dd5ce82753f33374b216c36ac1b1cb95a9`.
- Standalone benchmark: RM08 `ffn_down_bench`, SHA-256 `c687a693d20a95c81787754aa07b49f51e3cf868116f8652aa22f6d4f30ac914`.
- Model, mmproj, QID 37804 image, and all nine real `ffn_down-{0,13,26}` tensor files are pinned by `run_candidate.sh` and `real_tensor_hashes.sha256`.
- Numerical gate remains `max_abs <= 1e-3`, `RMSE <= 1e-4`, `cosine >= 0.999`. Standalone command counts are frozen: layer 0 (`N=1120`) 35 stage / 315 compute; layers 13 and 26 (`N=280`) 9 / 81 each.
- The integrated request checks answer `G`, 135 PL calls, 10 expected CPU fallbacks, and the frozen layer/call distribution. It records CLI/library hashes, PL trace, wall time, latency/perf output, CMA snapshots, and restore evidence.
- RM08 historical QID 37804 result is 522.34s, from CLI/lib hashes `73e4c882…` / `7351973a…`; it is a cross-build reference. `run_static_control_if_near.sh` conditionally permits one same-RM09-binary static request only if the RM10 result is 496.2–548.5s (±5% of 522.34s).

## Corrected-route gate and run order

The candidate script is pinned to the corrected route, but remains subject to exact-SHA scheduler authorization before any board load:

- Source/IP commit `3602eafa7de5cee187b79f8e28c186a19f6f6133`; source SHA-256 `31a7b26f9bf28c0ad57892184ed30b42126162111fe4c4bda82aa7847754319a`.
- IP `component.xml` SHA-256 `fae7fde4af5b3f5a1237d5e7717ea97622a9a8c6107ba96c97bfe6bb19feda56`; exported IP ZIP SHA-256 `b54c4ac0a15dc4501c3d1d470eeb2664fe9e2e60cf0d9ba7a0cfd9fdcca82e6b`.
- Routed `.bit` SHA-256 `18ba853551f85ce1814332eacd370264696a93423fbf5a408e028b307c18ac23`; XSA SHA-256 `a85ff605c6e5dbe52a4e413ce38499b70d6c1bc857509ff5433d1f03f5934e0b`.
- Bootgen v2024.2 output `.bit.bin` SHA-256 `722387cc80b345f0b7b29bdffe61911707cf12c5c25e42867d339b4a0c6fb5d7` (generated from the packaged relative-path BIF).

The package preserves the `.bit`, `.bit.bin`, and BIF recipe with a checksum manifest. Do not substitute a different image or alter these pins. The RM10 DTBO and `shell.json` hashes remain the checked template hashes.

Stage the package and helpers without root privileges. Only after exact-SHA authorization, invoke the integrated candidate procedure from the board's terminal:

```bash
sudo bash /tmp/rm10-boardprep/boardprep/run_candidate.sh
```

That single procedure runs the three frozen standalone tensors, then one QID 37804 request. It first checks all input hashes, starter-app/FCLK/CMA state, then arms a 4200-second RM09-known-good restore timer before unloading the current app. It does not change clocks, boot files, drivers, or the kernel. A failure leaves the timer armed. Confirm `starter_kit_restore=PASS` and the run's evidence directory before considering another app load.

If and only if the completed candidate request is within the threshold, and the owner authorizes the additional load, run the same-runtime static control with that candidate evidence directory:

```bash
sudo bash /tmp/rm10-boardprep/boardprep/run_static_control_if_near.sh \
  /home/ubuntu/kv260-vlm-p2-cpu/runs/rm10-a-ra-q37804-<UTC-stamp>
```

Outside the window, the script reports `SKIP` before app changes. Keep the 522.34s RM08 cross-build comparison distinct from any paired RM09-runtime control. No media-group/request sweep is part of this procedure.
