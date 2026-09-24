# KV260 first research-bitstream runbook

**Readiness: BLOCKED — the RM06 image exists, but no verified board load/run/rollback path exists.** This document records current evidence and the specific hardware recovery gap. It does not itself authorize a stateful board action. RM06 research authorization covers safe feasibility work; loading the concrete image still requires the verified recovery/load method and explicit artifact-specific approval. P3 method implementation remains **NO_GO_NOW**.

## Status labels

- **VERIFIED** — directly supported by the referenced records, within their stated scope.
- **HISTORICAL** — observed at the cited time; it must be checked again before any future trial.
- **OWNER CONFIRMATION REQUIRED** — a named owner or explicit authorization has not been recorded.
- **UNKNOWN** — available evidence does not establish the value or a safe procedure.

The original D01 evidence below was read from the coordinator source checkout after all nine SHA-256 entries in `orchestration/source_snapshots/TASK_D01.sha256` passed; it is historical as of 2026-09-23. A separate fresh read-only snapshot and new image evidence are recorded in the RM06 update below.

## RM06 update — 2026-09-24

- The K16 full-system bitstream was generated and its XSA validated. Bitstream SHA-256: `31ece1c9eee225931a860000b0a615778aa32085eeb69eb1976e0f083449abfc`; XSA SHA-256: `adcebed105372259967d1befab38ba4794d2dbbf1351728ba769d03c4ceb6e82`. Build record and routed timing/resource results are in [`RM06_RESULTS.md`](../experiments/rm06/RM06_RESULTS.md). The image is not loaded.
- Fresh board state at `2026-09-24T12:51:37Z`: `k26-starter-kits` / `XRT_FLAT` active at slot 0; FPGA Manager `operating`; XRT 2.13 Device Ready; four A53 cores; `MemAvailable=3,323,040 KiB`; idle `CmaFree=557,112 KiB`; no matching VLM/XRT/Vivado/apt process; apt and apt-upgrade inactive. Raw output: [`board_readonly_2026-09-24.txt`](../experiments/rm06/results/board_readonly_2026-09-24.txt).
- During the CPU-only VLM capture request, `CmaFree` fell to roughly 13 MiB. The full-tensor HLS API would require 32.77 MiB across three contiguous buffers and has no bounded-buffer implementation yet. This is an integration constraint, not a reason to defer a standalone test that can otherwise be run safely.
- Current known-good running image state is identified only as the starter-kit app in slot 0. The host has not verified that it is a usable rollback target. No load/unload command is authorized by the recorded sudoers entry (only `sudo -n xmutil listapps` works); no board-side RM06 app/driver path or recovery from an unbootable board is verified. SSH/XRT readiness does not provide that recovery path.
- Formal owner-window/reservation paperwork is not required for the user's authorized RM06 work. Stop only if a competing user/process is actually confirmed or if the board recovery/load risks above remain unresolved.

## Readiness facts and limits

| Status | Fact | What it does and does not establish |
|---|---|---|
| **HISTORICAL** | After the one user-approved normal reboot, Wi-Fi SSH returned under a new boot ID. The reboot marker was absent, APT services were inactive, PackageKit reported no active transactions, Jupyter was active, `k26-starter-kits` / `XRT_FLAT` was active in slot 0, and `xbutil examine` reported Device Ready. Three snapshots 30–34 seconds apart recorded `CmaFree=1,014,300 KiB`, `CmaTotal=1,024,000 KiB`, swap 0, and `MemAvailable` 3,342,276 / 3,352,188 / 3,337,564 KiB. | This is a post-reboot P0 and CPU-runner resource result at the recorded times. It is not a current-state assertion, PL/DMA capacity guarantee, recovery test, or permission for another board action. The prior low-CMA allocation owner remains unknown. |
| **HISTORICAL** | Board inventory records Ubuntu 22.04.4, AArch64, kernel `5.15.0-1027-xilinx-zynqmp`, KV260 revB, XRT 2.13, and the starter-kit application. | Re-read before a future trial; do not infer current image, active design, slot, clocks, temperature, or memory high-water mark from this snapshot. |
| **UNKNOWN** | A validated known-good firmware/image identifier and exact rollback target. The current read-only listing shows `k26-starter-kits` in slot 0; its compatibility as a recovery target has not been tested. | Slot 0 and a successful XRT check do not prove that the starter-kit image can restore the board after a failed RM06 load. |
| **PARTLY VERIFIED** | Current FPGA Manager state reads `operating`; `xmutil listapps` reports the starter-kit application in slot 0. | The read-only state is healthy but is not a bitstream identity or rollback validation. |
| **HISTORICAL** | The 2026-09-23 boot inspection found current and `.bak` FIT files and boot scripts. The FITs had the same kernel payload and first DTB hashes but different initramfs payloads; boot-script hashes differed. The backup was parseable but was explicitly not verified as a recovery route. | Do not select, copy, flash, or boot a `.bak` file as a rollback step. No boot/QSPI operation is authorized by this runbook. |
| **HISTORICAL** | No USB-UART device was connected to the recorded host inventory. Wi-Fi SSH did reconnect after the prior normal reboot. | SSH recovery after a successful Linux boot is not an independent path if the board fails to boot Linux. UART availability and a physical recovery method remain unverified. |
| **VERIFIED** | The recorded passwordless board command is `sudo -n /usr/bin/xmutil listapps` only. Application load/unload is not authorized by the recorded sudoers entry. | Read-only listing permission does not confer application-control permission. Do not infer that a load/unload command will work or is approved. |
| **VERIFIED** | RM06 K16 full-system bitstream and XSA now exist and passed Vivado route/bitgen/XSA validation. No RM06 image, adapter, DMA buffer runtime, or VLM inference has been loaded/run on the KV260. | The concrete image can be identified and reviewed; this does not verify the board load method, buffer driver, rollback, or inference result. |
| **OWNER CONFIRMATION REQUIRED** | Load approval for RM06 must name bitstream SHA-256 `31ece1c9eee225931a860000b0a615778aa32085eeb69eb1976e0f083449abfc` and the exact load action. | The broad research authorization does not by itself name a concrete image/action. Do not request this approval until a safe load and recovery plan can be stated. |

