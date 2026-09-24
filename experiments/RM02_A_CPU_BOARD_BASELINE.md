# RM02-A: KV260 CPU-only MiniCPM-V baseline

Date: 2026-09-24  
Status: **BLOCKED before inference; BOARD_MEASURED = no.**  
Scope: exact source/review gate check, local hash-preserving staging, one authorized synthetic-ALPHA runner attempt, and a frozen minimal TextVQA request set. No TextVQA request started; the ALPHA runner failed its fresh preflight before CLI launch.

## Latest board snapshot

Read-only snapshots collected by the coordinator over the existing SSH route (not measurements collected by this worker):

- `2026-09-24T05:07:32Z`: resource values in the table below.
- `2026-09-24T05:13:01Z`: `MemAvailable=3,307,868 KiB`, `CmaFree=1,009,680 KiB`, `load1=1.09`, `/home` free about 44.89 GB, swap 0, PackageKit `NO_ACTIVE_TRANSACTIONS`, apt services inactive, Jupyter active, AArch64/four CPUs, timeout executable SHA verified, CPU frequency 1,333,333 kHz. No thermal zones were readable (`thermal_c=UNKNOWN`). The pinned helper returned `PROCESS_STATE_UNKNOWN` because of transient PID identity/interval mismatches for short-lived kernel workers.

The later helper result is the operative preflight outcome: **do not start**. Repeat the fresh preflight immediately before any authorized run; do not change the runner based on one transient sample.

| Field | Value |
|---|---|
| Boot ID / kernel / architecture | `2a931c48-99ad-4a3f-b3e1-f42634597098`; `5.15.0-1027-xilinx-zynqmp`; `aarch64`, 4 CPUs |
| `MemAvailable` | 3,308,988 KiB |
| `CmaFree / CmaTotal` | 1,009,680 / 1,024,000 KiB |
| Swap / reboot marker | 0; absent |
| apt-daily / apt-daily-upgrade | inactive / inactive |
| PackageKit | service active; `GetTransactionList` returned `ao 0` |
| Load1 | 1.49 (runner limit is 1.5) |
| CPU frequency | 1,333,333 kHz reported |
| Jupyter / XRT app | Jupyter active; `k26-starter-kits`, `XRT_FLAT`, slot 0 |
| XRT readiness / `/home` free | Device Ready = Yes; about 43.8 GB free |
| Temperature | UNKNOWN |

The sampled memory, CMA, swap, reboot marker, apt, PackageKit transaction, home-space, XRT, and load values pass their CPU-runner thresholds. However, the pinned process-state helper returned `PROCESS_STATE_UNKNOWN` on the second snapshot, so the whole live preflight does not pass. Repeat it near a future authorized run. These point-in-time snapshots are not an inference reservation or proof that the board remains idle.

## Exact source and review gates

The coordinator source still matches the fixed readiness-map hashes:

| Subject | SHA-256 | Exact review |
|---|---|---|
| `scripts/run_board_cpu_p2_textvqa.py` | `418c72316a055d0260ba88ccf85e31dba98cc0e0256d499fefa96063aa82e694` | R19 PASS, P0=0/P1=0; fixed review SHA `6997035c279aed292e3ca6476d182072e1e078cc6d39a48fbb1e3b8050c2022c` |
| `scripts/parse_board_textvqa_pilot.py` | `48c834d6b803eb6a06f4be39f287913c461701ec606956c66493fe7f10d7e209` | R17 PASS_WITH_P2_FINDINGS, P0=0/P1=0; fixed review SHA `e9c1465941a0f4ec9ee489fd5a3d193a7bddb621dadb171bd392c56f05b89587` |
| `scripts/board_cpu_preflight_remote.py` | `16d5bf8a2158dd16f409fb6708fe60440cc95585e98f41044ce5732b192c9616` | runner-pinned source hash |

The residual review findings are P2 and are not the cause of this block. No source change is proposed in this checkpoint.

## Current run gate and first attempt

