# RM10 final warm QID37804 candidate

Board run directory: `/home/ubuntu/kv260-vlm-p2-cpu/runs/rm10-a-ra-q37804-20260926T084944Z`, started 2026-09-26 08:49:44 UTC. Raw driver, CLI output, PL trace, time-v, tensor checks, restore log, and pre-load clock diagnostics are retained here.

## Request result and paired metrics

The request returned `G`; `/usr/bin/time -v` reports exit 0 and **504.24 s** wall. Frozen trace checks passed: 145 total operations, 135 PL calls (35 at N=1120, 100 at N=280), 10 expected CPU fallbacks (five ViT merger, five MM-down), all 27 numbered layers on PL.

| Measure | RM09 static | 08:30 RM10 | 08:49 RM10 | 08:49 minus static |
|---|---:|---:|---:|---:|
| Request wall | 519.39 s | 517.10 s | 504.24 s | −15.15 s (−2.92%) |
| Five multimodal batch encodings | 445.026 s | 430.630 s | 428.750 s | −16.276 s |
| Five image decodes | 49.480 s | 49.207 s | 49.290 s | −0.190 s |
| FFN-down family wall | 99.630538 s | 82.975032 s | 83.081739 s | −16.548799 s |
| PL kernel | 86.545451 s | 69.879160 s | 69.854995 s | −16.690456 s |
| Host packing | 11.670977 s | 11.670128 s | 11.807243 s | +0.136266 s |
| Major page faults | 4,068 | 15,617 | 5,838 | +1,770 |
| Filesystem inputs | 76,840 | 563,712 | 165,016 | +88,176 |

This run is 10.15 s below the preregistered 514.39 s practical-win cutoff. The request-wall Amdahl arithmetic is:

```text
519.39 s static request − 99.630538 s static family + 83.081739 s RM10 family
= 502.841201 s predicted
504.24 s measured − 502.841201 s = +1.398799 s residual
```

The residual is not a causal attribution. The page-fault and filesystem-input counts improved substantially from the 08:30 candidate but remain 1.44× and 2.15× static, respectively, so cache state is still not identical. The 08:49 run followed the 08:30 RM10 run on the same board and build; it should be interpreted with that order and the counters in view.

CLI performance fields: load **497312.80 ms**, prompt eval **489524.08 ms**, eval **293.32 ms**, total **497617.53 ms**. These counters overlap and are not additive. Logged `mtmd batch encoding done` durations sum to **428.750 s**; image decode durations sum to **49.290 s**.

The PL summary reports wall **83.081739 s**, kernel **69.854995 s**, pack **11.807243 s**, sync-to **0.093035 s**, sync-from **0.080645 s**, submit **0.040849 s**, unpack **1.168972 s**. Request wall less family wall is **421.158261 s**; the corresponding static residual is **419.759462 s**, a **+1.398799 s** arithmetic difference.

## CMA, clock, and restore

The bounded XRT pool was 1,671,168 bytes. A read-only monitor sample during the VLM request observed `CmaFree` as low as **532 kB** (with `MemAvailable` around 1.89 GB); no XRT or CMA allocation failure appeared in driver or CLI logs. Driver snapshots show `CmaFree` **594,184 kB** before restore and **600,648 kB** after restore. The restore log records `k26-starter-kits` loaded, `starter_kit_restore=PASS`, FCLK0 **99,999,999 Hz**, FPGA manager `operating`, and exit status 0 at 08:58:18 UTC. A post-restore read-only timer listing showed no RM10 rollback timer. An unprivileged `xmutil listapps` query was denied by socket permissions, so slot verification here relies on the guarded restore log.

`REMOTE_SHA256SUMS.txt` contains hashes generated on the board and verified against all 23 copied raw files. `SHA256SUMS` covers the local handoff directory.