### Evidence index

- [`PROJECT_STATUS.md`](../status/PROJECT_STATUS.md) and [`go_no_go.md`](../status/go_no_go.md): P0/P3 decisions and historical stage status.
- [`board_reboot_cma_resolution_plan_20260923.md`](../handoff/board_reboot_cma_resolution_plan_20260923.md): reboot authorization boundary, post-reboot snapshots, and unresolved physical fallback.
- [`environment_evidence.yaml`](../handoff/environment_evidence.yaml): recorded board state, permissions, unknowns, and boot recovery status.
- [`board_update_cross_thread_report_20260923.md`](../handoff/board_update_cross_thread_report_20260923.md): earlier boot-file change history and limits of the relayed observations.
- [`board_cpu_baseline_feasibility_review.md`](../handoff/board_cpu_baseline_feasibility_review.md), [`board_cpu_cma_gate_review.md`](../handoff/board_cpu_cma_gate_review.md), and [`board_cpu_build_acceptance_review.md`](../reviews/board_cpu_build_acceptance_review.md): CPU-only limits. Their 700,000 KiB CMA floor is not a calibrated PL/DMA resource threshold.
- [`gaps.md`](../handoff/gaps.md): no connected USB-UART, no first-load approval in records, and remaining owner/recovery gaps.

## Gate A — read-only prerequisites for a future proposal

These checks are evidence collection only. This D01 task did not run them. A future operator must record timestamp, operator, board owner, source of each observation, and raw output. Read-only success does not authorize the stateful steps in Gate B.

| Status now | Read-only prerequisite | Required record and fail-closed condition |
|---|---|---|
| **HISTORICAL** | Reconfirm board identity, boot ID, running kernel, boot marker, current boot image/slot, active application/design, FPGA Manager read-only state, XRT readiness, systemd/package activity, Jupyter health, swap and memory/CMA snapshots. Capture exact outputs and timestamps from the existing read-only `xmutil listapps` and `xbutil examine` checks and the approved status sources. | Treat every 2026-09-23 value as stale. Stop the proposal if identity, boot image, slot, app/design, manager state, XRT, or service state is missing, inconsistent, uninterpretable, or cannot be read. Leave Jupyter and the starter-kit app untouched. |
| **HISTORICAL** | Reconfirm the current board SSH route using only the research owner's batch-mode path. | A successful connection proves only that this route is reachable now. Do not use the user-owned interactive SSH PTY, change networking, or count SSH as recovery from an unbootable state. |
| **VERIFIED for this snapshot** | A read-only process check found no matching VLM/XRT/Vivado/apt process; the user has authorized RM06 feasibility work. | Do not require a reservation string or lock file. Stop if another user or conflicting process is actually confirmed before the experiment. |
| **UNKNOWN** | Verify a recovery route independent of Linux/SSH, including physical UART/console or equivalent recovery media and an authorized person able to use it. | A prior SSH reconnect only proves reachability after Linux boots. Without an independent path, a failed first load may be unrecoverable; do not load. |
| **UNKNOWN** | Identify the current known-good image/slot and the exact rollback target. Inspect the relevant board/vendor recovery documentation and obtain the board owner's validation of the target's compatibility with this board and boot chain. | Backup-file presence or hash is not validation. Do not guess a boot file, slot, firmware ID, manager state, or recovery command. |
| **PARTLY VERIFIED** | Freeze the image and provenance: RM06 bitstream SHA-256, XSA SHA-256, Vivado 2024.2, KV260 target, routed timing/resources, and expected post-load checks. | Artifact and build evidence are frozen in `experiments/rm06/RM06_RESULTS.md`; board-side app/driver/load compatibility and bounded CMA buffer runtime remain unverified. |
| **HISTORICAL** | Recheck memory, CMA, swap, services, active jobs, and logs immediately before any proposed load. | The three post-reboot CMA snapshots were historical and the 700,000 KiB floor was drafted for CPU-only work; it is not a PL/DMA safety threshold. The future design's required headroom and stop criteria must be independently established. Never lower or repurpose the CPU threshold by inference. |
| **OWNER CONFIRMATION REQUIRED** | Prepare the concrete load/run action with exact image hash, preconditions, bounded timeout, success signal, post-load checks, and explicit artifact-specific approval. | Approval must name the exact image hash and action. Broad research authorization does not name a specific image. A formal owner-window file or lock string is not required; a verified recovery path is. |

