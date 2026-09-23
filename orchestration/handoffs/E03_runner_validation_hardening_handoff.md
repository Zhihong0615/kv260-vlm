# E03 runner validation hardening handoff

## Target and scope

- Base commit: `c550d3fe7e5272e6fee42d259d7f861b55ea4b2a`.
- Target commit: the single E03 commit on `agent/E03-runner-validation-hardening`; its exact SHA is returned with this handoff. The target directly parents the base above.
- Branch started clean at the exact base; final worktree is clean after the commit.
- Changed paths: `scripts/run_board_cpu_p2_textvqa.py` and this handoff only.
- Output SHA-256 values are reported with the exact target commit.

## Behavior addressed

- The host snapshot gate and embedded board worker gate now parse the first load token as finite and nonnegative. Missing, malformed, non-finite, or negative values add `LOAD_STATE_UNKNOWN`; the existing structured preflight block/error path stops before input staging or worker CLI launch. Valid values retain the existing `MAX_LOAD1` / configured threshold.
- Host CPU-row schema validation is now captured before threshold evaluation. Malformed rows add `PROCESS_STATE_UNKNOWN` and are not indexed for `pid` or `cpu_cores`; valid rows retain the existing duplicate/PID checks and busy-core threshold. The existing `PREFLIGHT_BLOCKED` and nonstart record path remains in place.
- Static inspection only. No tests, syntax checks, dry plans, benchmarks, execution, board/SSH, inference, answer/annotation reads, or GitHub actions were performed.

## Remaining gates

This change is validation hardening only; it does not establish board readiness. E01 P2-5/6/7, configured fixed review paths, ALPHA proof, current live-resource checks, an external owner window, and all other execution gates remain open. P3 remains `NO_GO_NOW`. An independent exact-target R06 review must pass before coordinator integration.
