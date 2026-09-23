# TASK E04 — Pin and attest the board `timeout` executable

## Frozen base and inputs

- Coordinator source base: `e6d867280badf8ce20cafc5082532cfc491058a1`.
- Builder branch/worktree: `agent/E04-timeout-identity` / `/home/zhiro/research/kv260-vlm-workers/E04-timeout-identity`.
- Build directly from the exact frozen base. The worker commit must directly parent it and leave a clean tree.
- Seven-entry source manifest: `orchestration/evidence_snapshots/E04_timeout_identity/SOURCE.sha256`; SHA-256 `67e632687bc35073fb7a051d257373d0c94b054673d1ce9758b4ff3f224c8a5c`.
- Rationale is frozen E01 finding P2-6: the inner CLI timeout and outer worker watchdog currently invoke bare `timeout`, and the parser does not bind the selected executable identity.

## Objective

Remove `PATH`-based timeout selection from both board-side invocations, bind the runtime command record to an absolute executable path and SHA-256 identity, and keep parser validation aligned with the command actually launched.

The active runner expects `scripts/parse_board_textvqa_pilot.py`, but this path is absent from the coordinator base. Add it from the frozen E01 snapshot parser (whose SHA-256 is `cdaa479d61a946e9bd243398389452e3337e2714b696ac73f1a380bae05ad032` and matches the current primary parser), then update it narrowly for the pinned timeout argv/identity contract. Do not edit the archived snapshot.

Use `/usr/bin/timeout` as the fixed absolute executable path and fail closed if it is unavailable, non-executable, or cannot be hashed. Record its resolved path and SHA-256 from read-only preflight; re-check the same identity immediately before the CLI wrapper is launched. The outer remote watchdog must use the same absolute path, and the execution records/parser must distinguish the path and hash from the remaining argv fields.

## Scope and deliverables

- Modify only `scripts/run_board_cpu_p2_textvqa.py` and `scripts/board_cpu_preflight_remote.py`.
- Add `scripts/parse_board_textvqa_pilot.py` from the frozen snapshot, then make only the changes needed for exact absolute timeout argv and identity validation.
- Add only `orchestration/handoffs/E04_timeout_identity_handoff.md` as a new deliverable.
- The handoff must report exact base/target SHAs, direct-parent and clean-tree evidence, changed paths, input/output hashes, path/identity binding, static behavior, and limitations.
- Do not add or run tests, syntax checks, dry plans, benchmarks, inference, board/SSH actions, reboot, bitstream work, answer/annotation reads, or GitHub activity.
- Do not modify the primary checkout or frozen review snapshots. Do not claim the target board's live timeout binary identity was observed; no board read is in scope.

## Acceptance and review gate

- Neither CLI nor watchdog launches bare `timeout` through `PATH`; the expected argv, actual worker argv, and remote watchdog command use the same fixed absolute path.
- A missing/unusable executable or identity mismatch blocks before CLI launch. The preflight path/hash and the rechecked worker path/hash are recorded in run provenance covered by existing integrity records.
- The adapter requires the absolute timeout argv and validates the associated path/hash fields; successful CLI option, timeout duration, and scoring semantics remain unchanged.
- Change no files outside the two runner/preflight sources, the active adapter path, and E04 handoff.
- Commit directly on the exact base and leave a clean tree. Independent exact-SHA R07 review is required before coordinator integration.
- This static patch does not establish the live board binary identity or board readiness. E01 P2-5/P2-7, owner-window evidence, ALPHA proof, current resources, fixed configured review paths, and all other external execution gates remain open. P3 remains `NO_GO_NOW`.