### Gate A exit rule

Gate A passes only when all required fields above have fresh, reviewable evidence and the verified physical recovery path and exact known-good restore target are available. If any field remains **UNKNOWN** or **OWNER CONFIRMATION REQUIRED**, do not proceed to Gate B. Do not treat the historical starter-kit state as a current baseline.

## Gate B — stateful steps requiring separate explicit user approval

No stateful action below is authorized by this document. The D01 evidence does not establish a safe load, unload, reset, rollback, or boot command. **No executable rollback command is provided because none is verified in the records.**

| State-changing step | Current status and required controls |
|---|---|
| Load the first research bitstream / design | **BLOCKED — UNKNOWN.** Preconditions: exact artifact compatibility and board-side load/run procedure; verified known-good restore target and physical recovery route; current state/resource check; explicit user approval naming the exact hash/action. No formal reservation or lock artifact is required; stop only if a competing user/process is confirmed. Bounded timeout and success signal remain **UNKNOWN** until the deployment method is verified. Failure response: cease further board mutations; do not retry, reset, unload, reboot, or alter boot files. Recovery route is currently **UNKNOWN**, so the load may not start. |
| Roll back / unload / restore known-good image | **BLOCKED — UNKNOWN.** Named owner: **OWNER CONFIRMATION REQUIRED**. Preconditions, authorized identity, validated target, bounded timeout, completion signal, and verified physical fallback: **UNKNOWN**. Failure response: do not execute or improvise a rollback; stop further mutations and transfer to the named board owner. Recovery route: **UNKNOWN**. Do not derive a command from `.bak` files, `xmutil listapps`, or the fact that slot 0 previously showed starter-kits. The board owner must supply and validate the exact recovery procedure before the first-load proposal can be approved. |
| Reboot after a load or recovery attempt | **BLOCKED — UNKNOWN / OWNER CONFIRMATION REQUIRED.** Named owner: **OWNER CONFIRMATION REQUIRED**. Preconditions: separate approval for this exact reboot, current known-good boot identity, and verified independent recovery route. Bounded timeout: **UNKNOWN**. Success signal: **UNKNOWN** until the image-specific boot and service checks are frozen. Failure response: stop further boot/network actions and transfer to the owner. Recovery route: **UNKNOWN**. The single earlier reboot approval is spent and non-transferable. No future reboot is authorized here. |

## Failure handling and stop points

| Observation | Required response |
|---|---|
| Any Gate A identity, boot, slot, application, XRT, service, image hash, or resource check fails, is stale, times out, or is ambiguous; or another user/process is confirmed | Stop before any load. Preserve the read-only evidence and resolve the concrete safety/integration gap. No cleanup or “repair” action is implied. |
| SSH disconnects during a future approved stateful operation | Do not issue another load/unload/reset/reboot command and do not infer whether the remote operation completed. Stop the session. The pre-verified physical recovery owner must take control; because no such route is currently verified, this condition is a hard blocker today. |
| Active design/slot differs from the frozen expected state, XRT is not ready, or a service is unhealthy after an operation | Do not retry or switch designs. Preserve available outputs, stop further mutations, and transfer to the owner using the pre-approved recovery procedure. If that procedure is absent, keep state **UNKNOWN** and do not improvise. |
| Operation exceeds its approved timeout, gives no unambiguous success signal, or produces a partial/error result | Stop according to the image-specific approved action plan. Do not extend the timeout, repeat the command, or try an unverified rollback. The plan must already state the recovery route; otherwise the operation must not have started. |
| Linux/SSH does not return | Existing SSH is unavailable by definition; no USB-UART fallback was recorded as connected. Do not issue blind network, boot, or power actions. The named board owner must use the previously verified physical recovery path. Current evidence has no such path, so a first load is prohibited. |

Capture a unique trial ID, artifact-specific approval, exact image and build hashes, preflight outputs, command text and operator identity, start/stop timestamps, exit/timeout result, post-load read-only outputs, and any failure evidence. Keep credentials, network addresses, keys, serials, and user data out of shared runbook artifacts. Preserve failures as-is; do not overwrite evidence with a successful retry.

## Current decision

**Do not load the RM06 image yet.** The candidate exists and has validated route/XSA evidence, but the board-side load/run method, independent physical recovery route, and exact known-good rollback procedure are unverified; during a full CPU VLM request, observed free CMA was also below the current full-buffer API's contiguous input requirement. These are concrete hardware/integration risks. The board is currently reachable with XRT ready, but SSH is not recovery from a failed Linux boot. Formal reservation paperwork is not a blocker; a safe load and rollback method is. Once those details are verified, request artifact-specific approval naming the hash above and the precise action.
