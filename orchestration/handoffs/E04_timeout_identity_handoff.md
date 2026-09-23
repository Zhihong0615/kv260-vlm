# E04 timeout identity handoff

## Build identity and scope

- Frozen base: `e6d867280badf8ce20cafc5082532cfc491058a1`.
- Branch: `agent/E04-timeout-identity`. The final E04 commit directly parents the frozen base and the worktree is clean. Its exact target SHA is returned in the builder completion message; a commit cannot include its own exact SHA in tracked content without changing that hash.
- Input manifest: `67e632687bc35073fb7a051d257373d0c94b054673d1ce9758b4ff3f224c8a5c`; all seven entries verified before the edits.
- The active parser was copied from the frozen E01 snapshot (`cdaa479d61a946e9bd243398389452e3337e2714b696ac73f1a380bae05ad032`); that snapshot was not modified.
- Changed paths: `scripts/run_board_cpu_p2_textvqa.py`, `scripts/board_cpu_preflight_remote.py`, `scripts/parse_board_textvqa_pilot.py`, and this handoff only.

## Behavior and output hashes

- Both remote timeout invocations use `/usr/bin/timeout`; the inner expected argv and parser require that absolute first argument.
- Read-only preflight records fixed path, resolved path, SHA-256, and usability. The host gate blocks unusable/malformed identity before staging. The worker compares its snapshot to that identity, then re-hashes immediately before the CLI wrapper launch. Command, result, and worker transport provenance carry the identity; the parser checks the preflight, recheck, result fields, and timestamps agree.
- `tools_present["timeout"]` remains present and derives from the fixed-path usability result, without PATH lookup.
- Runner SHA-256: `cf0577bac5bc39eb42e43289eead86febeb30e6012adf0254860f3e24437d1fc`.
- Preflight SHA-256 (also pinned in the runner): `16d5bf8a2158dd16f409fb6708fe60440cc95585e98f41044ce5732b192c9616`.
- Active parser SHA-256: `120c88faf788e73b2257dbab545572a0e6bf46864ab4ed30628191c43772baa3`.
- Handoff SHA-256 and the exact target commit SHA are reported in the builder completion message.

## Limits and remaining gates

This was static source work only; no tests, syntax checks, dry plans, SSH, board actions, inference, or answer/annotation reads were run. No live board `/usr/bin/timeout` identity was observed or claimed.

The frozen E01 parser has a separate pre-existing marker-schema mismatch with the current E03 worker: `ENVIRONMENT_KEYS` expects `MTMD_TEST_RESPONSE_MARKER`, `marker_removed_before_launch`, and `marker_was_present_before_removal`, while the worker emits `marker_name`, `marker_present_before_removal`, `marker_present_in_cli_environment`, and `marker_removed_before_launch`. The worker result also emits `marker_was_present_before_removal`, which is absent from parser `EXECUTION_KEYS`. This was left unchanged because E04 is limited to P2-6; resolve it in a separate bounded task before relying on parser acceptance of a successful run.

E01 P2-5/P2-7, configured fixed review paths, ALPHA proof, current live resources, owner-window evidence, and all other external execution gates remain open. P3 remains `NO_GO_NOW`. Independent exact-target R07 review is required before integration.
