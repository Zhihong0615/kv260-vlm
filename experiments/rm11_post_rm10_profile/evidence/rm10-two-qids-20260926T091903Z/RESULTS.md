# RM10 two-request board validation

Board run: `/home/ubuntu/kv260-vlm-p2-cpu/runs/rm10-a-ra-q38299-q35419-20260926T091903Z` on `kria`, 2026-09-26 09:19:03–09:34:15 UTC. The approved RM10 image was loaded once, both frozen requests ran in that session, and starter-kit was restored once. Runner status: `rm10_multi_request_board_run=PASS`, `starter_kit_restore=PASS`, `run_exit_status=0`. `CmaFree` after restoration was 651,908 kB, `fclk0=99,999,999 Hz`, `fpga_manager=operating`.

## Frozen artifacts and requests

RM10 source commit `3602eafa7de5cee187b79f8e28c186a19f6f6133`; source SHA-256 `31a7b26f9bf28c0ad57892184ed30b42126162111fe4c4bda82aa7847754319a`; pinned RM10 `.bit.bin` SHA-256 `722387cc80b345f0b7b29bdffe61911707cf12c5c25e42867d339b4a0c6fb5d7`. The run driver records the IP component/package/XSA/DTBO/shell hashes, RM09 CLI and CPU library hashes, and model/mmproj hashes in `raw/driver.log`.

| QID | Input image SHA-256 | Media groups | Expected = observed answer | Exit | Process wall | Peak RSS | Major faults | File-system inputs |
|---|---|---:|---|---:|---:|---:|---:|---:|
| 38299 | `4365f84b5d2cbc5c740bafde088b1aeaf5c7b8326c8b9b5bfe2a529f9bc7a256` | 3 | `3` | 0 | 285.53 s | 1,855,980 KiB | 7,144 | 142,136 |
| 35419 | `f703a5ce6bbf7c1aa1dd11fda26a7a30323913d404d771d51deba387c840c5f6` | 7 | `SHERIFF'S` | 0 | 619.70 s | 1,862,332 KiB | 63 | 124,736 |

## PL coverage and family timing

Call and histogram counts are from the driver summaries and full `RM08_PL_CALL` trace. Every numbered down call reached PL with the expected per-layer extent histogram; only the merger calls were CPU fallback (`reason=unmatched_merger`). All 27 layers passed their expected coverage check.

| QID | Total calls | Numbered PL calls | Merger CPU fallbacks | PL extent histogram | Dispatch wall sum | Kernel | Packing | Sync to/from | Submit |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 38299 | 87 | 81 (3/layer) | 6 | N1024=14, N1056=7, N256=40, N264=20 | 45.911267 s | 38.728162 s | 6.396589 s | 0.051 / 0.045 s | 0.023 s |
| 35419 | 203 | 189 (7/layer) | 14 | N1008=49, N252=140 | 104.584825 s | 88.081363 s | 14.712967 s | 0.123 / 0.108 s | 0.057 s |

The dispatch wall sum is the full family call-wall sum from the trace, including brief merger-fallback dispatch intervals. PL kernel time is nested in the call wall; the family and kernel values do not add to request wall. The RM09 static comparison had the same pinned runtime and exact requests: Q38299 299.14 s request / 55.250 s family / 47.980 s kernel / 6.451 s pack; QID35419 652.32 s / 125.625 s / 109.115 s / 14.718 s. Thus family speedup is 1.203x and 1.201x; end-to-end wall speedup is 1.048x and 1.053x, respectively. The same-runtime CPU request walls were 368.51 s and 822.35 s, so RM10 is 22.5% and 24.6% faster than CPU. RM10 full-request wall is 4.55% and 5.00% below RM09 static.

## Major-fault observations for these exact requests

| QID | Mode | Process wall | Major faults | File-system inputs | Note |
|---|---|---:|---:|---:|---|
| 38299 | Same-runtime CPU | 368.51 s | 587 | 8,768 | RM09 CPU-control raw `/usr/bin/time -v` |
| 38299 | RM09 static PL | 299.14 s | 10,526 | 242,024 | One run |
| 38299 | RM10 PL | 285.53 s | 7,144 | 142,136 | This run |
| 35419 | Same-runtime CPU | 822.35 s | 1,368 | 104,144 | RM09 CPU-control raw `/usr/bin/time -v` |
| 35419 | RM09 static PL | 652.32 s | 3,865 | 381,040 | One run |
| 35419 | RM10 PL | 619.70 s | 63 | 124,736 | This run |

Fault counts do not move consistently with wall across modes or requests; the repeated Q37804 RM10 runs are ordered and therefore show only warm-order association. `/usr/bin/time -v` “File system inputs” is a count, not bytes. Page-in bytes and continuous in-run CMA minima were not captured. These measurements support no stable causal attribution and no memory-management follow-up.

## CMA gate snapshots

| Point | CmaFree |
|---|---:|
| Before image load | 600,648 kB |
| After RM10 load | 580,292 kB |
| Before Q38299 | 557,168 kB |
| After Q38299 | 658,092 kB |
| Before Q35419 | 658,200 kB |
| After Q35419 | 645,428 kB |
| After restore | 651,908 kB |

These are boundary snapshots, not continuous minima. The XRT allocation gate passed for both requests; swap remained zero.

## Hash verification

`REMOTE_SHA256SUMS.txt` is the board-side SHA-256 listing produced for every copied raw file (relative path `./...`). All checks passed after copy. `raw/SHA256SUMS` is a local convenience manifest of the same raw payload; it intentionally does not hash itself. SHA-256 of `REMOTE_SHA256SUMS.txt`: `b580413b7e65cc4e4365d38448965648af0fac0867cd3705203cbf68c91ca2f7`.
