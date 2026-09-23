# E02 runner remediation handoff

Worker branch: `agent/E02-runner-remediation`  
Worker base / direct parent: `7385c0b10033244b3e203a3b152ca63720207222`  
Frozen E01 input snapshot: `880096cc50f4d37692012136ef7d204856df40ca`  
Snapshot manifest SHA-256: `0a021eb8c8abd55cbf95442e83667284bc672e99831a3fd159e8610de6a9deed`

## Finding-to-change map

1. **Host preflight CPU sampling:** `board_cpu_preflight_remote.py` records two `/proc` process snapshots around a fixed 2-second wait, verifies process identity continuity, and reports per-process CPU cores from tick deltas. Each PID uses the gap from the end of its first `stat` read to the start of its second as a lower bound on the counter interval, giving a conservative CPU-use estimate without a traversal-wide denominator that could bias early PIDs low. The host gate validates the sample schema, process IDs, counters, per-PID interval and error state; it blocks on malformed or unobservable state and rejects any other process at or above 0.25 cores. The gate still runs before image-directory creation or image staging.
2. **Board marker provenance:** the board worker captures `MTMD_TEST_RESPONSE_MARKER` presence in its own environment immediately before removing it from the CLI environment. `command.json` records the observed presence and removal; `result.json` carries the observed flag and binds the command hash. Host environment state is not used as board provenance.
3. **Worker timeout recovery:** the host persists partial worker stdout/stderr bytes and their hashes on timeout, then makes at most one read-only remote status request with a 45-second bound. Recovery proceeds only for the exact run ID with a free runner lock, no owned or unreadable CLI process, and a valid completion manifest, followed by the existing manifest and copied-file hash verification. Any incomplete or contradictory status/copy state remains `REMOTE_STATE_UNKNOWN`; the run ID is not retried.
4. **Owner-window reference:** `--execute` now requires both `--owner-window-confirmed` and a non-empty `--owner-window-ref`. The exact supplied reference is retained in the dry plan and execution provenance. This records an operator assertion; source code does not verify an external reservation.

## Input and output hashes

| File | Frozen input SHA-256 | Worker output SHA-256 |
|---|---|---|
| `scripts/board_cpu_preflight_remote.py` | `fad954fbef94946d12de9a22d67e82a15951a7d715a02201a7c92d968192aa02` | `2366b7f5291fbb51e859e943a7453baa033cf41ed64668017689d97ddc9db959` |
| `scripts/run_board_cpu_p2_textvqa.py` | `38e6d81b04fbf78c5ff398940e1bc934f224a621595311145e5b1a074fcce526` | `8e3bed3ce9917db2593df88405937e28d9fb32426a4f19b1df6c3807f32b9dbd` |

The runner pins the updated preflight SHA-256 above. Only these two source files and this handoff are deliverables.

## Unresolved scope and execution boundary

P2-5 continuous resource monitoring, P2-6 timeout executable identity, and P2-7 orchestration regression tests remain unresolved. The fixed review-path issue, valid ALPHA proof, live board-resource checks, and an externally coordinated owner window also remain outstanding. No tests, syntax checks, dry plans, benchmarks, SSH, board access, inference, reboot, bitstream activity, or GitHub actions were performed. P3 remains `NO_GO_NOW`; this source-only proposal makes no board-readiness claim.
