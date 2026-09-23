# E05 parser marker-contract handoff

## Build identity

- Base commit: `4dad4f86792ac3e29b5cdb4db392101dc398e745` (E04 target); the E05 commit directly parents this base. The exact target SHA is returned in the builder completion message because a commit cannot include its own hash in tracked content.
- Branch: `agent/E05-parser-marker-contract`; the worktree started clean at the exact base and is clean after commit.
- Input manifest SHA-256: `c7445ccf819b65f6850548b3a711c609c43411536461d6c231577a4c2044b46b`; all four entries passed verification.
- Changed paths: `scripts/parse_board_textvqa_pilot.py` and this handoff only.

| Frozen input | SHA-256 |
|---|---|
| `scripts/parse_board_textvqa_pilot.py` before E05 | `120c88faf788e73b2257dbab545572a0e6bf46864ab4ed30628191c43772baa3` |
| `scripts/run_board_cpu_p2_textvqa.py` | `cf0577bac5bc39eb42e43289eead86febeb30e6012adf0254860f3e24437d1fc` |
| `orchestration/handoffs/E04_timeout_identity_handoff.md` | `9c26820d843807224c4614cdf8955cad72913a77edcf506342061b570db1ba35` |
| `reviews/current_p2_gate_independent_review.md` | `569712d404eb4cc2d18aa10759d37a2928cd1b03df2fcf493fc9ab4e0330ef1f` |

## Contract change

- The parser now requires exactly `marker_name`, `marker_present_before_removal`, `marker_present_in_cli_environment`, and `marker_removed_before_launch`. It checks the marker name, boolean types, removal, and that the variable was absent from the CLI environment; missing or extra fields fail closed.
- Started execution records must include boolean `marker_was_present_before_removal`, equal to the command environment's recorded pre-removal value. Because this is in `EXECUTION_KEYS` and remains in `START_EVIDENCE_KEYS`, its presence in a non-start record is contradictory.
- Timeout argv/identity validation, image and label checks, scoring behavior, and other parser semantics were left unchanged.
- Parser SHA-256: `c98da380900582c22cebba90134170c1dd0f81c0f853c8dc67e5c82c98981281`.
- Handoff SHA-256 and exact target commit SHA are returned in the builder completion message.

## Limits and review gate

This was static source work only; no tests, syntax checks, dry plans, execution, SSH/board access, inference, or answer/annotation reads were performed. Runtime parser success remains unverified. Independent exact-target R08 review is required before integration.

E01 P2-5/P2-7, configured fixed review paths, ALPHA proof, current live resources, owner-window evidence, and all other external execution gates remain open. P3 remains `NO_GO_NOW`.
