# RM10 board-preparation package

This worktree contains a guarded board procedure for the corrected RM10 A route. The first route is explicitly invalid for board use: its dependence schedule showed the accumulator load at `ST_26` and store at `ST_35` despite a declared distance of five. No provisional RM10 bitstream is included or staged. The already-known-good RM09 static-control `.bit.bin` is staged for a possible paired control but ignored by Git's `*.bin` rule; its pinned SHA is `819b088199ac4346c1eb9b7bb65ade42afe8f95eaeec02cca4bc6bdd2bb0d87b`.

## Frozen inputs

- Runtime: RM09 CLI `6a45ea3647b1db19d06408441729681d19966af569040e4577b1410b803d7254`, CPU library `b44c771488d7fa63e73d1ddf0f15427f1943000fc969d4fe4cd42102e1c777b7`, runtime manifest `e35e0b1ff5ae5c3630af49c20f5494dd5ce82753f33374b216c36ac1b1cb95a9`.
- Standalone benchmark: RM08 `ffn_down_bench`, SHA-256 `c687a693d20a95c81787754aa07b49f51e3cf868116f8652aa22f6d4f30ac914`.
- Model, mmproj, QID 37804 image, and all nine real `ffn_down-{0,13,26}` tensor files are pinned by `run_candidate.sh` and `real_tensor_hashes.sha256`.
- Numerical gate remains `max_abs <= 1e-3`, `RMSE <= 1e-4`, `cosine >= 0.999`. Standalone command counts are frozen: layer 0 (`N=1120`) 35 stage / 315 compute; layers 13 and 26 (`N=280`) 9 / 81 each.
- The integrated request checks answer `G`, 135 PL calls, 10 expected CPU fallbacks, and the frozen layer/call distribution. It records CLI/library hashes, PL trace, wall time, latency/perf output, CMA snapshots, and restore evidence.
- RM08 historical QID 37804 result is 522.34s, from CLI/lib hashes `73e4c882…` / `7351973a…`; it is a cross-build reference. `run_static_control_if_near.sh` conditionally permits one same-RM09-binary static request only if the RM10 result is 496.2–548.5s (±5% of 522.34s).

## Corrected-route gate and run order

Do not run either board script until the scheduler authorizes the exact corrected `.bit.bin` SHA and rollback plan. The candidate script currently fails closed with pending route identity fields. After corrected RTL schedule/dependence validation and route review, replace those fields with the route worker's exact source commit, IP ZIP SHA, XSA SHA, source `.bit` SHA, and Bootgen `.bit.bin` SHA. Place only the matching `.bit`, `.bit.bin`, plus the hash-checked RM10 DTBO and `shell.json` under `/tmp/rm10-boardprep/package/kv260-rm10-a-ra/`. Recompute the DTBO/package checksum file only if the route worker changes those files.

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
