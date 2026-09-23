# R07 E04 timeout identity review handoff

## Verdict

**PASS for the E04 P2-6 timeout identity change.** Findings: P0 0, P1 0, P2 1. The P2 is the separately documented marker-schema mismatch between the current worker and parser; it is outside P2-6 and means parser acceptance is not ready to claim. This review establishes no live-board identity or readiness.

## Exact target and evidence

- E04 target: `4dad4f86792ac3e29b5cdb4db392101dc398e745`; direct parent: `e6d867280badf8ce20cafc5082532cfc491058a1`.
- Reviewer branch: `agent/R07-E04-review`; the exact-target worktree was clean before review and the builder worktree was clean at the same HEAD.
- R07 brief SHA-256: `ccdc2f7ce2da979ac08f4acb1ea24037c38c1ff60f21ccb098e1a01f87b2844d`; activation SHA-256: `6fe169c363a28306e012da4da78847f40995a1d5f84e18d51b9caccb5b4214de`.
- R07 output-manifest SHA-256: `9762359327070c54f212e86ed6900024c2efc555b7bf8e6e6a4cc56ae47ba0a9`; all four entries verified from the target tree. Their exact hashes are recorded in `reviews/E04_timeout_identity_independent_review.md`.
- E04 brief SHA-256: `06b83a7c5892590b1af6078cabd68f923bb79d50af1d2b67eaaa5e565f6e5c29`; activation SHA-256: `68799f0738c87b175c3e3288e4eea74eaf0c0d55cb8803f099a0a44a5e1de37a`.
- E04 seven-entry input-manifest SHA-256: `67e632687bc35073fb7a051d257373d0c94b054673d1ce9758b4ff3f224c8a5c`; all entries verified from the coordinator repository root. Exact entry hashes are in the review report.

## Findings and disposition

The preflight and host gate bind fixed path, resolved path, usability, and SHA-256 before image staging. The embedded worker rechecks the exact configured identity immediately before launch and refuses changed/unusable identity before `Popen`. The inner CLI argv and outer watchdog use `/usr/bin/timeout`, and the parser requires that absolute argv and cross-checks preflight, command, result, and timestamps. Complete and partial started records carry the recheck provenance; non-start records are explicit and do not assert CLI launch. Static source evidence supports PASS for P2-6.

P2-1: current worker record keys do not match the restored parser's exact marker schemas. It causes parser rejection of a normal result/command record; fix it in a separate bounded change before relying on parser acceptance. It does not alter the P2-6 timeout identity verdict.

No tests, execution, SSH, board access, inference, answer/annotation reads, reboot, bitstream work, or GitHub activity occurred. Do not infer live timeout identity or board readiness. E01 P2-5/P2-7, fixed configured review paths, ALPHA proof, live resources, owner-window evidence, and remaining external gates stay open; P3 remains `NO_GO_NOW`.
