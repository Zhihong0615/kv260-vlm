# R09 independent review: E06 point-in-time resource evidence

## Verdict

**FAIL.** Findings: P0 0, P1 1, P2 0. E06 correctly distinguishes prelaunch and post-run snapshots and preserves the attempted-request scoring behavior, but its resource classifier can mark `resource_gates_verified` true for incomplete or semantically inconsistent snapshot data. This contradicts the fail-closed evidence contract.

## Frozen identities and hashes

- Reviewed target: `4403b5ffdc7c4a8f40fc0b4451aba451f87077c0`; direct parent: `25a156a3d1bfe3292a5f7078225753b8455532b0`.
- Reviewer branch/worktree: `agent/R09-E06-review` / `/home/zhiro/research/kv260-vlm-workers/R09-E06-review`; it was clean at review start and checked out at the exact target. The target commit changes only the parser, focused test, and E06 handoff.
- R09 brief SHA-256: `76b704849739a2ab5010d50dd9c06cfb0552366a3a196f45743c512e58b8b5b8`.
- R09 activation SHA-256: `a94a4865d8ffcd88d230c33089fc9ae73abc62895edaa991e675849453785d53`.
- R09 seven-entry input-manifest SHA-256: `ef4d533fdbceef7014f7db5300268a48ead0573822db5f649b5c286e4ab6f4c2`; all entries verified from the exact target worktree.
- E06 task brief SHA-256: `edb1dd03e6539f044704ae4e3431e40dbe6c2c82a32670661a974d3c294126c2`.
- E06 activation SHA-256: `cec916913840dc92bd91d33ac878cfaf18e46e24824cb927c6a7e10015fdfb26`.
- E06 four-entry input-manifest SHA-256: `7858293b39e69f2cb0e3a9a5449646ef0f4c6502fee8dedec131ba613e1656c6`.

| E06 frozen target output/input | SHA-256 |
|---|---|
| `scripts/parse_board_textvqa_pilot.py` (target) | `92e7bf4edc797ca360aa9647fe54b5a21c224236ac123d2a9aa7ad3377f2641e` |
| `tests/test_p2_resource_snapshot_contract.py` | `ef7ae9b926385b3cb58c0202c09189f402ef80cf930981621272c5dde9ba05b9` |
| `orchestration/handoffs/E06_point_in_time_resource_contract_handoff.md` | `018f7a3c408162ac7ed8d754c80bc421323ecca62a9073060ccbcc5596596bcc` |
| Frozen parser before E06 | `c98da380900582c22cebba90134170c1dd0f81c0f853c8dc67e5c82c98981281` |
| Frozen pilot protocol | `4629db39f822dc8f0fd6f0ec619b1f36c1632406f035aca5860643c86567fce3` |
| Current P2 gate review | `569712d404eb4cc2d18aa10759d37a2928cd1b03df2fcf493fc9ab4e0330ef1f` |
| Authorized taskbook | `ad5e705e3a34510a28f1468ea619841e339b41a93a0c643821dbc80e53dc7b25` |

The E06 handoff reports the focused command `python3 -m unittest discover -s tests -p test_p2_resource_snapshot_contract.py` and `Ran 5 tests ... OK`. I confirmed that statement from the frozen handoff without rerunning the command.

## P1-1 — incomplete or inconsistent snapshot data can be classified PASS

`classify_resource_snapshot_evidence()` validates the schema, `gate_reasons` container, service/PackageKit container types, and timestamp (`scripts/parse_board_textvqa_pilot.py:175-197`, `:221-226`). For prelaunch it adds type checks for memory, disk, load text, process-list container, and timeout identity (`:198-220`), but it only parses the first load token with `float()`: it does not reject NaN or negative values (`:213-216`). The status itself is then selected solely from whether `gate_reasons` is empty (`:225-226`).

There are concrete false-pass paths:

1. A prelaunch load value of `nan` is accepted by `float()`. The later detailed gate checks only `float(loadavg_first_token) > 1.5` (`:734-741`); NaN compares false, so an empty `gate_reasons` list can still lead to `resource_gates_verified: true`.
2. For `post_run`, the helper skips the prelaunch-only field checks entirely (`:198-220`). A post-run snapshot can omit `memory_kib`, `loadavg`, `home_free_bytes`, and `selected_processes`, yet be classified PASS if it has an empty reasons list, structurally typed service/PackageKit containers, and a valid timestamp. The parser's later post-run checks validate the service container but not service values, and validate PackageKit values only (`:760-768`). Thus an `apt-daily.service` value inconsistent with an empty reason list can pass; after those checks the combined flag is assigned from the helper at `:785`.
3. Prelaunch `selected_processes` rows need only be dictionaries in the helper (`:208-212`). The later parser only looks for the unattended-upgrader name and role (`:751-754`); a row missing or mistyping required process identity fields can evade that check while an empty reasons list yields PASS.

If the other request evidence is valid, these paths can leave `resource_gates_verified` true and satisfy the pilot branch of `resource_gate_for_mode_passed`, allowing `image_processing_verified` to become true (`:826-833`). The focused fixtures do not cover these cases: the malformed test removes only `systemd_service_states`, `packagekit_transaction_state`, or `gate_reasons` from a post-run snapshot (`tests/test_p2_resource_snapshot_contract.py:65-72`), while its shared fixture supplies load, memory, and empty process rows (`:6-36`). The handoff's broad statement that missing/malformed required fields fail closed and that detailed resource checks support the combined PASS therefore exceeds the implementation (`orchestration/handoffs/E06_point_in_time_resource_contract_handoff.md:19-20`).

**Bounded fix:** validate a complete resource-snapshot schema for both stages, reject non-finite/negative load values, validate required process-row fields, and check post-run service/resource values against the same frozen gate semantics before returning PASS. Add focused fixtures for NaN/infinity, missing post-run measurements, malformed process rows, and service values inconsistent with empty reasons. Keep `resource_gates_verified` false unless both snapshots pass those checks.

## Confirmed behavior and scope

- Pilot output distinguishes prelaunch and post-run status, states `board_prelaunch_and_post_run_point_in_time_snapshots_only`, and hard-codes `in_run_resource_monitoring_performed: false` (`scripts/parse_board_textvqa_pilot.py:230-239`). This does not imply continuous monitoring.
- A non-empty gate-reason list produces `FAIL` and a false combined gate; pilot image-processing verification requires `resource_gates_verified is True` (`:225-238`, `:826-835`). A started request remains attempted (`:518-523`), initializes its failed-attempt score to zero (`:573-575`), and returns an empty prediction on errors (`:848-851`). The attempted denominator and zero-score rule remain intact.
- Rehearsal reports `host_rehearsal_direct_local_file_hashes_only; board resources not sampled`, statuses `NOT_APPLICABLE`, and `resource_gates_verified: None` (`:163-173`). It does not claim a board resource gate was measured.
- The E06 parser diff adds the helper and its result plumbing; it does not weaken the existing absolute argv/timeout identity, image binding, label privacy, completion-manifest, or scoring checks (`:133-143`, `:261-330`, `:477-489`, `:612-650`, `:680-713`, `:772-851`).

No tests, syntax checks, dry plans, benchmarks, code execution, SSH, board access, inference, or answer/annotation reads were performed. This review does not establish live board resources, runtime parser success, in-run safety, or board readiness. P2-7 and all other external gates remain open; P3 stays `NO_GO_NOW`.
