# Task ID

R01 — Adversarial Research Reviewer

# Role

Independent reviewer. Do not participate in A/B/C candidate construction and do not review chat summaries.

# Current project HEAD

Frozen review target: `6dd1a83c4c771570b992a7ac83ec7de3d41ef60b` (exact A/B/C integration and evidence snapshot commit). The target includes the unchanged global `status/go_no_go.md`, byte-matched to source SHA-256 `16c10d283170670466fb69f54f324d76c3fdfbdd61d52bc46585bcb403038738`. The activated brief and record are committed later on the coordinator branch; they do not change the review target.

# Branch / Worktree / Base commit

- Branch: `agent/R01-candidate-review`
- Worktree: `/home/zhiro/research/kv260-vlm-workers/R01-candidate-review`
- Base commit / review target: `6dd1a83c4c771570b992a7ac83ec7de3d41ef60b`
Required start state: clean worktree; verify branch is `agent/R01-candidate-review` and `git rev-parse HEAD` equals the exact base above. Stop on any mismatch.

# Stage

Active after A/B/C handoffs were committed, integrated, and hash-frozen. D01 is not a dependency.

# Question

Do any proposed architecture candidates establish a real, falsifiable contribution beyond the closest FPGA/LLM/VLM mechanisms and the strongest static control, using evidence that supports the stated KV260 + MiniCPM-V claims?

# Read first

Read only the activated Task Brief and the frozen review target. The activated version is committed on the coordinator branch after the target SHA above; the Scheduler supplies its commit in the worker dispatch. The exact reviewed content is the target SHA above, not later scheduler metadata.

At activation, read only:

1. This frozen task brief at its activated commit.
2. The frozen `status/go_no_go.md`.
3. The frozen `literature/independent_novelty_review.md`.
4. `orchestration/handoffs/A_novelty_handoff.md`.
5. `orchestration/handoffs/B_workload_handoff.md`.
6. `orchestration/handoffs/C_architecture_candidates.md`.
7. The primary papers and exact raw/derived evidence cited by A/B/C, only through the paths named in their handoffs/manifests.
8. The source snapshot/hash manifests named in the handoffs; verify them before using any external read-only evidence path.

Run `sha256sum -c orchestration/source_snapshots/TASK_R01.sha256` from the review target. For external source files, use only exact paths in the committed A/B/C source manifests and stop on any hash mismatch. Do not inspect arbitrary uncommitted files or use worker chat histories.

# Known facts

- Broad PhaseMap novelty was rejected; P3 remains NO_GO_NOW.
- Existing prior work already covers phase assignment, fixed-shape visual-token normalization, streaming/fusion, matrix dispatch, KV movement/residency, command aggregation, and bank/port assignment in adjacent settings.
- Current evidence is mainly host-side; it does not prove KV260 traffic, physical occupancy, PS–PL cost, or complete board VLM performance.
- A01/B01/C01 handoffs are committed in the frozen target. Worker final SHAs are A=`ca2e2101027eb3596b6747c6a5e91bcc80df6f00`, B=`16bd6abf60a92bacca74d6f28124fb085b865153`, and C=`d0c52e94830ca17b5629e2f1f703840ab84e09ac`.
- The frozen target contains the exact A/B/C deliverable hashes in `orchestration/source_snapshots/TASK_R01.sha256`; each worker's own source manifest is also committed.

# Important uncertainties

- Whether any candidate names a true failure regime absent from closest work.
- Whether the workload evidence directly supports its trigger and benefit mechanism.
- Whether static shape/tile/bucket/batching/command-list controls already match it.
- Whether evaluation separates analytical, simulated, host, and board-measured results.

# Forbidden assumptions

- Do not invent a novelty claim or supply a replacement candidate.
- Do not alter golden data, measurements, scoring rules, hypotheses, go/no-go, or worker files.
- Do not infer hardware performance from host shape or allocator evidence.
- Do not treat a candidate's proposed minimum experiment as achieved evidence.
- Do not modify the review target to make it pass.

# Scope

Attack each candidate on: renaming of known mechanisms; prior-art overlap; workload representativeness; evidence-to-claim support; baseline strength; transition/full-request cost; alternative simple solutions; evidence class; numeric falsifiability; and stated failure boundary.
Give a status for each candidate and only one overall result: PASS, PASS_WITH_MAJOR_CAVEATS, or FAIL.
Quote exact commits and cite source paths/hashes. Provide a repair list if FAIL.

# Out of scope

- No candidate generation, implementation, experiments, board activity, score changes, or global decision changes.
- No review of chat transcripts.
- No GitHub Issue, push, PR, or remote setup.

# Deliverables

- `reviews/current_candidate_review.md` on the activated review branch.
- A compact handoff to Scheduler naming exact reviewed commit and review result.

# Acceptance criteria

- Review is adversarial, evidence-linked, and bound to the exact frozen commit.
- It checks all ten attack questions in the role instructions and distinguishes evidence classes.
- The only overall label is PASS, PASS_WITH_MAJOR_CAVEATS, or FAIL.
- No global status or research file is edited.
- If the target changes after review, repeat the review against the new exact SHA.

# Stop conditions

Do not begin until the Scheduler's committed activation record names the target and the start-state checks pass. Stop if any input hash fails or the review target changes. Do not work around missing evidence with chat context.
