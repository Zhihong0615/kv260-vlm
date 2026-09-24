# TASK R16 — Independent review of E11's remote process gate fix

## Frozen target

- Exact E11 source commit and required direct parent: recorded in `orchestration/activations/R16.md` after E11 delivery.
- Review the runner, focused synthetic process-gate test, E11 handoff, and R15 P1 report.
- Required fixed runner review output: `reviews/board_cpu_p2_textvqa_runner_independent_review.md`.
- Preserve the prior R15 failure at `reviews/audit/R15_current_runner_BLOCKED_20260924.md`; do not edit or remove that archive.

## Objective and acceptance

1. Verify the exact E11 parent, clean worktree, task manifest, and source/test hashes before review.
2. Independently check that all R15 P1 paths fail closed at the final remote prelaunch decision: per-PID procfs failures are surfaced, before/after identity sets match, PID start identity is stable, counter/interval values are valid, and unknown state blocks CLI launch. Check that thresholds and the pinned preflight source did not change. Audit the focused test's fidelity to the production-used helper.
3. Source review plus one independent run of only `python3 -m unittest discover -s tests -p test_p2_remote_process_gate.py`. This is the sole execution permitted in the Reviewer worktree; use synthetic temporary procfs fixtures only. No other tests, imports, dry plans, runner, or remote worker execution.
4. Write a fresh report to the fixed runner review path binding the exact E11 runner SHA. Include `review_mode: independent_static`, `reviewer_role: independent_reviewer`, explicit P0/P1/P2 counts, exact test command/output, findings, and limitations. A P0/P1-free verdict is required to satisfy `review_gate`; P2 residuals must remain listed. Add an exact-SHA handoff and commit only the report and handoff, leaving the worktree clean.

## Boundaries

No board, SSH/network, runtime/inference/benchmark, reboot, bitstream, answer/annotation inspection, primary-checkout writes, or GitHub activity. No claim about live resources, owner window, runtime parser success, or board readiness.
