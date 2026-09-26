# RM10 warm QID37804 candidate

Board run directory: `/home/ubuntu/kv260-vlm-p2-cpu/runs/rm10-a-ra-q37804-20260926T083001Z` (started 2026-09-26 08:30:01 UTC). Captured driver, CLI output, PL trace, time-v, tensor checks, restore log, and pre-load clock diagnostics are retained beside this file.

## Request result

The request returned `G`; `/usr/bin/time -v` reports exit 0 and **517.10 s** wall time. The frozen trace expectation passed: 145 operations, 135 PL calls (35 at N=1120 and 100 at N=280), 10 expected CPU fallbacks (five ViT merger and five MM-down), and all 27 numbered layers on PL.

CLI-reported performance fields were load **510205.36 ms**, prompt eval **499632.62 ms**, eval **343.85 ms**, and total **510560.12 ms**. These counters overlap and do not sum to request wall. The five logged `mtmd batch encoding done` durations sum to **430.630 s** (static control: 445.026 s); five `image decoded` durations sum to **49.207 s** (static control: 49.480 s).

## Paired metrics

The comparison uses the RM09 static control at `../rm10-rm09-static-q37804-20260926T024229Z/` and the earlier cold RM10 run at `../rm10-a-ra-q37804-20260926T022237Z/`.

| Measure | RM09 static | Earlier RM10 | This RM10 | This RM10 minus static |
|---|---:|---:|---:|---:|
| Request wall | 519.39 s | 524.42 s | 517.10 s | −2.29 s (−0.441%) |
| Five multimodal batch encodings | 445.026 s | 429.287 s | 430.630 s | −14.396 s |
| Five image decodes | 49.480 s | 50.055 s | 49.207 s | −0.273 s |
| FFN-down family wall | 99.630538 s | 82.946846 s | 82.975032 s | −16.655506 s |
| PL kernel | 86.545451 s | 69.855115 s | 69.879160 s | −16.666291 s |
| Packing | 11.670977 s | 11.629916 s | 11.670128 s | −0.000849 s |
| Major page faults | 4,068 | 21,695 | 15,617 | +11,549 |
| Filesystem inputs | 76,840 | 845,952 | 563,712 | +486,872 |

Against the preregistered cutoffs, 517.10 s is below the 519.39 s control by 2.29 s, but above the 514.39 s practical-win cutoff by 2.71 s. It lies in the **514.39–519.39 s ambiguous interval**. The candidate's major faults remain 3.84× and filesystem inputs 7.34× the static run; versus the earlier cold candidate they fell by 6,078 faults and 282,240 input blocks. This run therefore does not isolate a cache-matched end-to-end difference.

Subtracting the trace family summary from each request wall gives 434.124968 s non-family time for this candidate and 419.759462 s for static, a +14.365506 s residual. This is an arithmetic decomposition, not an attribution to the FPGA or a specific host phase.

Candidate family medians per PL call were 1.374448 s wall / 1.161571 s kernel at N=1120 (35 calls), and 0.347966 s wall / 0.291952 s kernel at N=280 (100 calls). Static medians were 1.656022 / 1.439778 s and 0.417515 / 0.361505 s, respectively. The trace reports 11.670128 s packing, 0.092490 s sync-to, 0.079922 s sync-from, 0.040946 s submit, and 1.169978 s unpack; individual-line sum differs from summary by about 37 microseconds.

## Board recovery and resources

The driver recorded the bounded XRT pool as 1,671,168 bytes. A read-only monitor sampled minimum `CmaFree` at **5,376 kB** while VLM ran; no XRT/CMA allocation failure was reported. Driver snapshots were 520,280 kB before restore and 526,200 kB after restore. `restore.log` records `starter_kit_restore=PASS`, FCLK0 at 99,999,999 Hz, FPGA manager `operating`, and run exit status 0 at 08:38:49 UTC. An unprivileged post-run `xmutil listapps` query was denied by socket permissions, so active-slot verification is based on the guarded restore log rather than that query.

`REMOTE_SHA256SUMS.txt` records the board-side raw file hashes and was verified against the copied files. `SHA256SUMS` covers this local handoff directory.
