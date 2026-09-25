# RM09 same-runtime CPU controls

Board run directory: `/home/ubuntu/kv260-vlm-p2-cpu/runs/rm09-cpu-same-runtime-20260925T130058Z`.
Both requests ran on the restored starter image using the exact RM09 native
runtime artifacts used by the PL run. This control explicitly set
`RM08_FFN_DOWN_PL=0`, unset the PL selection/trace variables, passed
`--device none -ngl 0`, closed stdin, and bounded each process with
`timeout --signal=TERM --kill-after=10s 1800s`. It used no sudo and made no
overlay or board configuration changes. Both processes exited zero, produced
zero `RM08_PL_CALL` trace records, and returned the expected full text answers.

## Pinned inputs and runtime

- CLI SHA-256: `6a45ea3647b1db19d06408441729681d19966af569040e4577b1410b803d7254`
- CPU library SHA-256: `b44c771488d7fa63e73d1ddf0f15427f1943000fc969d4fe4cd42102e1c777b7`
- Model SHA-256: `8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773`
- MM projection SHA-256: `ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293`
- QID38299 image SHA-256: `4365f84b5d2cbc5c740bafde088b1aeaf5c7b8326c8b9b5bfe2a529f9bc7a256`
- QID35419 image SHA-256: `f703a5ce6bbf7c1aa1dd11fda26a7a30323913d404d771d51deba387c840c5f6`
- Both: `-t 4 -tb 4 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4`

The exact prompts and complete CLI command lines are in `raw/driver.log` and
the timed-command records. Raw stderr retains inference logs; stdout retains
the full generated answers. Board-side digests are in
[BOARD_SHA256SUMS](BOARD_SHA256SUMS), which match the copied raw files;
`sha256sum -c SHA256SUMS` passes. The manifest SHA-256 is
`c0f49cb331196c0cda8c821ad1a070906a4cb08f5341694e1daaf64301c58d28`.

## Same-runtime CPU versus RM09 PL

Process wall and peak RSS are from `/usr/bin/time -v`. Wall reduction is
`1 - PL process wall / CPU process wall`.

| QID | Same-runtime CPU wall | RM09 PL wall | Wall reduction | CPU peak RSS | PL peak RSS | CPU answer / PL answer |
|---:|---:|---:|---:|---:|---:|---|
| 38299 | 368.51 s | 299.14 s | 18.8% | 1,855,720 KiB | 1,856,120 KiB | `3` / `3` |
| 35419 | 822.35 s | 652.32 s | 20.7% | 1,862,020 KiB | 1,862,368 KiB | `SHERIFF'S` / `SHERIFF'S` |

This isolates the effect of PL acceleration against the same native CPU
runtime artifacts. The previously quoted CPU walls, 368.19 s and 850.48 s,
used an earlier CPU-library build; against those older figures the reductions
were 18.8% and 23.3%, respectively. For QID35419, the same-runtime control
reduces the measured PL gain to 20.7%.

These are full VLM output comparisons. They do not provide elementwise
real-tensor validation for the newly observed numeric extents.

## Board state

Boundary snapshots in `raw/driver.log` show `fpga_manager=operating`, FCLK0
`99,999,999 Hz`, and swap free `0` before and after the requests. `CmaFree`
was 555,172 kB before QID38299, 579,432 kB after QID38299, 572,296 kB after
QID35419, and 572,380 kB at the final snapshot. It was not monitored
continuously, so the true in-run minimum is unknown. No RM09 overlay was loaded
or unloaded during this CPU control.
