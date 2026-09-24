# E11 Handoff — Remote Process Sample Gate

## Target and source verification

- Branch: `agent/E11-remote-process-gate`
- Required base and commit parent: `9485eef4e975f7082d98d651bb156effd5221505`
- Initial worktree was clean; no source edit was made until branch, base, and frozen source checks passed.
- Frozen manifest: `orchestration/evidence_snapshots/E11_remote_process_gate/SOURCE.sha256`
- Frozen manifest SHA-256: `297aeff30994efaa6093a2d6012687b2f74edd910a0dda9e90ef8c32a90dc1fc`
- Every manifest entry passed `sha256sum -c`; the pinned runner subject before edits was `8f07232ef2bcfe78e3f5cd331273796de6db87402a8e502ca4980dc89682c577`.
- Task brief SHA-256: `9a7f50937701cd533b6bc28258b95a88a3cb47dd6dd4354e8e0d987e73e029b4`.

## Change

The embedded worker now uses a two-sample procfs CPU sampler that records read and parse errors, detects PID-set changes and process identity changes including start-time changes, and marks invalid counters, clock tick rates, and elapsed intervals as `PROCESS_STATE_UNKNOWN`. The final `rich_snapshot()` feeds this state and the per-process measurements to the production `gate()`. A non-empty gate result blocks the existing prelaunch path before `Popen`.

The focused test extracts and executes the runner’s literal embedded `REMOTE_WORKER` definitions. It supplies only temporary synthetic procfs trees, a deterministic clock and sleeper, and synthetic non-process resource data. It covers unreadable and malformed entries, appearing and disappearing PIDs, PID reuse, invalid CPU deltas and intervals, a stable below-threshold sample, and a busy-process sample. It does not read host `/proc`.

Existing thresholds and service, timeout, and wait limits were not changed. R15 P2 findings remain out of scope: non-permission cleanup/status read errors, one CLI across repeated owner-window references, and durable later non-start conflicts. This change does not authorize P3 or board execution.

## Test record

One authorized invocation; no failures and no second invocation:

```text
$ python3 -m unittest discover -s tests -p test_p2_remote_process_gate.py
......
----------------------------------------------------------------------
Ran 6 tests in 0.005s

OK
```

## Changed paths and SHA-256

- `scripts/run_board_cpu_p2_textvqa.py` — `0ff88fd1780fa52ae5a30a6a47fe89827887d4360e20a14e9dc3269e6fb6ba92`
- `tests/test_p2_remote_process_gate.py` — `7093a6680444f17aaf72b65977fa83d698a36582a5b7eb7c45276ddd892c3aea`
- `orchestration/handoffs/E11_remote_process_gate_handoff.md` — digest is reported in the builder completion message after this file is frozen; including a file’s own final SHA-256 inside itself would change that digest.

## Evidence limits

Evidence is limited to the single focused host-side unittest run over synthetic procfs fixtures. No hardware, SSH, network, runner, remote worker, inference, benchmark, or board-resource behavior was exercised. Transient process creation or exit during either sample intentionally makes the sample unknown and blocks prelaunch.
