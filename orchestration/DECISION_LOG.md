# Decision Log

## 2026-09-24 — Move to scheduled, branch-isolated P1/P2 work

- **Decision:** Scheduler role is Research Orchestrator / Scheduler / PI Agent. Prepare four bounded Builder tasks (A01/B01/C01/D01) and one queued independent Reviewer (R01); do not continue heavy literature, trace, architecture, RTL, or board work in the Scheduler window.
- **Evidence basis:** User-provided orchestration instructions; current `status/PROJECT_STATUS.md`, `status/go_no_go.md`, cited literature/derived evidence/spec/reviews/handoffs; current Git state.
- **Stage:** P1/P2 continue. P3 remains **NO_GO_NOW**. No global novelty conclusion changes.
- **Git finding at dispatch:** Local branch was `master` at `094edc130489dc59dd9333e4ae6b0aa4c8013149` with no remote configured. The primary checkout contains extensive uncommitted research work, including about 1.3 GB under `experiments/`. Do not rename the branch, commit the broad overlay, stage the full raw tree, create GitHub Issues, push, or publish.
- **Isolation decision:** Create a coordination worktree/branch containing only scheduler docs and frozen per-task input hashes. Create A/B/C/D worker worktrees from the clean project baseline SHA. Workers read the primary checkout through absolute, hash-checked paths and treat it as read-only; their output belongs in their own branch. This keeps their startup HEAD exact while avoiding raw-data copies.
- **Reviewer decision:** R01 stays queued until A/B/C deliver committed handoffs and Scheduler freezes an exact review target. The Reviewer is not a candidate-construction window.
- **Board safety:** D01 may document recorded facts only. No board command, SSH session, reboot, configuration change, VLM inference, bitstream build/load or stress run is authorized by this dispatch. The previous one-time reboot authorization is complete and does not extend to future actions.
- **Next decision:** After A/B/C commits and handoffs arrive, decide whether any candidate warrants independent review. Do not advance P3 based on a Worker statement or an unreviewed local note.

## 2026-09-24 — Configure the user-provided HTTPS remote

- **Action:** Set `origin` to `https://github.com/Zhihong0615/kv260-vlm.git` in the shared repository configuration after the user supplied that exact URL.
- **Verification:** `git remote -v` reports the same fetch and push URL. No credential is embedded in the URL. An unauthenticated fetch could not read a username, so repository reachability and account access remain unverified; no push, issue, PR, or publication was attempted.
- **Credential handling:** Do not collect or store the account password in chat or project files. If authentication is needed, use a local secure credential prompt/manager or a GitHub token entered through that secure mechanism.
- **Coordination:** Existing task briefs remain frozen. Workers must not push or create GitHub artifacts; the Scheduler controls any later remote operation.

## 2026-09-24 — Authenticate remote locally and integrate A/B/C/D handoffs

- **Authentication:** GitHub CLI device authorization completed for `Zhihong0615`; `gh auth status` reports the token in the system Keyring. A repository-local Git credential helper calls GitHub CLI; no account credential is stored in the remote URL or project files. `gh repo view` verifies `Zhihong0615/kv260-vlm` exists and is private. The repository has no default branch name, and `git ls-remote --heads origin` returned no refs, so the remote is currently empty. No push, issue, or PR was created.
- **Worker verification:** A01/B01/C01/D01 branches were clean at their final SHAs; their respective frozen source hash manifests passed. No primary-checkout artifacts were staged or modified by integration.
- **Integration:** Merged A01 at `ca2e2101027eb3596b6747c6a5e91bcc80df6f00` (`ac888a540a22be96bafe9976471dc6c41838d5ce`), B01 at `16bd6abf60a92bacca74d6f28124fb085b865153` (`e43406f62ff4fc9226b1bf5c07fea485b43842b7`), C01 at `d0c52e94830ca17b5629e2f1f703840ab84e09ac` (`12b32d191000bbf1acfd71cbe7ed4c7c292796dd`), and D01 at `ead34c7873dc0582e8ba4aa6c0b95b043edd7c91` (`e2c6d11b6e60739a3a804cd6643853e088dbde9c`).
- **Research decision:** A01 and C01 independently conclude that no current candidate survives as a method claim. B01 only prioritizes future workload measurements; D01 records that first-bitstream recovery remains blocked. Global status and P3 were not changed.
- **Freeze and activation:** Exact R01 target is `6dd1a83c4c771570b992a7ac83ec7de3d41ef60b`; it contains A/B/C handoffs, their frozen input manifests, a verified `TASK_R01.sha256`, and the byte-matched global `status/go_no_go.md`. R01 worktree `agent/R01-candidate-review` was created cleanly from that SHA. The activation record and current brief identify the target; R01 reviews only that immutable commit.
- **Next step:** Wait for R01's committed adversarial review. Keep all board state-changing work and first-bitstream load blocked.

