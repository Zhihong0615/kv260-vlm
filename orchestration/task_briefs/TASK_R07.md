# TASK R07 — Independent review of E04 timeout executable identity

## Frozen review target

- E04 worker commit: `4dad4f86792ac3e29b5cdb4db392101dc398e745`.
- Required direct parent: `e6d867280badf8ce20cafc5082532cfc491058a1`.
- Builder branch/worktree: `agent/E04-timeout-identity` / `/home/zhiro/research/kv260-vlm-workers/E04-timeout-identity`.
- Reviewer branch/worktree: `agent/R07-E04-review` / `/home/zhiro/research/kv260-vlm-workers/R07-E04-review`, checked out at the exact E04 target.
- E04 brief SHA-256: `06b83a7c5892590b1af6078cabd68f923bb79d50af1d2b67eaaa5e565f6e5c29`.
- E04 activation SHA-256: `68799f0738c87b175c3e3288e4eea74eaf0c0d55cb8803f099a0a44a5e1de37a`.
- E04 seven-entry input manifest SHA-256: `67e632687bc35073fb7a051d257373d0c94b054673d1ce9758b4ff3f224c8a5c`.
- Four-entry review output manifest: `orchestration/evidence_snapshots/R07_E04_review/SOURCE.sha256`.

## Review tasks

1. Verify the E04 commit directly parents the frozen base, the worktree is clean, and the diff contains only the three named source files and E04 handoff. Verify all four entries in the R07 output manifest from the E04 target worktree.
2. Independently verify E04's seven-entry input manifest at `/home/zhiro/research/kv260-vlm-orchestration/orchestration/evidence_snapshots/E04_timeout_identity/SOURCE.sha256`, plus the E04 brief and activation hashes listed above. These activation records are in the coordinator worktree because they were created after E04's frozen source base.
3. Trace the exact inner CLI argv and outer remote watchdog command. Confirm each selects `/usr/bin/timeout` directly and that no relevant timeout launch still resolves a bare `timeout` through `PATH`. Confirm the parser requires the same fixed absolute argv.
4. Trace timeout identity from the read-only board preflight through the host gate, staging boundary, embedded worker configuration, and immediate pre-`Popen` recheck. Confirm missing, unusable, malformed, or changed identity blocks CLI launch; verify `tools_present["timeout"]` remains compatible and reflects fixed-path usability.
5. Trace path, resolved path, and SHA-256 fields through command/result/transport provenance and parser checks. Confirm the parser binds preflight identity, rechecked identity, recorded result fields, and timestamps to the exact command. Review complete, partial, and non-start result paths.
6. Review scope and claim limits. The handoff discloses a separate pre-existing marker-schema mismatch between the restored E01 parser and current worker records. Assess and report it separately from E04's P2-6 verdict; do not silently imply parser acceptance is ready for a board run.

## Boundaries and outputs

- Static source review only. Do not run tests, syntax checks, dry plans, benchmarks, inference, answer/annotation reads, code, board/SSH actions, reboot, bitstream work, or GitHub activity.
- Add only `reviews/E04_timeout_identity_independent_review.md` and `orchestration/handoffs/R07_E04_review_handoff.md` on the reviewer branch.
- Report PASS/FAIL with P0/P1/P2 findings, exact target/output hashes, clean-tree evidence, the separate marker-schema limitation, and remaining execution gates. Reviewer commit must directly parent the exact E04 target.
- No coordinator integration before an exact-target PASS. This static review does not establish live board timeout identity or board readiness. E01 P2-5/P2-7, configured review paths, ALPHA proof, live resources, owner-window evidence, and all other external gates remain open; P3 stays `NO_GO_NOW`.
