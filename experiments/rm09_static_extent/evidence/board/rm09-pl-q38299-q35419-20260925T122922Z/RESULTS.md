# RM09 static extent board run

Run directory on the board: `/home/ubuntu/kv260-vlm-p2-cpu/runs/rm09-pl-q38299-q35419-20260925T122922Z`.
Loaded app: `kv260-rm09-static-extent` from route commit `2522fc2`; runtime
base commit `7c9c15992ff6df6d6fa10636b430e170a3dd2934`, patch SHA-256
`22d96ed06be3b8d6c2dd8f841785fdd90981932fe0c3754189dfe710493dc32d`.
Bitstream SHA-256 is
`819b088199ac4346c1eb9b7bb65ade42afe8f95eaeec02cca4bc6bdd2bb0d87b`, DTBO
SHA-256 is `85fd0a2e2186886d8d52178c0934ba51585c37c28e5dd54a1c5536f2e506521e`.
The runner completed both requests and restored the starter-kit image. The raw
logs listed in [SHA256SUMS](SHA256SUMS) were copied from the board. The captured
board-side digest output is [BOARD_SHA256SUMS](BOARD_SHA256SUMS); it matches the
local file hashes, and `sha256sum -c SHA256SUMS` passes.
The checksum manifest SHA-256 is
`c5db014d5a64477cc8036b37b6f6caabd438946e1cfc35f474a1b9a572b10edf`.

## Requests and process measurements

Process wall and peak RSS come from `/usr/bin/time -v`; both CLI exit statuses
were zero. CPU baseline walls are the frozen CPU-only request results supplied
for this comparison.

| QID | PL process wall | CPU baseline wall | Wall reduction | Peak RSS | Output |
|---:|---:|---:|---:|---:|---|
| 38299 | 299.14 s | 368.19 s | 18.8% | 1,856,120 KiB | `3` |
| 35419 | 652.32 s | 850.48 s | 23.3% | 1,862,368 KiB | `SHERIFF'S` |

The outputs matched the expected answers. Process wall is end-to-end CLI time.
`Dispatch wall sum` is accumulated `wall_ms` over FFN-down calls, including the
short merger fallback calls. Packing, sync, submit, kernel, and unpack columns
are the runtime's PL accounting. These component totals exclude model loading
and unrelated graph work.

## PL dispatch accounting

| QID | Calls | PL extent calls | CPU fallbacks | Dispatch wall sum | Pack | Sync to/from | Submit | Kernel | Input/output bytes |
|---:|---:|---|---|---:|---:|---:|---:|---:|---:|
| 38299 | 87 total; 81 PL | N1024=14, N1056=7, N256=40, N264=20 | 6 unmatched merger | 55.250 s | 6.451 s | 0.051 / 0.045 s | 0.023 s | 47.980 s | 12,332,716,032 / 171,638,784 |
| 35419 | 203 total; 189 PL | N1008=49, N252=140 | 14 unmatched merger | 125.625 s | 14.718 s | 0.119 / 0.109 s | 0.051 s | 109.115 s | 28,113,039,360 / 390,168,576 |

All 27 layers had the expected PL call count and zero layer CPU fallbacks. The
QID38299 merger fallbacks were ViT N256 twice and N264 once, plus MM-down N64
twice and N66 once. QID35419 had seven ViT N252 and seven MM-down N63
fallbacks. All fallbacks were `reason=unmatched_merger`; dtype was
F16/F32/F32. Other fallback reason counters were zero. Both summaries reported
`matches_expected=1` and the full extent histograms matched.

### Derived arithmetic throughput

For each PL extent call, MACs are computed as `K*M*N`, with fixed
`K*M=4304*1152=4,958,208`; the N call histogram supplies the total N. Kernel
rate is total GMAC divided by accumulated `kernel_ms`, and call rate uses the
accumulated dispatch `wall_ms`:

| QID | Derived total | Kernel rate | Dispatch call rate |
|---:|---:|---:|---:|
| 38299 | 184.683331584 GMAC | 3.849 GMAC/s | 3.343 GMAC/s |
| 35419 | 419.821387776 GMAC | 3.848 GMAC/s | 3.342 GMAC/s |

The near-constant aggregate rates show no evident throughput collapse across
these measured extents. These values are calculated from trace shape counts and
runtime timings; they are not standalone hardware performance-counter results.

The existing real-tensor helper passed its frozen layer0/N1120,
layer13/N280, and layer26/N280 checks for each request. There are no captured
real tensors for the new extents, so this run provides full VLM output
comparisons only; it does not establish elementwise correctness at N1008,
N1024, N1056, N252, N256, or N264.

## Board state and restoration

The HLS UIO, compatible string, AXI-Lite address, and APM identity checks
passed. The invalid-task probe returned `-4` with `dma_pointer_used=0`. FCLK0
read back `99,999,999 Hz` at every logged snapshot, within the routed
100 MHz ceiling.

`CmaFree` was sampled at run boundaries and DMA gates, not continuously:

| Checkpoint | CmaFree |
|---|---:|
| Before RM09 load | 492,512 kB |
| RM09 loaded | 481,480 kB |
| QID38299 before request/VLM DMA | 473,036 kB |
| After QID38299 | 582,484 kB |
| QID35419 before request/VLM DMA | 586,172 kB |
| After QID35419 | 541,120 kB |
| After starter restoration | 555,068 kB |

The minimum observed checkpoint was 473,036 kB. The true in-run `CmaFree`
minimum is unknown because it was not sampled continuously. Swap remained
zero at the request snapshots.

The 4,200-second rollback timer was verified active before app unload. Explicit
restore completed at 12:45:27 UTC with `starter_kit_restore=PASS`, FCLK0
`99,999,999 Hz`, and FPGA manager `operating`. Package cleanup passed; final
driver status was `run_exit_status=0 starter_kit_restore=PASS`.

## Pinned images

- RM09 bitstream SHA-256: `819b088199ac4346c1eb9b7bb65ade42afe8f95eaeec02cca4bc6bdd2bb0d87b`.
- RM09 DTBO SHA-256: `85fd0a2e2186886d8d52178c0934ba51585c37c28e5dd54a1c5536f2e506521e`.
- Runtime artifact manifest SHA-256: `e35e0b1ff5ae5c3630af49c20f5494dd5ce82753f33374b216c36ac1b1cb95a9`.