## 2026-09-24 — Activate E01 current-SHA P2 gate review

- **Decision:** Independently review the current parser, runner, and preflight hashes because both existing static reviews bind older source versions and the dry-plan execution gate rejects them as stale.
- **Frozen source target:** `880096cc50f4d37692012136ef7d204856df40ca`, containing only the explicit E01 source snapshot and SHA-256 manifest copied byte-for-byte from the primary evidence checkout.
- **Scope:** Source-only static review of parser/runner/preflight, with focused-test coverage inspected as text. No tests, dry plans, syntax checks, SSH, board access, inference, source fixes, or GitHub actions.
- **Rationale and boundary:** This can close or strengthen a software evidence gate. It cannot satisfy synthetic ALPHA, a current live resource check, an owner window, physical recovery, or authorize board execution.
- **Next step:** Integrate E01's exact-SHA handoff only after verifying its clean worker branch and all frozen input hashes. Keep P2 board inference paused and P3 at `NO_GO_NOW`.

## 2026-09-24 — Integrate R01 adversarial candidate review

- **Decision:** Retain no architecture candidate and keep P3 at `NO_GO_NOW`.
- **Evidence:** R01 reviewed only frozen target `6dd1a83c4c771570b992a7ac83ec7de3d41ef60b`; its source manifests passed and worker commit `ea1bfff920c1dc6571c0258935ad6697ea6a2225` has that exact target as parent. Result: **FAIL**. H1–H3 lack a measured K26 failure interval and advantage over strongest static controls; H4/H5 are screened out. Proposed numerical thresholds also conflict across A01/C01 and are not preregistered.
- **Integration:** Added the exact-SHA review and compact handoff to the coordinator branch in merge `7657525a147ce08ac2a3ac6b75a919b4fa6ebb8a`. The frozen source `status/go_no_go.md` was not edited; the review is recorded here and in `SCHEDULER_STATE.md`.
- **Next step:** E01 is independently reviewing the current P2 parser/runner/preflight hashes. Continue the safe P1/P2 work; no RTL, research bitstream, or board inference follows from this review.

## 2026-09-24 — Activate B02 selected host workload audit

- **Decision:** Continue P2 by checking whether existing real VLM request logs support the proposed workload/selector questions before collecting new traces.
- **Frozen evidence:** `548d6229d9fbff67db5103933d9c837259d6b4f4` contains four selected development qids, their command/log/resource records, the hashed dev50 workload inventory, and prior shape/dispatch-time audits. All 20 source artifacts passed the frozen manifest check.
- **Scope:** Offline reconciliation only. B02 will not run inference or scripts, inspect answer labels, access the board, edit source evidence, or change status/novelty conclusions.
- **Rationale:** The audit can establish whether existing logs expose request identity, ordered visual groups and op-shape coverage, and where the evidence still stops. It cannot establish a K26 failure interval or PL benefit.
- **Next step:** Integrate its report only after exact-source and clean-branch validation. Continue to hold P3 at `NO_GO_NOW`.
