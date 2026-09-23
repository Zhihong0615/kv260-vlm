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

## 2026-09-24 — Integrate E01 current-SHA P2 review

- **Decision:** Record the current parser/runner/preflight source review as complete with P0=0, P1=0, P2=7; retain all seven P2 findings and keep the actual configured runner gate closed.
- **Evidence:** Frozen input snapshot `880096cc50f4d37692012136ef7d204856df40ca`; all nine manifest entries passed. Worker report commit `9830c219f4f0a8f4c6361f57a668e210e0625ef7` is based on the exact isolated start `d5ab097050a74bf0eeec35a6d3b635e238ea25e9`. Coordinator merge `772fa8ad9985ee4c932226f7b9d12d2d5e70318d` contains the exact-hash report and handoff.
- **Gate interpretation:** The report meets the source-level review predicate for both current parser and runner hashes, but the runner reads fixed paths in the primary checkout. The report was not copied to those paths because the primary checkout is the immutable evidence source. ALPHA proof, live resources, owner window, dynamic tests, and any execution authorization remain absent/unverified.
- **Next step:** B02 is auditing existing host visual-pattern records offline. Keep board inference paused until all taskbook gates and a separately authorized owner window are met; retain P3 `NO_GO_NOW`.

## 2026-09-24 — Integrate B02 selected workload-pattern audit

- **Decision:** Mark B02 complete and continue P2 with a narrowly scoped host metadata trace for the four selected request patterns, if the existing capture point and isolated output path are suitable. Do not promote any method claim.
- **Evidence:** Frozen snapshot `548d6229d9fbff67db5103933d9c837259d6b4f4`; all 20 hashes passed. Worker branch started at `a7b9d5cd2e9ec2212689de0838bd46f91a9c4691`, final worker commit `eb0c7a64a9cebac30187f414a8f0b5421a7c9acf`; coordinator merge `bf7cc170c9fddcf40d843a9851958fe1d24cef6f`.
- **Finding:** The four selected host requests match the logged ordered visual-token patterns and have successful command/log/resource records. None has per-op shape or allocator traces. The existing optrace callback captures graph metadata during scheduler graph evaluation after backend splitting, so its records do not themselves prove backend eligibility/selection or a K26 decision.
- **Scope:** A follow-on host-only trace may establish per-op workload shape coverage tied to request/image hashes. It must preserve the primary checkout, avoid storing/inspecting answer labels, and explicitly state that CPU graph traces cannot establish PL assignment, physical traffic, or board performance. No SSH, board inference, tests, or bitstream work follows from B02.
- **Next step:** Freeze the exact runtime, CLI build inputs, four prompt/image metadata records and image hashes; verify output isolation and callback semantics before running one metadata-only host trace per request. Retain P3 `NO_GO_NOW`.

## 2026-09-24 — Dispatch B03 selected-request host traces

- **Decision:** Run one CPU-only graph-metadata capture for qids 35950, 34609, 35419, and 35005. This is the smallest experiment that fills B02's selected-request per-op shape gap without asserting a hardware mechanism.
- **Task setup parent:** `358234101d1d448419a907c4221a06d72220be10`; clean project baseline `094edc130489dc59dd9333e4ae6b0aa4c8013149`; pinned runtime `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`. The exact worker base will be recorded in `orchestration/activations/B03.md` before execution. Exact file hashes are in `orchestration/evidence_snapshots/B03_selected_qid_optraces/SOURCE.sha256`.
- **Capture semantics:** Source inspection confirms ggml scheduler eval callbacks run over backend-split graphs, so they expose scheduled graph nodes but do not directly report `supports_op` tests or chosen backend identity. The task may add an MTMD media-batch ordinal; that ordinal will not identify internal crops.
- **Activation:** Worker branch `agent/B03-selected-qid-optraces` starts from clean coordinator commit `2f31453557cdbb1501cdda33c52c32e0a3ef7cf2`; activation record `orchestration/activations/B03.md` freezes the branch, worktree and acceptance conditions. All 39 source hashes passed before activation. The experiment reads only the four frozen `command.json` records and image files; it does not parse the full baseline run manifest.
- **Boundaries:** Worktree-only writes; read-only primary source, image and model paths. No answer labels or generated answers, no per-op timing, no tests, no board SSH/inference/reboot/bitstream, and no GitHub publication. This cannot change P3 `NO_GO_NOW`.
- **Next step:** Verify all frozen hashes, execute the four bounded host captures, and integrate only after checking exact-base commit, clean worker tree, trace integrity, and the task's evidence limits.

## 2026-09-24 — Complete B03 capture; activate independent review

- **Capture commit:** `4d7ce5e5fa5e750833cb5a05b8b3a15364861134`, with exact parent `2f31453557cdbb1501cdda33c52c32e0a3ef7cf2`; worker tree is clean. All 39 frozen input hashes passed before and after collection.
- **Evidence result:** four CPU-only requests passed. Media-batch counts (5, 7, 7, 5 by qid 34609/35005/35419/35950) match B02 token-sequence lengths. Qid 35005 changes dense matrix shapes after the first group. Qid 35419 changes spatial orientation while retaining a shared dense matrix shape/stride set. Full details and hashes are in the worker handoff and derived JSON.
- **Interpretation:** the selected traces expose real ordered per-group shape changes and strengthen the exact per-op shape/stride static control. They do not establish backend eligibility from this callback, K26 costs, traffic, resource pressure, or method advantage. No candidate or novelty claim is promoted.
- **Review:** activated R02 on the exact B03 SHA; activation record `orchestration/review_activations/R02.md`. Coordinator integration waits for its committed independent review.
- **Stage decision:** R01 remains **FAIL**; P3 remains `NO_GO_NOW`. B03 involved no tests, answers/annotations, source checkout changes, board activity, or remote GitHub actions.
