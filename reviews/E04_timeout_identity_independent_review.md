# R07 independent review: E04 timeout identity

## Verdict

**PASS for E04's P2-6 timeout identity change.** Findings: P0 0, P1 0, P2 1. The single P2 is the separately documented marker-schema mismatch between the current worker and restored parser; it is outside E04's timeout scope and prevents claiming that the parser is ready to accept a successful current-worker record. This is a static source review only and makes no live-board or readiness claim.

## Frozen identities and hashes

- Reviewed target: `4dad4f86792ac3e29b5cdb4db392101dc398e745`; direct parent: `e6d867280badf8ce20cafc5082532cfc491058a1`.
- Reviewer branch/worktree: `agent/R07-E04-review` / `/home/zhiro/research/kv260-vlm-workers/R07-E04-review`. The target worktree was clean at review start. The target diff contains only the two runner/preflight files, the added parser, and the E04 handoff. The builder worktree was also clean at the same target.
- R07 brief SHA-256: `ccdc2f7ce2da979ac08f4acb1ea24037c38c1ff60f21ccb098e1a01f87b2844d`.
- R07 activation SHA-256: `6fe169c363a28306e012da4da78847f40995a1d5f84e18d51b9caccb5b4214de`.
- R07 output-manifest SHA-256: `9762359327070c54f212e86ed6900024c2efc555b7bf8e6e6a4cc56ae47ba0a9`; all four entries verified from the target worktree:

| Target output | SHA-256 |
|---|---|
| `scripts/run_board_cpu_p2_textvqa.py` | `cf0577bac5bc39eb42e43289eead86febeb30e6012adf0254860f3e24437d1fc` |
| `scripts/board_cpu_preflight_remote.py` | `16d5bf8a2158dd16f409fb6708fe60440cc95585e98f41044ce5732b192c9616` |
| `scripts/parse_board_textvqa_pilot.py` | `120c88faf788e73b2257dbab545572a0e6bf46864ab4ed30628191c43772baa3` |
| `orchestration/handoffs/E04_timeout_identity_handoff.md` | `9c26820d843807224c4614cdf8955cad72913a77edcf506342061b570db1ba35` |

- E04 brief SHA-256: `06b83a7c5892590b1af6078cabd68f923bb79d50af1d2b67eaaa5e565f6e5c29`.
- E04 activation SHA-256: `68799f0738c87b175c3e3288e4eea74eaf0c0d55cb8803f099a0a44a5e1de37a`.
- E04 seven-entry input-manifest SHA-256: `67e632687bc35073fb7a051d257373d0c94b054673d1ce9758b4ff3f224c8a5c`. All seven entries verified from the coordinator repository root:

| Frozen input | SHA-256 |
|---|---|
| `scripts/run_board_cpu_p2_textvqa.py` | `aa44a21e98ed6bbded3681ba80f3f2f81ed5496dabf6b1f5a726f413e7270528` |
| `scripts/board_cpu_preflight_remote.py` | `2366b7f5291fbb51e859e943a7453baa033cf41ed64668017689d97ddc9db959` |
| `orchestration/evidence_snapshots/E01_p2_static_gate_review/scripts/parse_board_textvqa_pilot.py` | `cdaa479d61a946e9bd243398389452e3337e2714b696ac73f1a380bae05ad032` |
| `reviews/current_p2_gate_independent_review.md` | `569712d404eb4cc2d18aa10759d37a2928cd1b03df2fcf493fc9ab4e0330ef1f` |
| `reviews/E03_preflight_validation_independent_review.md` | `c8d30be4b1414ba08807f7c0cd8736447ca8e2c13234545cb0ac8237589f2688` |
| `orchestration/handoffs/R06_E03_review_handoff.md` | `2fe1d5c0034a40c940a812226dfd278757a9aa9f116fd5c788c89487f95e3b9e` |
| `orchestration/handoffs/E03_runner_validation_hardening_handoff.md` | `b6151a144f3b4decba3f4507c479bffd625feb8c71b9e37d32d1d2c4b60000d6` |

## P2-6 review

