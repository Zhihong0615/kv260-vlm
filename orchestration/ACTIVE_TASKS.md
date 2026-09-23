# Active Tasks

Updated: 2026-09-24  
Capacity: up to 4 Builders + 1 independent Reviewer. A01/B01/C01 are delegated and running in isolated worktrees. D01 waits for a worker slot. R01 remains queued.

| Task ID | Role | Problem | Dependencies | Expected deliverable | Priority | State | Branch / Worktree / Base |
|---|---|---|---|---|---|---|---|
| A01 | Prior-Art / Novelty Researcher | Identify constraint-specific failure regimes in closest papers and test whether any MiniCPM-V/KV260 hypothesis survives strong static controls. | Frozen source inputs; no other task required. | `orchestration/handoffs/A_novelty_handoff.md` plus targeted `literature/` changes. | P1 high | RUNNING — branch/HEAD/hash preflight passed | `agent/A01-prior-art` / `/home/zhiro/research/kv260-vlm-workers/A01-prior-art` / `094edc130489dc59dd9333e4ae6b0aa4c8013149` |
| B01 | Profiling / Workload Researcher | Convert current host traces into a hardware-decision profile and rank the measurements still missing. | Frozen source inputs; no new board activity. | `orchestration/handoffs/B_workload_handoff.md` and a concise reproducible profile under `experiments/derived/`. | P2 high | RUNNING — preflight report pending | `agent/B01-workload-profile` / `/home/zhiro/research/kv260-vlm-workers/B01-workload-profile` / `094edc130489dc59dd9333e4ae6b0aa4c8013149` |
| C01 | Architecture Hypothesis Researcher | Screen no more than three mechanisms against current evidence, closest prior art and strongest static controls. | Start immediately from frozen inputs; later incorporate committed A01/B01 handoffs. | `orchestration/handoffs/C_architecture_candidates.md` and optional compact `spec/` matrix. | P1 highest | RUNNING — preflight report pending | `agent/C01-architecture-candidates` / `/home/zhiro/research/kv260-vlm-workers/C01-architecture-candidates` / `094edc130489dc59dd9333e4ae6b0aa4c8013149` |
| D01 | Board Readiness / Recovery Researcher | Convert recorded board evidence into a fail-closed, operator-usable first-bitstream runbook while marking unknown recovery paths. | Frozen board records; documentation only. | `orchestration/handoffs/D_board_readiness_handoff.md` and `docs/first_bitstream_runbook.md`. | P2 high | QUEUED — wait for worker slot | `agent/D01-board-readiness` / `/home/zhiro/research/kv260-vlm-workers/D01-board-readiness` / `094edc130489dc59dd9333e4ae6b0aa4c8013149` |
| R01 | Adversarial Research Reviewer | Attack novelty, evidence, workload support, strongest controls and falsification of A/B/C candidates. | A01, B01 and C01 handoffs must be committed and frozen; Scheduler must publish activation SHA. | `reviews/current_candidate_review.md` and compact exact-SHA handoff. | Gate-critical; queued | QUEUED — DO NOT OPEN | Branch planned: `agent/R01-candidate-review`; worktree and exact base assigned at activation. |

## Worker dispatch and task brief paths

A01/B01/C01 are already active as delegated workers in the listed worktrees. Do not open duplicate writers on those branches. Once a slot opens, the Scheduler will dispatch D01 from its task brief. If using user-visible Codex task windows instead, first coordinate branch/worktree ownership; never run a second writer on an active branch.

The frozen task brief paths are:

- A01: `/home/zhiro/research/kv260-vlm-orchestration/orchestration/task_briefs/TASK_A01.md`
- B01: `/home/zhiro/research/kv260-vlm-orchestration/orchestration/task_briefs/TASK_B01.md`
- C01: `/home/zhiro/research/kv260-vlm-orchestration/orchestration/task_briefs/TASK_C01.md`
- D01: `/home/zhiro/research/kv260-vlm-orchestration/orchestration/task_briefs/TASK_D01.md`

Each worker must verify the exact branch and clean base SHA in its brief. C01 starts without waiting for A01/B01 and may later make a follow-up commit that cites their handoff commits. Keep R01 closed until Scheduler activates it on a frozen input SHA.

The primary checkout `/home/zhiro/research/kv260-vlm` is an immutable evidence source for these tasks, not a work directory. Do not modify it from a Worker window.
