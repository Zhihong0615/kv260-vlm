# E09 runner orchestration regressions handoff

## Build identity

- Base and required direct parent: E08 target `215d3c1acb6a3091a84f53cfdacb644d90116871`.
- Branch/worktree: `agent/E09-runner-orchestration-regressions` / `/home/zhiro/research/kv260-vlm-workers/E09-runner-orchestration-regressions`.
- E09 source manifest SHA-256: `eb17dec6cf5758a55e9fd6ddaec4e34748e4066175cc8864553ed07a4fb18488`; all 23 frozen inputs passed before edits.
- E01 runner-review evidence SHA-256: `8cafc732a0a9af26ca8da9e4097f1192b5b324661632904d93c27961621a6e3e`; overall E01 review SHA-256: `569712d404eb4cc2d18aa10759d37a2928cd1b03df2fcf493fc9ab4e0330ef1f`.
- Changed paths: `scripts/run_board_cpu_p2_textvqa.py`, `scripts/parse_board_textvqa_pilot.py`, `tests/test_p2_runner_orchestration.py`, and this handoff only.
- The target commit directly parents the exact base above. Its commit ID and this handoff's own SHA-256 are reported in the builder completion message because they cannot be embedded in their own tracked content.

## Orchestration contract

- `main()` now routes each requested qid through the production-used `run_host_orchestration` state machine. `HostOrchestrationOps` injects the previous-case gate, preflight, image staging, worker launch, one status query, copy/manifest/hash verification, scoring, and record callbacks. Production callbacks retain the existing SSH, subprocess, rsync, provenance, and parser operations; tests supply local fakes.
- A worker timeout never relaunches the worker. The single status response must identify the current run and report a present run directory, free runner lock, valid completion marker, and empty CLI/unreadable process lists before copy proceeds.
- The exact worker response `{"status":"REMOTE_LOCK_BUSY","cli_started":false}` records the current qid with parser-valid `RUNNER_LOCK_BUSY`, `cli_started: false`, and no score/attempt. Later qids stop as unresolved.
- Transport/nonzero/malformed/incomplete status and incomplete copy remain unresolved and stop later qids. Copy failure does not call scoring; copy callback preserves available partial output. A failed earlier qid records the requested and later qids as non-starts before begin, preflight, staging, worker, status, copy, or scoring can run.
- Resource thresholds, worker timeout values, completion/receipt hashing, score rules, image parsing, and the E08 point-in-time contract were not intentionally changed.

## Verification and output hashes

- The only command run: `python3 -m unittest discover -s tests -p test_p2_runner_orchestration.py`
- Result: `Ran 5 tests ... OK`. Subtests cover timeout recovery/no retry, exact current run ID and status gates, lock-busy non-start schema, status transport/nonzero/malformed/incomplete cases, raw-copy timeout/nonzero/manifest/hash failures, and ordered stop.
- Runner SHA-256: `02d2c794c292bdb350803f9d028866e8b256e5846581e789b42928851f1a9cdf`.
- Parser SHA-256: `0e28f81cc26ec47cfe2488c680623c74accd1bef92d9a4f3a31ae2fa73ba3b8d`.
- Focused test SHA-256: `6e91308f475e09bf4e84dafb8250d2ae27b3c30d2bc32243639e988667c78974`.
- Handoff SHA-256: reported in the builder completion message.

## Limits and remaining gates

Tests use only local fake operations, synthetic records, and temporary directories; no user images, labels, annotations, board, SSH, network, inference, runtime, benchmark, or GitHub activity was used. The fake suite verifies the injected host state machine, not live board or parser execution. Exact-target independent R12 review is required before integration. P2-5 is closed only at source-parser level; runtime parser success and external execution gates remain unverified. P3 stays `NO_GO_NOW`.
