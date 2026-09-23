# TASK R08 — Independent review of E05 parser marker-contract repair

## Frozen review target

- E05 worker commit: `ad41ad163c2b4d8064bfd2e8f59c953a1ae436ea`.
- Required direct parent: E04 target `4dad4f86792ac3e29b5cdb4db392101dc398e745`.
- Builder branch/worktree: `agent/E05-parser-marker-contract` / `/home/zhiro/research/kv260-vlm-workers/E05-parser-marker-contract`.
- Reviewer branch/worktree: `agent/R08-E05-review` / `/home/zhiro/research/kv260-vlm-workers/R08-E05-review`, checked out at the exact E05 target.
- E05 brief SHA-256: `6fea21f12bf84301965570189bdac8fd85f2ebfe5767d6473e27870dd1ba5888`.
- E05 activation SHA-256: `4418f3c5e35a6104f0eb4df68ee3818fed6d161b36bfab0369e1b81c620f0f06`.
- E05 four-entry input manifest SHA-256: `c7445ccf819b65f6850548b3a711c609c43411536461d6c231577a4c2044b46b`.
- Two-entry review output manifest: `orchestration/evidence_snapshots/R08_E05_review/SOURCE.sha256`.

## Review tasks

1. Verify the E05 commit directly parents the exact E04 target, the worktree is clean, and only the parser plus E05 handoff changed. Verify both output hashes from the E05 target worktree.
2. Verify the four E05 input hashes from the E04 target worktree and confirm the E05 brief/activation hashes from `/home/zhiro/research/kv260-vlm-orchestration`.
3. Independently compare the parser's exact command environment schema and required values with the frozen runner's actual emitted fields. Check missing/extra fields, wrong marker name, non-boolean values, marker retained in the CLI environment, and removal-state failures are rejected.
4. Trace started-result key handling: the marker-presence field is allowed, required and boolean for started records, and must equal the pre-removal command value. Confirm non-start records containing it remain contradictory and are rejected.
5. Confirm timeout argv/identity checks, label privacy, image binding, result completeness, and scoring paths were not weakened or changed by the marker-contract patch. Review the E05 handoff's scope and claim limits.

## Boundaries and outputs

- Static source review only. Do not run tests, syntax checks, dry plans, benchmarks, inference, answer/annotation reads, code, board/SSH actions, reboot, bitstream work, or GitHub activity.
- Add only `reviews/E05_parser_marker_contract_independent_review.md` and `orchestration/handoffs/R08_E05_review_handoff.md` on the reviewer branch.
- Report PASS/FAIL with P0/P1/P2 findings, exact target/output hashes, clean-tree evidence, and claim limits. Reviewer commit must directly parent the exact E05 target.
- Do not integrate before exact-target PASS. This source review does not establish parser success on runtime data or board readiness. E01 P2-5/P2-7, fixed review paths, ALPHA proof, live resources, owner-window evidence, and all other external gates remain open; P3 stays `NO_GO_NOW`.
