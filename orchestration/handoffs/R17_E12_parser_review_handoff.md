# R17 Handoff — Independent E12 Parser Review

## Frozen target and verification

- Reviewer target: `6b4a3d5af46f7b44069a1a7d36e5bad88167b960` (`Fix parser label and QID contracts`).
- Required direct parent: `ada49814f53f3c16b3e36383dcee65cb93473118`.
- Reviewer branch/worktree: `agent/R17-E12-parser-review`, `/home/zhiro/research/kv260-vlm-workers/R17-E12-parser-review`.
- Source manifest SHA-256: `5396cca3e5576bc40bf8ac21f945afc9922bcea7f306ebcc6b68cc823e7da1a7`; all entries passed `sha256sum -c` before review or test.
- E12 parser SHA-256: `48c834d6b803eb6a06f4be39f287913c461701ec606956c66493fe7f10d7e209`.
- Runner context SHA-256: `0ff88fd1780fa52ae5a30a6a47fe89827887d4360e20a14e9dc3269e6fb6ba92`.
- Focused test SHA-256: `a7ef837fc5a16129ce3fbe6d377ad5360b0a0d38423879c489ba275c014b9a23`.

## Review result

- Verdict: `PASS_WITH_P2_FINDINGS`, P0=0, P1=0, P2=1.
- Both R14 production findings are fixed in the exact parser: `answer_parse_ok` requires a boolean JSON value, and all current JSON `question_id` checks plus manifest pilot selection use strict integer matching that rejects booleans and floats.
- P2: the AST source-contract test marks a read as guarded based on containment anywhere in a `qid_matches` call subtree rather than verifying that the read is the helper's value argument. Static review confirmed all current parser reads are correctly passed as that argument. The review report describes the limitation and a test-hardening direction.
- The original R14 report is preserved at `reviews/audit/R14_adapter_PASS_WITH_P2_FINDINGS_20260924.md`, unchanged at its pinned SHA-256 `50512e90346b2be84c871ac983412c05361d359032ccf7b9b4205539bc5a26e8`.

## Authorized test record

Exactly one authorized command was run:

```text
$ python3 -m unittest discover -s tests -p test_p2_parser_label_qid_contract.py
......
----------------------------------------------------------------------
Ran 6 tests in 0.012s

OK
```

Exit code: 0. No other tests or parser/runner invocations were made. Test inputs were synthetic in-memory values; no answers, annotations, raw-run artifacts, board, SSH, network, runtime, inference, benchmark, reboot, or bitstream were accessed.

## Review outputs

- `reviews/kv260_cpu_p2_textvqa_output_contract_v2_independent_review.md` — SHA-256 `e9c1465941a0f4ec9ee489fd5a3d193a7bddb621dadb171bd392c56f05b89587`.
- `orchestration/handoffs/R17_E12_parser_review_handoff.md` — SHA-256 is recorded in the commit metadata / scheduler record to avoid a self-referential digest.
- Only these two review outputs are to be committed by R17.

This is source-level review and a synthetic helper test only. It does not validate real artifacts or board readiness. P3 remains `NO_GO_NOW`.
