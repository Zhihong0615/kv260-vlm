# TASK E05 — Reconcile the TextVQA parser with runner marker records

## Frozen source and activation condition

- Planned source base: E04 target `4dad4f86792ac3e29b5cdb4db392101dc398e745`, after exact-target R07 PASS and coordinator integration.
- Builder branch/worktree: `agent/E05-parser-marker-contract` / `/home/zhiro/research/kv260-vlm-workers/E05-parser-marker-contract`.
- Four-entry source manifest: `orchestration/evidence_snapshots/E05_parser_marker_contract/SOURCE.sha256`; verify from the coordinator worktree.
- Do not activate this builder until R07 has passed. The target currently has a known parser/runner schema mismatch recorded in the E04 handoff.

## Objective

Align the active TextVQA parser with the current board runner's marker-environment and execution-result fields, while retaining exact schemas and fail-closed validation.

The E04 runner records `command.json.environment` with exactly `marker_name`, `marker_present_before_removal`, `marker_present_in_cli_environment`, and `marker_removed_before_launch`. The restored E01 parser currently expects different field names and a literal `MTMD_TEST_RESPONSE_MARKER=UNSET`. The runner's execution result also records `marker_was_present_before_removal`, which the parser's allowed execution-key set currently omits.

## Scope and deliverables

- Modify only `scripts/parse_board_textvqa_pilot.py` and add only `orchestration/handoffs/E05_parser_marker_contract_handoff.md`.
- Validate the exact current environment field names, marker name, boolean types, marker removal, and absence from the CLI environment. Reject missing or extra fields.
- Allow and require `marker_was_present_before_removal` on started execution records, validate its boolean type, and require it to equal the command environment's recorded pre-removal value. Keep it contradictory on non-start records.
- Preserve all unrelated argv, timeout identity, image, label privacy, timing, scoring, and output semantics.
- Handoff must include exact base/target identities, direct-parent and clean-tree evidence, changed paths, source/output hashes, static claim limits, and remaining external gates.
- Do not add or run tests, syntax checks, dry plans, benchmarks, inference, answer/annotation reads, code execution, SSH/board actions, reboot, bitstream work, or GitHub activity. Do not modify the primary checkout or frozen snapshots.

## Review gate

Queue independent exact-target R08 after the builder commit. Integrate E05 only after PASS. This source-level schema repair does not establish board readiness or prove the parser succeeds on runtime data. E01 P2-5/P2-7, fixed review paths, ALPHA proof, live resources, owner-window evidence, and all other external execution gates remain open; P3 stays `NO_GO_NOW`.
