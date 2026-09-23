# Task ID

E01 — Current P2 TextVQA Gate Independent Reviewer

## Role

Independent static reviewer. Review the current P2 parser, runner, and preflight implementation. Do not implement fixes.

## Frozen input target

Input snapshot commit: `880096cc50f4d37692012136ef7d204856df40ca` — `freeze current P2 runner review inputs`.

Frozen evidence directory:
`orchestration/evidence_snapshots/E01_p2_static_gate_review/`

At the activated commit, verify `SOURCE.sha256` with `sha256sum -c` from the evidence directory and independently verify the worker branch, clean start state, and base commit recorded in the activation file. Stop on any mismatch.

The exact reviewed source hashes are:

- parser: `cdaa479d61a946e9bd243398389452e3337e2714b696ac73f1a380bae05ad032`
- runner: `38e6d81b04fbf78c5ff398940e1bc934f224a621595311145e5b1a074fcce526`
- read-only board preflight: `fad954fbef94946d12de9a22d67e82a15951a7d715a02201a7c92d968192aa02`
- focused test source, for static coverage review only: `8d89eed8cd92c3041a4b1170dad8b13f5e4c0b07fce7388e428d0fab3a84e3a9`

The two prior review files in the snapshot are context only. Their parser/runner hashes are stale and they do not satisfy the current gate. Independently inspect all current source; do not inherit their counts or conclusions.

## Scope

Review only files in the frozen evidence directory. Examine parser input/label/attempt-state validation, command and model binding, image-event state, completion manifest and host receipt checks, runner preflight and resource gates, board worker lock and subprocess lifecycle, timeout/incomplete-copy behavior, ordered stop behavior, raw evidence provenance, and the focused test file's coverage by static inspection.

Report P0/P1/P2 findings with exact snapshot file paths and line numbers, concrete failure conditions, consequences, and bounded repair criteria. Distinguish source consistency from dynamic proof. Identify any condition that makes the current-SHA reviews unacceptable to the execution gate.

## Forbidden work

- Do not modify reviewed source, prior reviews, dry-plan evidence, or global status.
- Do not run tests, dry plans, syntax checks, benchmarks, SSH, board commands, or inference.
- Do not access primary-checkout files, raw runs, chat histories, or network sources.
- Do not create GitHub issues, push, or open a PR.

## Deliverables

1. `reviews/current_p2_gate_independent_review.md`, with frontmatter:
   - `review_mode: independent_static`
   - `reviewer_role: independent_reviewer`
   - exact `parser_sha256`, `runner_sha256`, and `preflight_sha256`
   - explicit P0/P1/P2 counts
2. A compact `orchestration/handoffs/E_current_p2_gate_review.md` naming the exact input target, reviewed hashes, conclusion, findings, and whether each review can satisfy the current runner gate.

The runner gate accepts a review file only if it contains the exact current subject SHA, the two independent-review fields above, and P0=0 and P1=0. Do not suppress a real finding to satisfy this mechanical condition; if P0/P1 is nonzero, report it and say the gate must remain closed.

## Acceptance

Commit the report and handoff on the activated worker branch. The worktree must be clean at final HEAD. Do not change the global go/no-go or claim board execution readiness.
