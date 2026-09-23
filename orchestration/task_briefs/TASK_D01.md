# Task ID

D01 — Board Readiness / Recovery Researcher

# Role

Builder for board-safety and recovery documentation only. Do not operate the board.

# Current project HEAD

Project baseline: `094edc130489dc59dd9333e4ae6b0aa4c8013149`  
Source evidence checkout: `/home/zhiro/research/kv260-vlm` (dirty overlay; read-only; verify `orchestration/source_snapshots/TASK_D01.sha256`).  
Task brief and hash manifest are frozen in `/home/zhiro/research/kv260-vlm-orchestration`.

# Branch / Worktree / Base commit

Branch: `agent/D01-board-readiness`  
Worktree: `/home/zhiro/research/kv260-vlm-workers/D01-board-readiness`  
Base commit and required initial HEAD: `094edc130489dc59dd9333e4ae6b0aa4c8013149`  
Required start state: clean worktree; verify `git status --short --branch`, `git branch --show-current`, and `git rev-parse HEAD`. Stop if any value differs.

# Stage

P0 recovery evidence is post-reboot pass for the recorded CPU-only CMA floor. Research-image load and P3 remain NO_GO_NOW.

# Question

What facts, owner controls, recovery route, and fail-closed steps must be verified before a future, explicitly approved first research-bitstream trial could be considered recoverable?

# Read first

Read these exact source-checkout files first; do not scan the full repository:

1. `/home/zhiro/research/kv260-vlm/status/PROJECT_STATUS.md`
2. `/home/zhiro/research/kv260-vlm/status/go_no_go.md`
3. `/home/zhiro/research/kv260-vlm/handoff/board_reboot_cma_resolution_plan_20260923.md`
4. `/home/zhiro/research/kv260-vlm/handoff/environment_evidence.yaml`
5. `/home/zhiro/research/kv260-vlm/handoff/board_cpu_baseline_feasibility_review.md`
6. `/home/zhiro/research/kv260-vlm/handoff/board_cpu_cma_gate_review.md`
7. `/home/zhiro/research/kv260-vlm/handoff/board_update_cross_thread_report_20260923.md`
8. `/home/zhiro/research/kv260-vlm/reviews/board_cpu_build_acceptance_review.md`
9. `/home/zhiro/research/kv260-vlm/handoff/gaps.md`

Verify their hashes using `orchestration/source_snapshots/TASK_D01.sha256` in the coordinator worktree. Use only recorded evidence; identify when a fact needs owner confirmation.

# Known facts

- The last approved reboot completed; Wi-Fi SSH returned under a new boot ID, the reboot marker is absent, the starter-kit app is active, XRT reports ready, and three recorded snapshots show CmaFree 1,014,300 KiB.
- Earlier low CMA's allocation owner remains unknown. The current CMA result is a point-in-time resource gate, not a permanent guarantee.
- The board has no verified USB-UART fallback in the recorded host inventory. Physical recovery if Linux/SSH fails is unknown.
- No custom research bitstream or VLM inference has been run.
- The reboot authorization was for one normal reboot only; it does not authorize new board activity.
- First research-bitstream loading requires separate explicit user approval and a verified recovery route.

# Important uncertainties

- Current starter-kit image/slot and known-good firmware identifiers beyond the recorded evidence.
- Whether FPGA manager / xmutil read-only state is still identical at a future trial.
- A verified rollback path and physical UART access.
- Future board owner, exclusive reservation window, lock acquisition/release, SSH identity/path, timeout and failure escalation.
- The future research image, source/build commit, bitstream hash, compatibility and expected resource gate.

# Forbidden assumptions

- A backup boot file or prior successful SSH reconnect is not proof of recoverability.
- Do not infer board state from stale records as current.
- Do not publish management IPs, network identifiers, credentials, SSH keys, board secrets or user data.
- No board commands, SSH, reboot, device-tree/driver changes, package actions, bitstream load, reset, or performance run.
- Do not lower the 700,000 KiB CMA gate or rewrite global go/no-go.

# Scope

- Draft a fail-closed first-bitstream runbook from existing evidence.
- Cover current/known-good image and slot identity, FPGA manager/xmutil state, research-image naming/hash/build provenance, owner and exclusive lock, preflight and timeout, first-load stop points, rollback/recovery commands only when verified, SSH and UART fallback, failure handling and evidence capture.
- Label every item VERIFIED, HISTORICAL, OWNER CONFIRMATION REQUIRED, or UNKNOWN.
- Make it usable by a second operator; never invent a rollback command or represent an unverified route as safe.
- Separate pre-load read-only prerequisites from actions that require explicit user approval.
- Record a concise hardware-gate readiness matrix and exact missing evidence.

# Out of scope

- No command on or connection to the board.
- No first-load, bitstream build, reboot, device-tree/driver/configuration change, inference, or stress test.
- No GitHub Issue, push, PR, remote setup, or publication.

# Deliverables

- `orchestration/handoffs/D_board_readiness_handoff.md`
- `docs/first_bitstream_runbook.md` on this branch.
- Do not edit global status or treat documentation completion as gate closure.

# Acceptance criteria

- Every stateful step has a named owner, precondition, bounded timeout, success signal, failure response and recovery route—or is explicitly blocked as UNKNOWN.
- The runbook states that first loading needs separate user approval and that the current prior reboot approval does not extend to it.
- No unverified command is presented as executable recovery procedure.
- Handoff includes readiness status, missing evidence, changed files, commit SHA and blockers.
- The runbook leaves P3 at NO_GO_NOW.

# Stop conditions

Stop and report if any safe rollback/recovery route cannot be verified from available records, if a step would require connecting to the board or privileged evidence, or if the runbook would have to guess image/slot/device state. Keep all source evidence read-only.
