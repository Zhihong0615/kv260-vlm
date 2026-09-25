# QID38299 on RM07 at 100 MHz: zero PL coverage

Board run: `/home/ubuntu/kv260-vlm-p2-cpu/runs/rm09-pl-q38299-q35419-20260925T091523Z`. The starter-kit was unloaded and the original RM07 app was loaded under a 3000-second rollback timer. RM07 remained at FCLK0 `99,999,999 Hz`, below the `187,512,000 Hz` route ceiling. The standalone helper's three real-tensor checks passed. The frozen QID38299 request used four threads and the expected three media groups.

The answer was `3` as expected. The PL trace records 87 dispatches: 81 numbered FFN calls and six merger calls. All 87 fell back to CPU, so this run is not a PS+PL measurement. The strict expected-coverage check stopped before QID35419. Starter-kit restoration passed at 09:22:13Z; FCLK0 returned to `99,999,999 Hz` and FPGA manager state was `operating`.

## Numbered calls

Every numbered call had `K=4304`, `M=1152`, dtype `f16/f32/f32`, status `CPU_FALLBACK`, and reason `layer_extent_mismatch`.

| Layers | N distribution per layer | Calls |
| --- | --- | ---: |
| 0–6 | N=1024 twice, N=1056 once | 21 |
| 7–26 | N=256 twice, N=264 once | 60 |

Totals: N=1024 14 calls; N=1056 7; N=256 40; N=264 20.

## Merger fallbacks

All six had status `CPU_FALLBACK`, reason `unmatched_merger`, dtype `f16/f32/f32`:

1. K=17216, M=1152, N=264
2. K=4608, M=1024, N=66
3. K=17216, M=1152, N=256
4. K=4608, M=1024, N=64
5. K=17216, M=1152, N=256
6. K=4608, M=1024, N=64

Trace summary: `actual_calls=87`, `actual_PL=0`, `cpu_fallbacks=87`, `wall_ms=0.193`, `pack_ms=0`, `submit_ms=0`, `kernel_ms=0`.

## Timing and resource use

llama.cpp reported total inference time `395.489 s`, including `377.199 s` prompt evaluation for 240 tokens and `0.327 s` evaluation for one output token. `/usr/bin/time` measured `402.26 s` wall and `1,851,044 KiB` maximum RSS. The matched CPU baseline was `368.19 s` wall, so the board request with the PL app loaded but zero PL dispatches took 9.3% longer end to end. It should be treated as CPU fallback behavior, not accelerator performance.

At request completion and restore, swap remained zero. The driver log records `starter_kit_restore=PASS`, FCLK0 `99,999,999 Hz`, and FPGA manager `operating`.

## Source files

The full trace SHA-256 is `4adc72a2fa36891efe4afc5dc410a533121a7b0e544980c505a6bd1b588500a2`; its local copy matches the board source. All eight copied result files were hash checked against the board before commit; their hashes are in `../SHA256SUMS.txt`.