The read-only preflight fixes the executable entry point at `/usr/bin/timeout`, resolves it, verifies it is a regular executable file, hashes it, and reports an unusable identity on lookup/hash failure (`scripts/board_cpu_preflight_remote.py:19-41`). The snapshot exposes that identity and keeps `tools_present["timeout"]` as the fixed-path `usable` value (`:233-245`).

The host resource gate requires exactly the four identity fields, the fixed path, an absolute resolved path, a lowercase 64-character SHA-256, and `usable is True`; otherwise it adds `TIMEOUT_EXECUTABLE_UNKNOWN` (`scripts/run_board_cpu_p2_textvqa.py:124-133`). The preflight response is validated and gated before the remote input directory is created or the JPEG is copied (`:1070-1114`, then staging at `:1122-1147`). A missing or malformed identity therefore stops before image staging.

On the board, the embedded worker accepts only the configured identity and fixed path (`scripts/run_board_cpu_p2_textvqa.py:486-499`), then recomputes path, resolution, usability, and hash (`:410-418`). Immediately before writing the launch record and calling `Popen`, it requires `argv[0] == /usr/bin/timeout` and exact equality between the recheck and preflight identity; a mismatch raises before `Popen` (`:640-660`). The inner command begins with the fixed path (`:923-931`), and the remote watchdog command does as well (`:1149-1151`). Static inspection found no board timeout invocation selected by bare `timeout` through `PATH`; Python `subprocess.run(..., timeout=...)` arguments are host-side duration controls, not executable selection.

The command record stores preflight and rechecked identities plus a timestamp before launch (`:648-657`). Complete results record both identities and the verification timestamp (`:677-689`); partial started results do likewise (`:745-784`). The worker transport record includes the expected identity on normal and watchdog-timeout paths (`:1156-1172`). Host-generated non-start results explicitly record null identity paths/hashes, `identity_verified: false`, and a null recheck time (`:882-916`); worker-side failures before successful `Popen` record their observed recheck state (`:706-721`).

The parser requires the exact absolute timeout argv (`scripts/parse_board_textvqa_pilot.py:394-406`), validates identity shape and usability (`:132-143`), compares the command identity with its recheck and launch flag (`:543-548`), checks recheck time against CLI start and result time (`:571-574`), and binds execution-result path/resolved-path/hash fields plus the preflight identity to the command identity (`:622-639`). Incomplete started attempts remain unscorable rather than accepted as complete (`:489-516`, `:714-720`). These source paths satisfy E04's P2-6 acceptance criteria.

## P2-1 — separate marker-schema mismatch

`scripts/parse_board_textvqa_pilot.py:56-80` defines `EXECUTION_KEYS` without `marker_was_present_before_removal` and defines `ENVIRONMENT_KEYS` as `MTMD_TEST_RESPONSE_MARKER`, `marker_removed_before_launch`, and `marker_was_present_before_removal`. The current worker emits the extra result key at `scripts/run_board_cpu_p2_textvqa.py:687` and emits command environment keys `marker_name`, `marker_present_before_removal`, `marker_present_in_cli_environment`, and `marker_removed_before_launch` (`:653-656`).

The parser's exact-key check rejects a normal worker `result.json` before it reaches command validation (`scripts/parse_board_textvqa_pilot.py:434-441`); the parser catch path records `ATTEMPT_STATE_INVALID` and returns `ATTEMPTED_SCORED_EMPTY` (`:478-487`). Even if that result key were absent, the command environment would fail the parser's exact-key/value check (`:703-710`). The consequence is that a successful current-worker run cannot be accepted by this parser. This mismatch predates E04's P2-6 change and is disclosed in the E04 handoff. Bounded fix: align the worker and parser marker field names and exact-key/type/value rules in a separate scoped change, then review that change independently. Do not infer parser acceptance from this PASS.

## Limits and remaining gates

No tests, syntax checks, dry plans, benchmarks, code execution, SSH, board commands, inference, or answer/annotation reads were performed. The target board's live `/usr/bin/timeout` identity was not observed. E01 P2-5/P2-7, configured review paths, ALPHA proof, live resource checks, owner-window evidence, and all other external execution gates remain open; P3 remains `NO_GO_NOW`.
