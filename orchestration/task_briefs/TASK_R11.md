# TASK R11 — Independent review of E08 timestamp ordering

## Frozen target

- E08 target: `215d3c1acb6a3091a84f53cfdacb644d90116871`.
- Required direct parent: E07 target `6a658012e0ae8269c4c69efff884042be52058d4`.
- Builder branch/worktree: `agent/E08-resource-timestamp-ordering` / `/home/zhiro/research/kv260-vlm-workers/E08-resource-timestamp-ordering`.
- Reviewer branch/worktree: `agent/R11-E08-review` / `/home/zhiro/research/kv260-vlm-workers/R11-E08-review`, created at exact E08 target.
- E08 brief SHA-256 `4f71325bef50844d48f23b01f9f351df294db971adb97f5dc5504c662705d678`; activation SHA-256 `27d70577aea439623e232f176d4a080345502714c9950c48d23934b8465ae671`; 18-entry source manifest SHA-256 `4432b4293de9e74b6fc965e05cd1eb1302c9597a921f2befcc19f4e185b53d9e`.
- E08 parser SHA-256 `d31ef5a1df63ec1f0cd5a3c19c2a5f5ec34ea76b1d64ecb7be3aa8c0c5d4de45`; focused-test SHA-256 `f4d55864f704fe1ffb39b097b1adb87209b94c6895f2acf34dcbe874b92fd751`; handoff SHA-256 `65637edd64ae125e1cb53b24c1477e46b3ab2aff2c454850f15c6efcd7f47cc3`.
- R10 finding source: commit `dd54d749992e54cbb1c092d9d1ba755f1fe3a492`, FAIL P0=0/P1=1/P2=0; report SHA-256 `14bbe508dc1ce869fcf659dcd1c72222aecf17cc3a70a33e68455d2676d2736c`; handoff SHA-256 `9f1bbebb6df2680e6bf19c72c6dfdb52875a40981366b453d63039f57dca1e3a`.
- R11 source manifest: `orchestration/evidence_snapshots/R11_E08_review/SOURCE.sha256`.

## Review tasks and limits

1. Verify exact parent, clean worktree, exactly three E08 changed paths, all frozen source entries, output hashes, and the builder's recorded single focused test result. Do not infer more than the recorded/tested evidence.
2. Run exactly once the only independently authorized command: `python3 -m unittest discover -s tests -p test_p2_resource_snapshot_contract.py`. Run no other tests, syntax checks, or dry plans.
3. Statically verify the parser's helper is used on the pilot path before `resource_gates_verified` is restored, and enforces the complete aware-UTC ordering `pre_stamp <= started_at <= ended_at <= post_stamp`.
4. Confirm tests reject both an inverted CLI interval and a post snapshot before CLI start even when it is later than the reversed end; confirm the valid ordering and existing content-gate cases remain covered.
5. Confirm E07 snapshot-content validation, timeout identity, attempted denominator, failure scoring, host-rehearsal scope, point-in-time-only claim, and unrelated parser gates remain intact.

Add only `reviews/E07_timestamp_ordering_independent_review.md` and `orchestration/handoffs/R11_E08_review_handoff.md` on the reviewer branch. Report PASS/FAIL and P0/P1/P2 findings, exact hashes, clean-tree evidence, independent test result, and claim limits. Commit must directly parent exact E08 target.

No board/SSH, runtime/inference/benchmark, answer/annotation access, reboot, bitstream, GitHub activity, broader tests, syntax checks, or code execution beyond the single specified unit-test command. Do not integrate unless R11 returns exact-target PASS. P2-7 and external execution gates remain open; P3 stays `NO_GO_NOW`.