1. **Authorization:** the user replied **“完全授权”** to the coordinator's explicit owner-window question. The recorded scope is this bounded CPU-only baseline: synthetic ALPHA plus the selected TextVQA QIDs below, without bitstream load or reboot. This is explicit operation authorization; it is not a separate external board-wide reservation or evidence that other users are inactive.
2. **Runner safety inspection:** the coordinator checked the current single-runner SHA `1f055bedc1468af2309535cc6c1e4d88deec474c5afe82634b03b66dae36b4ed` and found no P0/P1 obstruction for one isolated `--device none -ngl 0` CPU request. The runner's fresh resource/process preflight still controls every start.
3. **Synthetic ALPHA attempt:** run ID `kv260_cpu_p2_alpha_20260924_rm02_01` ended `PRECHECK_FAILED` at `2026-09-24T05:32:18.110367Z`, exact failure `ValueError('CmaFree below fixed floor')`. The runner record says `board_inference_attempted=false`; the CLI never started. `preflight_before.json` records `CmaFree=471,804 KiB` / `CmaTotal=1,024,000 KiB` against the unchanged 700,000 KiB floor; `MemAvailable=3,304,380 KiB`, swap 0, load1 1.24, `/home` free 44,890,525,696 bytes, `NO_ACTIVE_TRANSACTIONS`, apt services inactive, Jupyter active, AArch64/4 CPUs and 1,333,333 kHz. No thermal zones were readable (`UNKNOWN`). The sampler also reported `PROCESS_STATE_UNKNOWN` from two short-lived PID identity changes; selected processes included `packagekitd`, the idle `unattended-upgr` shutdown waiter, and two `python3` processes (one was this preflight worker).
4. **Raw evidence:** local append-only directory `experiments/raw/kv260_cpu_p2_alpha_20260924_rm02_01/`; `run.json` SHA-256 `4e3e3cb700524432e4862996b010535a037d2b00b1f48a9ec799d508a3c86b8d`; `preflight_before.json` SHA-256 `2e9a0803dcf3368f7d9eaae08510da351e15b36a84f5f519ccf75f9cdfc3ab59`; `preflight_before.stdout` SHA-256 `147fce7cc76ab9106a40b856b2fafc8e3a56425ae00fd0996fd1652d64317dfa`; transport SHA-256 `4141c777569c180d26595ca932aa841770149436e85d33e610371a61fe760516`. The raw records remain untracked and local; no model output or answer text exists in this run.
5. **Next safe retry condition:** do not lower the CMA floor, kill unidentified processes, or alter services. Let board state settle naturally, then use the same frozen runner for a new preflight; retry ALPHA only when `CmaFree >= 700,000 KiB` and the full resource/process gate passes. If it passes, proceed to QID 38299.

The present hard stop is the measured CMA resource deficit. `PROCESS_STATE_UNKNOWN` is separately recorded but does not justify bypassing the independent CMA gate. No TextVQA request has started.

## Pinned inputs and proposed minimum coverage

Identity from the primary manifest (`SHA-256 7983dc4b63a6d0aba28ef85c87ce7a9c4ac76ebd1385e480699905b96d44a85c`): OpenBMB MiniCPM-V-4.6 and processor revision `36f34a661a4bd35d0dc2294cb044d2584646c7d3`; llama.cpp `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`; Q4_K_M `no-nextn` language GGUF `8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773`; F16 mmproj `ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293`. The host TextVQA development run manifest SHA is `d92fa666e25ad8fb2b9e06d03c806cda890319664bed4fc503f1837bcf066050`; the separate workload inventory SHA is `dc3b6da619d3947c0022ec1b8f9be5e5bb3e1d9f9204d460108f1017072a25be`.

The existing AArch64 CPU build attestation is at `experiments/raw/kv260_cpu_p2_baseline_round01/cpu_build_attestation_v1.json`, SHA `48cfe4fa9c5a4647ecb193ca91c6eaa07a539abd8addb2407ec14bf4d87755c2`. The pinned development manifest is at `datasets/textvqa_v0.5.1_dev_50_seed20260923/manifest.json`, SHA `62c32317029e40895ffd8e476e8a845416dac9d1d9490dfd6efb5f28a4374962`. Both are staged untracked with matching source/destination hashes; neither is committed, and no answer text was read or added to this report. GGUF, mmproj, processor config, runtime source archive, and JPEGs are staged likewise and listed in `experiments/staged/rm02_a/staged_inputs.sha256`.

