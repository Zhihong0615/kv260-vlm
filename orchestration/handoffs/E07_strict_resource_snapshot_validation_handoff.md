# E07 strict resource snapshot validation handoff

## Build identity

- Base and required direct parent: E06 target `4403b5ffdc7c4a8f40fc0b4451aba451f87077c0`.
- Branch/worktree: `agent/E07-strict-resource-snapshot-validation` / `/home/zhiro/research/kv260-vlm-workers/E07-strict-resource-snapshot-validation`.
- E07 input manifest SHA-256: `d05f56e523e80598279ed3119ca0b1c6db1d4c0f28e4975cdfa88e20eb611fff`. All 14 frozen entries passed before edits. The parser and focused test naturally no longer match their frozen hashes after this change; the other 12 entries remain unchanged.
- Changed paths: `scripts/parse_board_textvqa_pilot.py`, `tests/test_p2_resource_snapshot_contract.py`, and this handoff only.
- The target commit directly parents the exact base above; post-commit checks confirmed the worktree is clean. The exact target commit and this handoff's own SHA-256 are returned in the builder completion message because they cannot be embedded in their own tracked content.

| Frozen input | SHA-256 |
|---|---|
| Parser before E07 | `92e7bf4edc797ca360aa9647fe54b5a21c224236ac123d2a9aa7ad3377f2641e` |
| Focused test before E07 | `ef7ae9b926385b3cb58c0202c09189f402ef80cf930981621272c5dde9ba05b9` |
| E06 handoff | `018f7a3c408162ac7ed8d754c80bc421323ecca62a9073060ccbcc5596596bcc` |
| Frozen runner | `cf0577bac5bc39eb42e43289eead86febeb30e6012adf0254860f3e24437d1fc` |
| Frozen pilot protocol | `4629db39f822dc8f0fd6f0ec619b1f36c1632406f035aca5860643c86567fce3` |
| R09 review | `54cc72fa7824c06b31f7a3a5b0cf4cc40b47c37e53d88b7c13012eb807f42d3a` |
| R09 handoff | `dea56895ccbcb70f7bbaaf91b006428adcd2f98353e08edb995cc67eeb251e35` |
| R09 task brief | `76b704849739a2ab5010d50dd9c06cfb0552366a3a196f45743c512e58b8b5b8` |
| R09 activation | `a94a4865d8ffcd88d230c33089fc9ae73abc62895edaa991e675849453785d53` |
| R09 source manifest | `ef4d533fdbceef7014f7db5300268a48ead0573822db5f649b5c286e4ab6f4c2` |
| E06 task brief | `edb1dd03e6539f044704ae4e3431e40dbe6c2c82a32670661a974d3c294126c2` |
| E06 activation | `cec916913840dc92bd91d33ac878cfaf18e46e24824cb927c6a7e10015fdfb26` |
| E06 source manifest | `7858293b39e69f2cb0e3a9a5449646ef0f4c6502fee8dedec131ba613e1656c6` |
| Authorized taskbook | `ad5e705e3a34510a28f1468ea619841e339b41a93a0c643821dbc80e53dc7b25` |

## Corrected contract

- The parser validates both raw embedded-worker `rich_snapshot()` records, including their full runner-shaped fields, nested service and PackageKit records, memory and vmstat values, loadavg format and finite nonnegative loads, process rows, board identity, thresholds, exact snapshot scope, and timeout identity. It rejects missing/malformed values and internally inconsistent records. Direct field violations with an empty `gate_reasons` list are classified `INCONSISTENT`; nonempty reasons remain a gate failure.
- The prelaunch and post-run timeout identities must each match the validated command identity. Prelaunch/post-run timestamps must also bracket the recorded CLI interval before the combined resource gate can pass.
- `resource_gates_verified` is true only when both snapshots pass. Post-run failure keeps `image_processing_verified` false. Pilot evidence still explicitly describes two point-in-time snapshots and `in_run_resource_monitoring_performed: false`; no continuous monitor is added. Host rehearsal retains its separate evidence scope and does not claim board measurements.
- Attempted-request denominator, empty-prediction/zero-score handling for failed attempts, answer scoring, and unrelated parser gates are unchanged.

## Verification and output hashes

- Focused command, run once: `python3 -m unittest discover -s tests -p test_p2_resource_snapshot_contract.py`
- Result: `Ran 11 tests ... OK`, covering both-pass, preflight/postflight failures, malformed containers and measurements, non-finite/negative loads, malformed process rows, empty-reason contradictions for service/memory/process gates, and rehearsal scope.
- Parser SHA-256: `325fee0fc07c6a9cbe03909e438b8761b81459ac057e93164b4dbf553acae87c`.
- Focused test SHA-256: `dfd6c808c0fe1b7eaee66ad69e4e197aaf4300d3d1d86e1792e7a85078b2ed2b`.
- Handoff SHA-256: recorded in builder completion message.

## Limits and remaining gates

This is parser and focused-test work only. No runtime execution, answer/annotation read, board or SSH access, inference, benchmark, broader test suite, syntax check, dry plan, reboot, bitstream, or GitHub action was performed. Snapshot passes remain point-in-time evidence and do not establish request-long resource safety. Independent exact-target R10 review is required before integration. P2-7 and all other execution gates remain open; no board-readiness claim is made. P3 remains `NO_GO_NOW`.
