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