**Current reviewed runner's minimum runnable set:** `(38299, 37804, 35419)`, three fresh processes with existing host references and 3/5/7 media groups. This covers a wide three-group input, an ordinary five-group input, and seven-group input whose internal group shapes change orientation. Qid 35419's source is 1024×819 landscape; it is not a true portrait original. The fixed three-QID pipeline therefore meets the small-run and group-behavior goals but leaves a **true portrait-original coverage limitation**. Do not alter runner/parser QID lists without an experiment-critical reason and exact-SHA review.

| QID | Original dimensions | Ordered media batches | Image SHA-256 |
|---:|---|---|---|
| 38299 | 1024×577 | `[66,64,64]` | `4365f84b5d2cbc5c740bafde088b1aeaf5c7b8326c8b9b5bfe2a529f9bc7a256` |
| 37804 | 1024×683 | `[70,70,70,70,70]` | `3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f` |
| 35419 | 1024×819 | `[63,63,63,63,63,63,63]` | `f703a5ce6bbf7c1aa1dd11fda26a7a30323913d404d771d51deba387c840c5f6` |

Proposed four fresh-process requests, all with existing host-run references and frozen source-image hashes:

| Coverage | QID | Original image / dimensions | Existing ordered media batches | Image SHA-256 |
|---|---:|---|---|---|
| Portrait, three-group | 38169 | `b1a23041365708ed`; 485×1024 | `[60,64,64]` | `2c3530ee99a012d397b54aa3884dd3197b07aae355b6bce526de3ab11fab75f5` |
| Ordinary landscape | 37804 | `58d543df7eab2bfc`; 1024×683 | `[70,70,70,70,70]` | `3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f` |
| Wide landscape | 35950 | `9d85d260f22be0c8`; 1024×633 | `[60,60,60,60,60]` | `225ff76c542d9f49474f60dfeb316e3ca31828b44b3ebaee52dcb3eeec984c30` |
| Mixed seven-group | 35005 | `97c8c2c2c6f572f1`; 1024×1024 | `[64,70,70,70,70,70,70]` | `2512aeae080117e96813702fc68733be80a4051fc1e871d926306c37a91abdb6` |

References: host dev50 `run.json` SHA above and `textvqa_dev50_visual_workload_inventory.json` SHA above. Image dimensions/batch patterns/hashes are metadata only; this record contains no prompt, label, prediction, or answer. A host phase timeline exists for qid 37804; qid 38169 has host graph/allocator traces but no phase timeline. Qids 35950 and 35005 have original host development-run references, not isolated target-stage timing.

**Coverage limitation:** the current reviewed runner and parser freeze only QIDs `(38299, 37804, 35419)`. The four-case extension above adds a true portrait and a mixed seven-group request, but requires a source change and current-hash review. Per RM02 scope, keep the runner/parser unchanged unless this coverage gap blocks the predeclared experiment; the three-QID run remains the minimum executable set and its portrait-original omission must be reported.

The existing draft's diagnostic CPU settings are `-t 2 -tb 2`, `-c 4096`, `-n 48`, seed 42, temperature 0, `--device none`, `-ngl 0`; its fresh-process wrapper wall time is the mandatory endpoint. TTFT and disjoint stage timing, temperature, and peak RSS are UNKNOWN unless the pinned runtime can report them reliably. Any field not reliable must remain UNKNOWN. Results must be appended outside this planning checkpoint, with request IDs/image hashes and current system metrics, and host scorer comparison must remain a development-set diagnostic.

## RM02-A outcome

- Real CPU-only KV260 VLM requests: **0 attempted**. One synthetic-ALPHA runner attempt was made; its CLI did not start.
- Board requests meeting the user's coverage requirement: **none**.
- Inference failures: **none; the synthetic ALPHA process did not start**. One fresh preflight failed before inference because `CmaFree` was below the fixed floor.
- Current state: **BLOCKED** by the real `CmaFree=471,804 KiB` deficit against the fixed 700,000 KiB floor. User explicitly authorized the bounded operation; no external reservation is claimed. Model/input assets are staged locally with verified hashes; no target transfer occurred.
- No board files, applications, services, images, or model files were changed. No TextVQA request or dry plan was run.
