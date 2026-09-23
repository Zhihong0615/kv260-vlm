# KV260 first research-bitstream runbook

**Readiness: BLOCKED — no first-load attempt is recoverable on the available evidence.** This document is a fail-closed checklist for a future, separately approved trial. It does not authorize a board connection, load, reboot, application change, or recovery action. P3 remains **NO_GO_NOW**; no custom research bitstream exists.

## Status labels

- **VERIFIED** — directly supported by the referenced records, within their stated scope.
- **HISTORICAL** — observed at the cited time; it must be checked again before any future trial.
- **OWNER CONFIRMATION REQUIRED** — a named owner or explicit authorization has not been recorded.
- **UNKNOWN** — available evidence does not establish the value or a safe procedure.

The evidence below was read from the coordinator source checkout after all nine SHA-256 entries in `orchestration/source_snapshots/TASK_D01.sha256` passed. It is read-only historical evidence dated 2026-09-23; none of it is a live board check on the date this runbook is used.

## Readiness facts and limits

| Status | Fact | What it does and does not establish |
|---|---|---|
| **HISTORICAL** | After the one user-approved normal reboot, Wi-Fi SSH returned under a new boot ID. The reboot marker was absent, APT services were inactive, PackageKit reported no active transactions, Jupyter was active, `k26-starter-kits` / `XRT_FLAT` was active in slot 0, and `xbutil examine` reported Device Ready. Three snapshots 30–34 seconds apart recorded `CmaFree=1,014,300 KiB`, `CmaTotal=1,024,000 KiB`, swap 0, and `MemAvailable` 3,342,276 / 3,352,188 / 3,337,564 KiB. | This is a post-reboot P0 and CPU-runner resource result at the recorded times. It is not a current-state assertion, PL/DMA capacity guarantee, recovery test, or permission for another board action. The prior low-CMA allocation owner remains unknown. |
| **HISTORICAL** | Board inventory records Ubuntu 22.04.4, AArch64, kernel `5.15.0-1027-xilinx-zynqmp`, KV260 revB, XRT 2.13, and the starter-kit application. | Re-read before a future trial; do not infer current image, active design, slot, clocks, temperature, or memory high-water mark from this snapshot. |
| **UNKNOWN** | The current active research design ID and a known-good firmware / image identifier suitable for recovery. `xmutil listapps` showing the starter-kit base did not establish a research design ID. | Slot 0 and a successful XRT check are not proof that a prior or backup image can restore the board. |
| **UNKNOWN** | FPGA Manager state beyond the historical `xmutil listapps` application listing. No recorded manager-state value was compared against a known-good research design. | A future proposal must define the exact read-only manager/application fields and their expected values for its frozen image; an uninterpreted or unavailable field blocks the proposal. |
| **HISTORICAL** | The 2026-09-23 boot inspection found current and `.bak` FIT files and boot scripts. The FITs had the same kernel payload and first DTB hashes but different initramfs payloads; boot-script hashes differed. The backup was parseable but was explicitly not verified as a recovery route. | Do not select, copy, flash, or boot a `.bak` file as a rollback step. No boot/QSPI operation is authorized by this runbook. |
| **HISTORICAL** | No USB-UART device was connected to the recorded host inventory. Wi-Fi SSH did reconnect after the prior normal reboot. | SSH recovery after a successful Linux boot is not an independent path if the board fails to boot Linux. UART availability and a physical recovery method remain unverified. |
| **VERIFIED** | The recorded passwordless board command is `sudo -n /usr/bin/xmutil listapps` only. Application load/unload is not authorized by the recorded sudoers entry. | Read-only listing permission does not confer application-control permission. Do not infer that a load/unload command will work or is approved. |
| **VERIFIED** | No custom research image, PS–PL adapter, DMA driver, or VLM inference on the KV260 is recorded. Existing HLS/Vivado smoke artifacts are vector-add and GPIO setup checks. | There is no research artifact to identify, validate, time, load, or roll back. Build/help success for the CPU CLI is not bitstream evidence. |
| **OWNER CONFIRMATION REQUIRED** | First research-bitstream loading requires separate explicit user approval and a verified recovery route. The prior approval was for one normal OS reboot only. | Reboot approval does not extend to first load, unload, reset, device-tree / driver change, or another reboot. P3 is still **NO_GO_NOW**. |

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
| **UNKNOWN** | Establish board ownership, a single-operator reservation window, other users' activity, and the exact coordination/lock protocol, including who acquires and releases it. | The named board owner, operator, reservation times, lock mechanism, and release authority must be recorded before considering any stateful action. Do not invent a lock file, lock command, or owner identity. |
| **UNKNOWN** | Verify an independent physical recovery route end to end, including actual UART/console hardware, the authorized person who can use it, required access, and recovery media/procedure. | A host device listing or prior SSH reconnect alone is insufficient. The board owner must attest to a tested route that remains available during the reservation. If this cannot be demonstrated, stop; the trial is not recoverable. |
| **UNKNOWN** | Identify the current known-good image/slot and the exact rollback target. Inspect the relevant board/vendor recovery documentation and obtain the board owner's validation of the target's compatibility with this board and boot chain. | Backup-file presence or hash is not validation. Do not guess a boot file, slot, firmware ID, manager state, or recovery command. |
| **UNKNOWN** | Freeze the research artifact and its provenance: image/design name, bitstream SHA-256, source commit, tool/version and build record, target board/revision, expected slot/design ID, interface/driver/DT compatibility, resource requirements, and expected post-load checks. | There is no research image in the current record. A future proposal is incomplete until a reviewer can verify the exact binary and compatibility evidence. No build or transfer is part of D01. |
| **HISTORICAL** | Recheck memory, CMA, swap, services, active jobs, and logs immediately before any proposed load. | The three post-reboot CMA snapshots were historical and the 700,000 KiB floor was drafted for CPU-only work; it is not a PL/DMA safety threshold. The future design's required headroom and stop criteria must be independently established. Never lower or repurpose the CPU threshold by inference. |
| **OWNER CONFIRMATION REQUIRED** | Prepare an image-specific action plan with explicit user approval, owner, preconditions, one bounded operation timeout, expected completion signal, post-load checks, and stop conditions. | Approval must name the exact image hash and action. Approval for reboot, CPU build, or inference does not cover a bitstream load. If the timeout, success signal, or owner cannot be stated, the step remains blocked. |

