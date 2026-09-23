# TASK E07 — Close R09's fail-open resource snapshot classification

## Frozen source and review inputs

- Exact source base: E06 target `4403b5ffdc7c4a8f40fc0b4451aba451f87077c0`.
- Required direct parent: `4403b5ffdc7c4a8f40fc0b4451aba451f87077c0`.
- Builder branch/worktree: `agent/E07-strict-resource-snapshot-validation` / `/home/zhiro/research/kv260-vlm-workers/E07-strict-resource-snapshot-validation`.
- Frozen input manifest: `orchestration/evidence_snapshots/E07_strict_resource_snapshot_validation/SOURCE.sha256`.
- R09 exact-target review commit: `d5759cbbc6ee0d605c989cbc21a9def2273eb613`, directly parented E06 and returned **FAIL, P0=0/P1=1/P2=0**.

R09 found that `resource_gates_verified` can be true for incomplete or internally inconsistent snapshots. Concrete examples include post-run `apt-daily.service` marked active with an empty gate-reason list, missing post-run memory/load/process evidence, and prelaunch `loadavg` equal to `nan`; current tests do not cover these cases. The review report and handoff are frozen inputs.

## Objective and acceptance

Repair the pilot parser so a snapshot is not classified `PASS` solely because `gate_reasons` is empty. For both prelaunch and post-run evidence:

- Validate the complete required resource snapshot shape and value types actually emitted by the frozen runner, including nested service and PackageKit records and process rows. Missing, malformed, non-finite, negative, or semantically inconsistent evidence must not produce a passing status.
- Recheck frozen gate semantics against fields in each snapshot before allowing `PASS`: board architecture/CPU identity, memory/CMA/swap, disk space, finite nonnegative load no higher than 1.5, timeout-executable identity, service states, PackageKit state, and forbidden process conditions. If a directly checkable resource field violates its gate while `gate_reasons` is empty, classify the snapshot as malformed/inconsistent or failed and keep the combined gate false. A nonempty gate-reason list remains a gate failure.
- Set `resource_gates_verified` true only when both required snapshots are well-formed, internally consistent, and pass the frozen point-in-time gate checks. Preserve separate prelaunch/post-run fields and the explicit no-in-run-monitor scope.
- Preserve the existing attempted-request denominator, empty-prediction/zero-score rule for failed attempts, host rehearsal scope, answer scoring logic, and all unrelated parser gates.
- Expand only `tests/test_p2_resource_snapshot_contract.py` with valid runner-shaped fixtures and focused regressions for at least: prelaunch NaN/infinity load, missing post-run measurements, malformed process rows, and post-run service values that contradict an empty reason list. Keep the both-pass, preflight-fail, postflight-fail, malformed-container, and host-rehearsal cases.
- Run only this focused test module using `python3 -m unittest discover -s tests -p test_p2_resource_snapshot_contract.py`; no broader suite, syntax checks, dry plan, benchmark, inference, answer/annotation read, board, SSH, reboot, bitstream, or GitHub activity.

Passing prelaunch and post-run snapshots still provide only point-in-time evidence; do not add an in-run monitor or imply request-long safety. If a continuous monitor is required, it needs a separate versioned design and review.

## Scope and deliverables

- Modify only `scripts/parse_board_textvqa_pilot.py`, `tests/test_p2_resource_snapshot_contract.py`, and add `orchestration/handoffs/E07_strict_resource_snapshot_validation_handoff.md`.
- The handoff records exact base/target, parent and clean-tree evidence, changed paths, frozen input/output hashes, test command/result, corrected fail-closed contract, and remaining gates.
- Require independent exact-target R10 review before integration. R10 must check all R09 false-pass cases and scoring/scope invariants without rerunning tests.
- Do not modify the primary checkout or frozen snapshots. P2-7 and all other execution gates remain open; P3 stays `NO_GO_NOW`.
