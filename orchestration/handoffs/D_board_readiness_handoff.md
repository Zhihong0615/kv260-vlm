# D01 board-readiness handoff

## Readiness

**BLOCKED — no first research-bitstream trial is recoverable from the available evidence.** The runbook is intentionally fail-closed. P3 remains `NO_GO_NOW`. No board connection, command, bitstream build/load, reboot, application/driver change, or other state change was performed for D01.

The nine source files named in the frozen brief were SHA-256 checked against `orchestration/source_snapshots/TASK_D01.sha256`; all entries returned `OK`. The worker checkout was verified at start as clean on `agent/D01-board-readiness`, HEAD `094edc130489dc59dd9333e4ae6b0aa4c8013149`.

## Findings

- **HISTORICAL:** The recorded 2026-09-23 post-reboot Wi-Fi SSH, starter-kit/XRT-ready state, and three CMA snapshots passed the fixed CPU-runner CMA floor. This does not establish current state, PL/DMA headroom, or recoverability.
- **UNKNOWN:** The current known-good boot image/slot and FPGA design ID; a research bitstream; a validated rollback/restore command; and a physical UART or other independent recovery route.
- **OWNER CONFIRMATION REQUIRED:** Named board owner, exclusive reservation and lock protocol, access/identity, exact image-specific action plan, and separate explicit approval for the first load. The prior approval covered one normal reboot only.
- The existence of boot `.bak` files and prior SSH reconnection are not treated as rollback or physical recovery evidence. No rollback commands are published.

## Deliverables

- [`docs/first_bitstream_runbook.md`](../../docs/first_bitstream_runbook.md) — readiness evidence, read-only preflight gates, explicit approval boundary, blocked stateful steps, failure handling, and exact remaining recovery evidence.
- `orchestration/handoffs/D_board_readiness_handoff.md` — this handoff.

## Commit and blockers

- Content commit SHA: `07eb1057b16a69a1fd076753d5d07a0bd202e219` (initial commit carrying both deliverables; this line is recorded in a metadata-only follow-up).
- Final task HEAD: **to be reported in the task completion message**.
- Exact missing evidence: (1) end-to-end verified physical UART/console or other independent recovery route and responsible recovery operator; (2) exact known-good boot image/slot and validated restore target/procedure; (3) fresh current FPGA Manager / application / slot state and interpreted expected values; (4) exact research design, bitstream hash, source/build/toolchain provenance, compatibility, and PL/DMA resource gate; (5) named board owner, exclusive reservation, lock acquire/release protocol, and access identity; (6) image-specific bounded load and rollback timeouts, success signals, failure responses, and recovery steps; and (7) separate explicit user approval naming the exact bitstream hash and operation.
- The runbook marks the load, rollback, and any future reboot as blocked; timeout/success/recovery fields remain explicitly `UNKNOWN` until the concrete image plan is reviewed.
- No board test was run because the frozen brief forbids board access and the recovery route cannot be verified from the recorded evidence.
