# TASK E12 — Close the two R14 parser contract findings

## Frozen target and evidence

- Exact source base and required direct parent: `ada49814f53f3c16b3e36383dcee65cb93473118` (E11-integrated coordinator source plus preserved R14 audit report).
- R14 exact-target report: `reviews/audit/R14_adapter_PASS_WITH_P2_FINDINGS_20260924.md`, SHA-256 `50512e90346b2be84c871ac983412c05361d359032ccf7b9b4205539bc5a26e8`.
- Current parser subject before edits: `scripts/parse_board_textvqa_pilot.py`, SHA-256 `0e28f81cc26ec47cfe2488c680623c74accd1bef92d9a4f3a31ae2fa73ba3b8d`.
- Current runner context: `scripts/run_board_cpu_p2_textvqa.py`, SHA-256 `0ff88fd1780fa52ae5a30a6a47fe89827887d4360e20a14e9dc3269e6fb6ba92`.
- Frozen source manifest and its hash are recorded in `orchestration/activations/E12.md`.
- User taskbook: `/home/zhiro/Downloads/Codex_KV260_VLM_端到端研究任务书_v3.md`, SHA-256 `ad5e705e3a34510a28f1468ea619841e339b41a93a0c643821dbc80e53dc7b25`.

## Objective and bounded scope

Fix only R14's two P2 findings in `scripts/parse_board_textvqa_pilot.py` and add one focused local regression module.

1. `answer_parse_ok` is the only safe non-label metadata key. Accept it only as a JSON boolean; scalar text or any non-boolean value under that key must be treated as invalid/label-bearing. Preserve recursive scanning so nested label-bearing keys remain rejected.
2. Require JSON `question_id` values to be true integers, excluding booleans and float-equal values such as `38299.0`, wherever the parser compares an artifact/record QID to the expected QID. Apply the same type check when accepting manifest samples into the pilot QID map. Keep integer QID behavior unchanged.
3. Add `tests/test_p2_parser_label_qid_contract.py`. It must exercise the actual production `has_label_keys` and QID helper extracted from the parser source, not a duplicate implementation. Include boolean-safe versus scalar-text cases, nested label-key cases, integer acceptance, float-equal rejection, and boolean-as-integer rejection. Include a source-contract check that all parser JSON `question_id` comparisons use the strict helper. Use synthetic in-memory examples only; do not inspect manifest answers or raw-run data.
4. Preserve all scoring, answer parsing, resource gate, runner, schema, path, and board behavior. Do not change the runner or any other parser behavior outside these two findings.
5. Change only the parser, the new focused test module, and `orchestration/handoffs/E12_parser_contract_hardening_handoff.md` in the worker commit.
6. Run only `python3 -m unittest discover -s tests -p test_p2_parser_label_qid_contract.py`, at most twice total: once after the initial patch and a second time only if a correction is needed. No other test, import probe, parser/runner execution, dry plan, board, SSH, runtime, inference, benchmark, reboot, bitstream, network, answer/annotation inspection, primary-checkout write, or GitHub action.
7. Commit directly on the frozen target with a clean worktree. The handoff must include exact command/output for every invocation, changed paths, source/test/handoff hashes, and evidence limits. R17 independently reviews the exact E12 target; preserve the original R14 failure report unchanged at its audit path.

## Acceptance and limitations

The two findings are closed at source and synthetic-test level only after exact-target R17 reports P0=0/P1=0. Do not claim real artifact validation or board readiness. P3 remains `NO_GO_NOW`.
