# Active Tasks

Updated: 2026-09-24  
Capacity: up to 4 Builders + 1 independent Reviewer. A01/B01/C01/D01 delivered on isolated worktrees and are integrated in the coordinator branch. R01 and E01 are active on separate frozen targets and review scopes.

| Task ID | Role | Problem | Dependencies | Expected deliverable | Priority | State | Branch / Worktree / Base |
|---|---|---|---|---|---|---|---|
| A01 | Prior-Art / Novelty Researcher | Identify constraint-specific failure regimes in closest papers and test whether any MiniCPM-V/KV260 hypothesis survives strong static controls. | Frozen source inputs; no other task required. | `orchestration/handoffs/A_novelty_handoff.md` plus targeted `literature/` changes. | P1 high | DELIVERED / INTEGRATED — final worker HEAD `ca2e2101027eb3596b6747c6a5e91bcc80df6f00`; coordinator merge `ac888a540a22be96bafe9976471dc6c41838d5ce` | `agent/A01-prior-art` / `/home/zhiro/research/kv260-vlm-workers/A01-prior-art` / `094edc130489dc59dd9333e4ae6b0aa4c8013149` |
| B01 | Profiling / Workload Researcher | Convert current host traces into a hardware-decision profile and rank the measurements still missing. | Frozen source inputs; no new board activity. | `orchestration/handoffs/B_workload_handoff.md` and a concise reproducible profile under `experiments/derived/`. | P2 high | DELIVERED / INTEGRATED — final worker HEAD `16bd6abf60a92bacca74d6f28124fb085b865153`; coordinator merge `e43406f62ff4fc9226b1bf5c07fea485b43842b7` | `agent/B01-workload-profile` / `/home/zhiro/research/kv260-vlm-workers/B01-workload-profile` / `094edc130489dc59dd9333e4ae6b0aa4c8013149` |
| C01 | Architecture Hypothesis Researcher | Screen no more than three mechanisms against current evidence, closest prior art and strongest static controls. | Start immediately from frozen inputs; later incorporate committed A01/B01 handoffs. | `orchestration/handoffs/C_architecture_candidates.md` and optional compact `spec/` matrix. | P1 highest | DELIVERED / INTEGRATED — final worker HEAD `d0c52e94830ca17b5629e2f1f703840ab84e09ac`; coordinator merge `12b32d191000bbf1acfd71cbe7ed4c7c292796dd` | `agent/C01-architecture-candidates` / `/home/zhiro/research/kv260-vlm-workers/C01-architecture-candidates` / `094edc130489dc59dd9333e4ae6b0aa4c8013149` |
| D01 | Board Readiness / Recovery Researcher | Convert recorded board evidence into a fail-closed, operator-usable first-bitstream runbook while marking unknown recovery paths. | Frozen board records; documentation only. | `orchestration/handoffs/D_board_readiness_handoff.md` and `docs/first_bitstream_runbook.md`. | P2 high | DELIVERED / INTEGRATED — final worker HEAD `ead34c7873dc0582e8ba4aa6c0b95b043edd7c91`; coordinator merge `e2c6d11b6e60739a3a804cd6643853e088dbde9c` | `agent/D01-board-readiness` / `/home/zhiro/research/kv260-vlm-workers/D01-board-readiness` / `094edc130489dc59dd9333e4ae6b0aa4c8013149` |
| R01 | Adversarial Research Reviewer | Attack novelty, evidence, workload support, strongest controls and falsification of A/B/C candidates. | A01/B01/C01 are integrated and hash-frozen; D01 is not a dependency. | `reviews/current_candidate_review.md` and compact exact-SHA handoff. | Gate-critical | ACTIVE — frozen review target `6dd1a83c4c771570b992a7ac83ec7de3d41ef60b`; isolated start state verified before dispatch. | `agent/R01-candidate-review` / `/home/zhiro/research/kv260-vlm-workers/R01-candidate-review` / `6dd1a83c4c771570b992a7ac83ec7de3d41ef60b` |
| E01 | Current P2 Gate Reviewer | Independently review current parser, runner, and preflight hashes; identify execution-gate defects without board access. | Frozen source snapshot commit `880096cc50f4d37692012136ef7d204856df40ca`. | `reviews/current_p2_gate_independent_review.md` and exact-SHA handoff. | Gate-critical | ACTIVE — all nine source hashes verified; worker start HEAD `d5ab097050a74bf0eeec35a6d3b635e238ea25e9` clean. | `agent/E01-p2-gate-review` / `/home/zhiro/research/kv260-vlm-workers/E01-p2-gate-review` / `d5ab097050a74bf0eeec35a6d3b635e238ea25e9` |

## Worker dispatch and task brief paths

A01/B01/C01/D01 are complete; their branches remain preserved as individual source-of-record outputs. Do not reopen them as writers. R01 is the sole active worker and reviews only the frozen target; its activation record is `orchestration/review_activations/R01.md`.

The frozen task brief paths are:

- A01: `/home/zhiro/research/kv260-vlm-orchestration/orchestration/task_briefs/TASK_A01.md`
- B01: `/home/zhiro/research/kv260-vlm-orchestration/orchestration/task_briefs/TASK_B01.md`
- C01: `/home/zhiro/research/kv260-vlm-orchestration/orchestration/task_briefs/TASK_C01.md`
- D01: `/home/zhiro/research/kv260-vlm-orchestration/orchestration/task_briefs/TASK_D01.md`

Each worker must verify the exact branch and clean base SHA in its brief. C01 starts without waiting for A01/B01 and may later make a follow-up commit that cites their handoff commits. Keep R01 closed until Scheduler activates it on a frozen input SHA.

The primary checkout `/home/zhiro/research/kv260-vlm` is an immutable evidence source for these tasks, not a work directory. Do not modify it from a Worker window. R01 is restricted to its frozen novelty target; E01 is restricted to its frozen P2 code snapshot.
