# TASK R15 — Independent review of the current TextVQA runner

## Frozen target

- Review the exact coordinator source snapshot selected by the Scheduler activation record.
- Subject: `scripts/run_board_cpu_p2_textvqa.py`, SHA-256 `8f07232ef2bcfe78e3f5cd331273796de6db87402a8e502ca4980dc89682c577`.
- Interface context: `scripts/parse_board_textvqa_pilot.py`, SHA-256 `0e28f81cc26ec47cfe2488c680623c74accd1bef92d9a4f3a31ae2fa73ba3b8d`; pinned preflight source SHA `16d5bf8a2158dd16f409fb6708fe60440cc95585e98f41044ce5732b192c9616`.
- Required fixed output: `reviews/board_cpu_p2_textvqa_runner_independent_review.md`.
- Exact base commit, branch, worktree, and source manifest are in `orchestration/activations/R15.md`.

## Objective

Independently review current runner control flow, static checks before SSH, one-request bound, prior-case/ordered-stop behavior, host/remote preflight sequencing, timeout/status/copy evidence checks, lock handling, append-only recording, and parser integration. Identify unsafe transitions, ambiguous records, or claims unsupported by the implementation. Report concrete findings with severity and exact file/line references.

## Acceptance

1. Verify exact branch/base and all entries in `orchestration/evidence_snapshots/R15_current_runner_review/SOURCE.sha256`; stop if they do not match.
2. Review source only. Do not execute the runner or embedded/remote code, import modules, run tests, invoke a dry plan, or inspect answer/annotation contents.
3. Write the report at the fixed output path. Frontmatter must include `review_mode: independent_static`, `reviewer_role: independent_reviewer`, and `runner_sha256: 8f07232ef2bcfe78e3f5cd331273796de6db87402a8e502ca4980dc89682c577`. State explicit `P0: N`, `P1: N`, and `P2: N`; do not claim a clean pass if a P0/P1 remains.
4. Include scope, method, findings, limitations, and a clear exact-target verdict. Distinguish source-level safeguards from live board state, authorization, or resource evidence.
5. Add `orchestration/handoffs/R15_current_runner_review_handoff.md` with target/base, output SHA-256, verdict/counts, changed paths, and limitations. Commit only these two review artifacts on the assigned branch; leave the source unchanged and the worktree clean.

## Boundaries

No tests or code execution of any kind; no SSH, network, board, runtime, inference, benchmark, reboot, bitstream, answer/annotation inspection, primary-checkout writes, or GitHub activity. This review is not a board-readiness or owner-window attestation.
