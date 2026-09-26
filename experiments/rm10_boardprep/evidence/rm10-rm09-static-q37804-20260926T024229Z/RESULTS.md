# RM10 paired RM09 static control

Run directory on `kria`: `/home/ubuntu/kv260-vlm-p2-cpu/runs/rm10-rm09-static-q37804-20260926T024229Z`.

## Static run result

The same RM09 CLI/library, model, mmproj, image, prompt, decode parameters, PL dispatch settings, and 100 MHz FCLK were used as in the RM10 candidate run. Static app `.bit.bin` SHA-256 was `819b088199ac4346c1eb9b7bb65ade42afe8f95eaeec02cca4bc6bdd2bb0d87b`; DTBO SHA-256 was `85fd0a2e2186886d8d52178c0934ba51585c37c28e5dd54a1c5536f2e506521e`.

The request returned `G`, exited 0, and passed the frozen trace checks: 145 total operations, 135 PL calls (35 at N=1120 and 100 at N=280), and 10 expected CPU fallbacks (five ViT merger, five MM down); all 27 numbered layers ran five times on PL. `/usr/bin/time -v` wall was **519.39 s** (`8:39.39`); model performance summary total time was 512.835 s. The corrected static-control runner SHA-256 was `cf79d13ad7f36178a21c494daf1c905922c3d9e0e0b22de694be071fea94f8fe` (commit `7a1d1a32148c00dfccff784c5542e0a3186b9c37`).

| Measure | RM10 candidate | RM09 static control | Candidate minus static |
|---|---:|---:|---:|
| Full request wall | 524.42 s | 519.39 s | +5.03 s (+0.968%) |
| Five image encoding intervals | 429.287 s | 445.026 s | −15.739 s |
| Five image decode intervals | 50.055 s | 49.480 s | +0.575 s |
| Model performance-summary total | 517.737 s | 512.835 s | +4.902 s |
| 135-call FFN-down family wall | 82.946846 s | 99.630538 s | −16.683692 s (−16.746%) |
| PL kernel time | 69.855115 s | 86.545451 s | −16.690336 s (−19.285%) |
| Host packing / output unpack | 11.629916 / 1.169185 s | 11.670977 / 1.166789 s | −0.041061 / +0.002396 s |
| XRT sync to + from / AXI submit | 0.174010 / 0.041247 s | 0.171320 / 0.040611 s | +0.002690 / +0.000636 s |
| Kernel / total-call throughput | 4.769752 / 4.016929 GMAC/s | 3.849903 / 3.344272 GMAC/s | +23.893% / +20.112% |
| PL calls / CPU fallbacks | 135 / 10 | 135 / 10 | same |
| Answer / restore | `G` / PASS | `G` / PASS | same |

Both traces cover 333.1915776 GMAC and report 22.2292992 GB input plus 0.3096576 GB output. The request-wall difference is smaller than the expected gain from the measured family-time reduction and is confounded by run order: the candidate ran first with 21,695 major page faults and 845,952 file-system inputs, while this static run followed with 4,068 major faults and 76,840 file-system inputs. The candidate therefore ran cold and the control ran with a substantially warmer cache. This single pair does not establish an end-to-end regression or speedup.

Using the paired static full-request wall and family time for the Amdahl estimate:

```text
519.39 s static request − 99.630538 s static family + 82.946846 s candidate family
= 502.706308 s predicted candidate wall
524.42 s measured candidate wall − 502.706308 s = +21.713692 s residual
```

The residual is not attributable to the FPGA architecture from this run because the two requests had markedly different page-fault and storage-read counts. Decision label for this paired end-to-end evidence: **`END_TO_END_INCONCLUSIVE`**.

## CMA, clock, and restore

The static runner used the same 1,671,168-byte bounded XRT pool. Its pre-load `CmaFree` was 494,916 KiB, and the loaded-app snapshot was 499,456 KiB. Read-only polling during the request sampled a low of 776 KiB; the buffer pool had already been allocated and no allocation failure appeared. Post-request and post-restore snapshots showed 604,736 and 615,660 KiB. FCLK0 remained 99,999,999 Hz and the FPGA manager was `operating`.

The 4,200-second rollback timer was active before app change. Explicit restoration at 02:51:10–02:51:11Z loaded `k26-starter-kits`; `starter_kit_restore=PASS`, `run_exit_status=0`.

Raw files were copied read-only from the board. `REMOTE_SHA256SUMS.txt` was generated on the board and verified against every copy; `SHA256SUMS` covers the local handoff. The candidate run and its same-runtime/cross-cache caveat are documented in the sibling [`RM10 candidate results`](../rm10-a-ra-q37804-20260926T022237Z/RESULTS.md).
