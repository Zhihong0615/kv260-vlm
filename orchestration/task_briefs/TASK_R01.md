# Task ID

R01 — Adversarial Research Reviewer

# Role

Independent reviewer. Do not participate in A/B/C candidate construction and do not review chat summaries.

# Current project HEAD

Queued. At activation, Scheduler will freeze the exact integration/base commit containing the Task Brief, A/B/C handoffs, their referenced input hashes, and the unchanged global go/no-go. Record that exact SHA here before dispatch. Do not start against today's dirty source checkout.

# Branch / Worktree / Base commit

Planned branch: `agent/R01-candidate-review`  
Worktree: Scheduler assigns a new isolated worktree at activation.  
Base commit: set to the exact frozen input commit at activation.  
Required start state: clean worktree; branch and `git rev-parse HEAD` must match the activated brief. Stop on any mismatch.

# Stage

Queued after the A/B/C handoffs are committed. D01 is not a dependency.

# Question

Do any proposed architecture candidates establish a real, falsifiable contribution beyond the closest FPGA/LLM/VLM mechanisms and the strongest static control, using evidence that supports the stated KV260 + MiniCPM-V claims?

# Read first

At activation, read only:

1. This frozen task brief at its activated commit.
2. The frozen `status/go_no_go.md`.
3. The frozen `literature/independent_novelty_review.md`.
4. `orchestration/handoffs/A_novelty_handoff.md`.
5. `orchestration/handoffs/B_workload_handoff.md`.
6. `orchestration/handoffs/C_architecture_candidates.md`.
7. The primary papers and exact raw/derived evidence cited by A/B/C.
8. The source snapshot/hash manifests named in the handoffs.

Do not inspect uncommitted files or use worker chat histories.

# Known facts

- Broad PhaseMap novelty was rejected; P3 remains NO_GO_NOW.
- Existing prior work already covers phase assignment, fixed-shape visual-token normalization, streaming/fusion, matrix dispatch, KV movement/residency, command aggregation, and bank/port assignment in adjacent settings.
- Current evidence is mainly host-side; it does not prove KV260 traffic, physical occupancy, PS–PL cost, or complete board VLM performance.
- A/B/C handoffs and the current frozen commit do not yet exist; this task must remain queued until they are committed.

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

Do not begin until the Scheduler publishes the activation SHA and all required committed handoffs are present. Stop if the input hashes fail or the review target changes. Do not work around missing evidence with chat context.
