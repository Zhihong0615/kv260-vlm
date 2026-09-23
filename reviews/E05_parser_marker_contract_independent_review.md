# R08 independent review: E05 parser marker contract

## Verdict

**PASS.** Findings: P0 0, P1 0, P2 0. The marker-environment and started-result contract matches the frozen runner, rejects malformed or contradictory marker records, and leaves non-start contradiction handling and unrelated parser checks intact. This is a static source review; it does not demonstrate runtime parser success or board readiness.

## Frozen identities and verified hashes

- E05 target: `ad41ad163c2b4d8064bfd2e8f59c953a1ae436ea`; direct parent: `4dad4f86792ac3e29b5cdb4db392101dc398e745`.
- Reviewer branch/worktree: `agent/R08-E05-review` / `/home/zhiro/research/kv260-vlm-workers/R08-E05-review`; clean at the target before review. The target diff changes only the parser and E05 handoff.
- R08 task brief SHA-256: `492e2a6ed1f7d83f4a33f667be3fafc6fc50cda4c4eb7636b088132cebe5627c`.
- R08 activation SHA-256: `d2efb962d7a8bdcc9206aa9e822c17fe97521033298d8c26a90e20861b22168a`.
- R08 output-manifest SHA-256: `16de931ea35db35f8cd629975b70db00c65a9969b665c96c0f8ac7442cebc76c`; both entries verified from the target worktree:

| Target output | SHA-256 |
|---|---|
| `scripts/parse_board_textvqa_pilot.py` | `c98da380900582c22cebba90134170c1dd0f81c0f853c8dc67e5c82c98981281` |
| `orchestration/handoffs/E05_parser_marker_contract_handoff.md` | `a47628e18c243b88cb37b97541496b87a38b69d1aee0b6df31c12a20d6aeca92` |

- E05 task brief SHA-256: `6fea21f12bf84301965570189bdac8fd85f2ebfe5767d6473e27870dd1ba5888`.
- E05 activation SHA-256: `4418f3c5e35a6104f0eb4df68ee3818fed6d161b36bfab0369e1b81c620f0f06`.
- E05 four-entry input-manifest SHA-256: `c7445ccf819b65f6850548b3a711c609c43411536461d6c231577a4c2044b46b`. All four entries verified from the E04 target worktree:

| Frozen input | SHA-256 |
|---|---|
| `scripts/parse_board_textvqa_pilot.py` (pre-E05) | `120c88faf788e73b2257dbab545572a0e6bf46864ab4ed30628191c43772baa3` |
| `scripts/run_board_cpu_p2_textvqa.py` | `cf0577bac5bc39eb42e43289eead86febeb30e6012adf0254860f3e24437d1fc` |
| `orchestration/handoffs/E04_timeout_identity_handoff.md` | `9c26820d843807224c4614cdf8955cad72913a77edcf506342061b570db1ba35` |
| `reviews/current_p2_gate_independent_review.md` | `569712d404eb4cc2d18aa10759d37a2928cd1b03df2fcf493fc9ab4e0330ef1f` |

## Contract review

The frozen runner records exactly `marker_name`, `marker_present_before_removal`, `marker_present_in_cli_environment`, and `marker_removed_before_launch`; its values are the marker constant `MTMD_TEST_RESPONSE_MARKER`, a boolean captured before removing it, `False`, and `True`, respectively (`scripts/run_board_cpu_p2_textvqa.py:637-656`). The parser now declares that exact environment key set (`scripts/parse_board_textvqa_pilot.py:78-81`) and rejects a non-object, missing or extra key, wrong marker name, non-boolean pre-removal state, a value other than the actual boolean `False` for CLI presence, or a value other than boolean `True` for removal (`:704-714`). Failures enter the existing command/input contract error path (`:716-717`) and prevent successful scoring (`:747-758`).

The runner includes `marker_was_present_before_removal` in its started result (`scripts/run_board_cpu_p2_textvqa.py:677-689`). The parser now permits that field in `EXECUTION_KEYS` (`scripts/parse_board_textvqa_pilot.py:56-70`); the started-record validation requires it to be a boolean and equal the pre-removal environment value (`:712-714`). Missing, non-boolean, or unequal values fail closed.

The field remains in `START_EVIDENCE_KEYS`: the set removes base non-start metadata and timeout identity fields, but not the marker field (`scripts/parse_board_textvqa_pilot.py:98-106`). Consequently, a non-start result containing `marker_was_present_before_removal` is rejected by the existing contradiction check (`:443-460`).

## Preservation and limits

The E05 diff is limited to the marker key sets and marker validation. The fixed absolute timeout argv and identity checks remain in place (`scripts/parse_board_textvqa_pilot.py:132-143`, `:394-406`, `:543-548`, `:622-640`). Label privacy checks, qid/image/path/SHA binding, and prelaunch verification remain (`:535-538`, `:551-571`); post-run image verification remains (`:682-690`). Result completeness, image-event validation, and scoring/status paths remain (`:719-758`). No unrelated parser behavior was changed in this target diff.

No tests, syntax checks, dry plans, benchmarks, code execution, SSH, board access, inference, or answer/annotation reads were performed. Runtime parser success remains unverified. E01 P2-5/P2-7, fixed review paths, ALPHA proof, live resources, owner-window evidence, and all other external execution gates remain open; P3 stays `NO_GO_NOW`.
