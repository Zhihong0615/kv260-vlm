# QID37804 P0 startup failure

The first authorized QID37804 P0/P1 CPU precision pair stopped in P0 after 1.81 seconds, before model loading or operator execution. llama.cpp aborted in `common_params_fit_impl` while reading device memory for automatic argument fitting:

```text
common_init_: fitting params to device memory ...
common_params_fit_impl: getting device memory data for initial parameters:
free(): invalid pointer
Command terminated by signal 6
```

P0 exited 134 at 2026-09-25T09:01:18Z. P1 did not run. The staged CLI was SHA-256 `9da96349e42cc9ee3d8ee25fe2d98795bf87905cbc538a1bc9710cdc284f4317`. Runtime help documents `--fit [on|off]`, so one retry added `--fit off` to the otherwise-identical P0/P1 arguments.

The raw board log, run metadata, and pair wrapper log were copied from the board and SHA-256 checked against their source copies:

| File | SHA-256 |
| --- | --- |
| `p0.log` | `213dabb8297829b33ff49c9deb1801f0fd3f24626e2972e41696b0aab0622522` |
| `run_meta.txt` | `f5fba1216d72d4dcff18de93c45eb437eafbf51e311508ffdd0e5b572953c99b` |
| `pair-launch.log` | `158c5e886aa4a46ec8df5cfd913e287d1c6977cc5704e186a427924dae4b704a` |

## Retry with device-memory fitting disabled

The retry began at 2026-09-25T09:08:40Z in `/home/ubuntu/kv260-vlm-p2-cpu/runs/rm09-q37804-p0-p1-20260925T090754Z`. It exited 134 one second later. The model loader read GGUF metadata and reported architecture `qwen35`; it then aborted during metadata dumping, before tensor/model load or operator execution:

```text
llama_model_loader: loaded meta data with 41 key-value pairs and 320 tensors
llama_model_loader: - kv 0: general.architecture str = qwen35
free(): invalid pointer
Command terminated by signal 6
```

P1 did not run. This retry locates the fault later than the original auto-fit crash, but still before inference. The raw files below are SHA-256 checked against their source copies on the board:

| File | SHA-256 |
| --- | --- |
| `../rm09-q37804-p0-20260925T090754Z/p0.log` | `c38cdf7f279a957bae57d3318cb633436e980fccfb7e6043ba29315a41f72ac1` |
| `../rm09-q37804-p0-20260925T090754Z/run_meta.txt` | `bfc12e9c23eda42205439092f168214c535a37aa401e1a58801dba4b8dcf59ac` |
| `../rm09-q37804-p0-20260925T090754Z/pair-launch.log` | `f20dcf63f7e9fa06cd9fdf671afc94b3de4c1e7b25c8d2d1431a96ee7e957dde` |
