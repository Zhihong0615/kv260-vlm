# TASK E03 — Bounded preflight input-validation hardening

## Frozen base and inputs

- Coordinator source base: `c550d3fe7e5272e6fee42d259d7f861b55ea4b2a`.
- Builder branch/worktree: `agent/E03-runner-validation-hardening` / `/home/zhiro/research/kv260-vlm-workers/E03-runner-validation-hardening`.
- Build directly from the exact frozen base above. The final worker commit must directly parent it and leave the worktree clean.
- Four-entry source manifest: `orchestration/evidence_snapshots/E03_runner_validation_hardening/SOURCE.sha256`; SHA-256 `3df5b3862b6da6966a1be0c4bbabdc935393b428f0014b474e5004b7feb97090`.
- The two source files are exact E02 outputs reviewed by R04. R04 review report and handoff are frozen context for the two conditional residuals.

## Objective

Address only R04 conditional findings P2-1 and P2-2 in the frozen host/board CPU preflight runner:

1. A non-finite or negative `loadavg` first token must not compare as an acceptable load. Validate it as a finite nonnegative number at both applicable gates (host snapshot gate and board-side worker gate) and fail closed through the existing structured block/error path before input staging or CLI launch.
2. Malformed `process_cpu_rows` must not trigger an unhandled `KeyError` while evaluating CPU thresholds after schema validation has already identified an unknown row. Preserve the normal structured `PREFLIGHT_BLOCKED` and nonstart-record path so an operator gets an auditable result and does not strand an append-only raw output directory.

Use the smallest source change that satisfies those behaviors. Preserve existing valid-input thresholds and successful-run semantics.

## Scope and deliverables

- Modify only `scripts/run_board_cpu_p2_textvqa.py` and, only if needed, `scripts/board_cpu_preflight_remote.py`.
- Add only `orchestration/handoffs/E03_runner_validation_hardening_handoff.md` as a new deliverable.
- The handoff must list exact base/target SHAs, direct-parent and clean-tree evidence, changed paths, output hashes, behavior addressed, and all remaining gate limitations.
- Do not add or run tests, syntax checks, dry plans, benchmarks, inference, board/SSH actions, reboot, bitstream work, answer/annotation reads, or GitHub activity.
- Do not modify the primary checkout or the frozen global `status/go_no_go.md`.

## Acceptance and review gate

- Demonstrate from static code inspection that `nan`, `inf`, `-inf`, negative load, missing/malformed load, and malformed CPU rows become structured blocked states before image staging and CLI launch.
- Preserve finite nonnegative load and valid CPU-row behavior and current configured thresholds.
- Change no files outside the two named source files and the E03 handoff.
- Commit directly on the exact base, report all hashes, and leave the worker worktree clean.
- Independent exact-SHA review is required before coordinator integration. This source hardening does not establish board readiness or clear E01 P2-5/6/7, configured fixed review paths, ALPHA proof, current live resources, an external owner window, or any other execution gate. P3 remains `NO_GO_NOW`.