### Gate A exit rule

Gate A passes only when all required fields above have fresh, reviewable evidence and the verified physical recovery path and exact known-good restore target are available. If any field remains **UNKNOWN** or **OWNER CONFIRMATION REQUIRED**, do not proceed to Gate B. Do not treat the historical starter-kit state as a current baseline.

## Gate B — stateful steps requiring separate explicit user approval

No stateful action below is authorized by this document. The D01 evidence does not establish a safe load, unload, reset, rollback, or boot command. **No executable rollback command is provided because none is verified in the records.**

| State-changing step | Current status and required controls |
|---|---|
| Load the first research bitstream / design | **BLOCKED — UNKNOWN.** Named board owner: **OWNER CONFIRMATION REQUIRED**. Preconditions: Gate A complete; exact artifact hash/provenance/compatibility reviewed; exclusive reservation and lock held; known-good slot/image and physical recovery route verified; current board state and resource gate pass; separate user approval names the exact hash and action. Bounded timeout: **UNKNOWN until a design-specific procedure is reviewed and approved**. Success signal: **UNKNOWN until the design-specific expected active design/slot, XRT, service, and application checks are frozen**. Failure response: cease all further board mutations, retain available host-side timestamps/output, and hand control to the named board owner; do not retry, reset, unload, reboot, or alter boot files. Recovery route: **UNKNOWN** in current evidence, so the load may not start. |
| Roll back / unload / restore known-good image | **BLOCKED — UNKNOWN.** Named owner: **OWNER CONFIRMATION REQUIRED**. Preconditions, authorized identity, validated target, bounded timeout, completion signal, and verified physical fallback: **UNKNOWN**. Failure response: do not execute or improvise a rollback; stop further mutations and transfer to the named board owner. Recovery route: **UNKNOWN**. Do not derive a command from `.bak` files, `xmutil listapps`, or the fact that slot 0 previously showed starter-kits. The board owner must supply and validate the exact recovery procedure before the first-load proposal can be approved. |
| Reboot after a load or recovery attempt | **BLOCKED — UNKNOWN / OWNER CONFIRMATION REQUIRED.** Named owner: **OWNER CONFIRMATION REQUIRED**. Preconditions: separate approval for this exact reboot, current known-good boot identity, and verified independent recovery route. Bounded timeout: **UNKNOWN**. Success signal: **UNKNOWN** until the image-specific boot and service checks are frozen. Failure response: stop further boot/network actions and transfer to the owner. Recovery route: **UNKNOWN**. The single earlier reboot approval is spent and non-transferable. No future reboot is authorized here. |

## Failure handling and stop points

| Observation | Required response |
|---|---|
| Any Gate A identity, boot, slot, application, XRT, service, owner, lock, image hash, or resource check fails, is stale, times out, or is ambiguous | Stop before any load. Preserve the read-only evidence and ask the board owner to resolve the exact gap. No cleanup or “repair” action is implied. |
| SSH disconnects during a future approved stateful operation | Do not issue another load/unload/reset/reboot command and do not infer whether the remote operation completed. Stop the session. The pre-verified physical recovery owner must take control; because no such route is currently verified, this condition is a hard blocker today. |
| Active design/slot differs from the frozen expected state, XRT is not ready, or a service is unhealthy after an operation | Do not retry or switch designs. Preserve available outputs, stop further mutations, and transfer to the owner using the pre-approved recovery procedure. If that procedure is absent, keep state **UNKNOWN** and do not improvise. |
| Operation exceeds its approved timeout, gives no unambiguous success signal, or produces a partial/error result | Stop according to the image-specific approved action plan. Do not extend the timeout, repeat the command, or try an unverified rollback. The plan must already state the recovery route; otherwise the operation must not have started. |
| Linux/SSH does not return | Existing SSH is unavailable by definition; no USB-UART fallback was recorded as connected. Do not issue blind network, boot, or power actions. The named board owner must use the previously verified physical recovery path. Current evidence has no such path, so a first load is prohibited. |

Capture a unique trial ID, approval text, owner/reservation/lock records, exact image and build hashes, preflight outputs, command text and operator identity, start/stop timestamps, exit/timeout result, post-load read-only outputs, and any failure evidence. Keep credentials, network addresses, keys, serials, and user data out of shared runbook artifacts. Preserve failures as-is; do not overwrite evidence with a successful retry.

## Current decision

**Do not load a research bitstream.** The board's 2026-09-23 post-reboot CPU-only checks passed, but the research design does not exist, the current known-good image/slot and FPGA design identity are not established, the board owner and exclusive lock are unconfirmed, no physical UART/fallback route is verified, and no bitstream rollback procedure is known. P3 remains **NO_GO_NOW**. Revisit only after Gate A is complete and a concrete artifact-specific plan is reviewed and separately approved.
