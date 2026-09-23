# TASK E02 — Bounded offline remediation of current P2 runner findings

## Objective

Prepare an isolated source patch for the four code-level findings from E01 that can be addressed without a board session:

1. Sample per-process CPU use in host preflight before staging an image, failing closed on malformed or unobservable process state.
2. Record `MTMD_TEST_RESPONSE_MARKER` presence inside the board-side worker immediately before removing it from the CLI environment.
3. On host timeout of the remote worker, preserve partial stdout/stderr bytes and make at most one bounded read-only status check; recover only through the existing strict completed-manifest/copy-verification path, otherwise keep `REMOTE_STATE_UNKNOWN` and never retry the run ID.
4. Require a non-empty `--owner-window-ref` when `--execute` is requested, and record the exact supplied reference.

This is a source-only proposal in an isolated worktree. It does not close the board gate or authorize an inference run.

## Frozen source inputs

- E01 snapshot commit: `880096cc50f4d37692012136ef7d204856df40ca`.
- Exact source paths and hashes: `orchestration/evidence_snapshots/E01_p2_static_gate_review/SOURCE.sha256`.
- Verify all nine entries before and after; the snapshot tree is read-only.
- Copy only `board_cpu_preflight_remote.py` and `run_board_cpu_p2_textvqa.py` from the snapshot to their root project paths in the worker tree before editing. Do not copy or modify the parser, frozen test file, protocol, or review files.
- The exact worker start SHA and worktree are frozen in `orchestration/activations/E02.md` after this brief is committed.

## Required behavior

- Preserve all existing fail-closed behavior. CPU sampling must be bounded, use two samples over a fixed short interval, and treat permission/read/parse/process-race failures conservatively. The gate must execute before any board image staging.
- Host environment state must not be presented as board-worker environment provenance. The board worker records the marker state it actually observes immediately before removal.
- Timeout recovery may only inspect status once, use a fixed bound, and proceed to copy only after a valid complete manifest and the existing hash/receipt verification. Missing, partial, or contradictory state remains unresolved; do not launch the CLI again.
- A claimed owner window requires both the existing confirmation flag and a non-empty reference. Record the supplied reference exactly and do not claim that source code verifies an external reservation.

## Boundaries

- No primary-checkout writes; no tests, syntax checks, dry plans, benchmarks, SSH, board access, inference, reboot, bitstream work, or GitHub actions.
- No answer/annotation inspection or access to other dataset/model artifacts.
- Do not claim these edits are tested, board-ready, or sufficient for P3. P2-5 (point-in-time resources versus continuous monitoring), P2-6 (timeout executable identity), P2-7 (orchestration regression tests), the fixed review-path issue, ALPHA proof, live resources, and an inference owner window remain unresolved.
- Keep P3 at `NO_GO_NOW`.

## Deliverables

- Only the two updated runner/preflight Python source files copied from the frozen snapshot and edited in the isolated worktree.
- `orchestration/handoffs/E02_runner_remediation_handoff.md` with an exact finding-to-change map, source/output hashes, unresolved items, and a clear statement that no tests or board activity occurred.
- One clean commit on `agent/E02-runner-remediation`, with direct parent equal to the exact frozen worker base in `orchestration/activations/E02.md`.
