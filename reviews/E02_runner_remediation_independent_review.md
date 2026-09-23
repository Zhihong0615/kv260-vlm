# E02 runner remediation — independent review

- **review_mode:** independent static source review
- **reviewer_role:** independent reviewer
- **Verdict:** PASS for integration of the four scoped source remediations
- **Findings:** P0: 0 · P1: 0 · P2: 2 (conditional input-validation/auditability residuals)
- **Frozen target:** `aad962435278e470d36b3a0f247e9fb5624cf0f1`
- **Required direct parent:** `7385c0b10033244b3e203a3b152ca63720207222`
- **Reviewer branch:** `agent/R04-E02-review`

## Identity and frozen evidence

The reviewer worktree was clean at the frozen target before this review, and the target commit directly parents the required base. The target diff contains only the two runner/preflight sources and the E02 handoff. The E02 target worktree was also verified clean at the same commit and parent.

The R04 activation is `orchestration/review_activations/R04.md`, SHA-256 `03569ce789f19b4d974cd4acb5116fb1b99515d9666e7dc0d12941c1e3f88d41`. The task brief SHA-256 is `1ec6f05f4c86c380a9daa2b23eb1cc04dae5d9fae0a288e04d14655ab3968159`. The five-entry R04 frozen manifest SHA-256 is `5ab201c5aabdd9d1024d2064ed2a0b44e0b7ad31cd1dee45176c5a9218a50d90`; all five entries passed verification. The nine entries in the E01 snapshot manifest all passed verification; that manifest SHA-256 is `0a021eb8c8abd55cbf95442e83667284bc672e99831a3fd159e8610de6a9deed`.

| Deliverable | Frozen E01 input SHA-256 | E02 target SHA-256 |
|---|---|---|
| `scripts/board_cpu_preflight_remote.py` | `fad954fbef94946d12de9a22d67e82a15951a7d715a02201a7c92d968192aa02` | `2366b7f5291fbb51e859e943a7453baa033cf41ed64668017689d97ddc9db959` |
| `scripts/run_board_cpu_p2_textvqa.py` | `38e6d81b04fbf78c5ff398940e1bc934f224a621595311145e5b1a074fcce526` | `8e3bed3ce9917db2593df88405937e28d9fb32426a4f19b1df6c3807f32b9dbd` |
| `orchestration/handoffs/E02_runner_remediation_handoff.md` | — | `3da825485a0d3f25616b63a48221af5b76821b364507c6fc4e46590b40c467bc` |

The runner pins the exact updated preflight digest at `scripts/run_board_cpu_p2_textvqa.py:41`. The E02 activation digest is `61dcb508521b068e933b13a2cebf90e895619f1731b1391359052cecdab93aab`; the frozen E02 task brief digest is `5765f81c890bde5865bf04e8a95ef2710a5df3b905caa54bbd388aacfb09edcf`.

## Scoped behavior review

1. **Per-PID CPU gate and pre-staging order — satisfied.** The remote preflight takes two process snapshots around a fixed two-second wait and records each stat read’s boundaries (`scripts/board_cpu_preflight_remote.py:133-177`). It rejects read errors, process-set changes, PID identity changes, negative counter deltas, invalid clock rates, and nonpositive per-PID intervals. For each PID it divides by the gap from the first stat read’s end to the second read’s start, a lower bound on the counter interval and therefore a conservative CPU-use estimate (`scripts/board_cpu_preflight_remote.py:155-173`). The host validates sample state, errors, PID uniqueness, counters, finite intervals and CPU values, and the 0.25-core threshold (`scripts/run_board_cpu_p2_textvqa.py:121-184`). The read-only preflight and its gate precede remote input-directory creation and image rsync (`scripts/run_board_cpu_p2_textvqa.py:990-1034`, then `:1036-1061`).

2. **Board marker provenance — satisfied.** The board worker reads marker presence from its own environment immediately before removing the variable from the child environment; it writes the observation and removal fact into `command.json` (`scripts/run_board_cpu_p2_textvqa.py:586-596`). `result.json` records the observed marker flag and command hash (`:613-625`), and the completion manifest covers the run files (`:633-638`). Host environment state is not substituted for board provenance.

3. **Timeout recovery — satisfied.** Timeout partial stdout/stderr bytes are persisted and hashed (`scripts/run_board_cpu_p2_textvqa.py:72-83`, `:1076-1086`). After the timeout, the host issues at most one status request with a 45-second bound; failure, malformed output, or incomplete state is recorded as `REMOTE_STATE_UNKNOWN` and stops later work (`:1108-1138`). The status source checks the exact run ID, run directory, free runner lock, completion manifest hashes, matching CLI processes, and unreadable processes (`:749-792`). Only a complete state enters the bounded copy and host-side exact manifest/file size/hash verification path (`:1142-1190`; frozen E01 adapter `orchestration/evidence_snapshots/E01_p2_static_gate_review/scripts/parse_board_textvqa_pilot.py:153-192`). Recovery does not relaunch the CLI. The handoff accurately retains timeout executable identity as unresolved P2-6.

4. **Owner-window reference — satisfied.** Execution requires a qid, confirmation flag, nonempty reference after whitespace trimming, and ALPHA proof (`scripts/run_board_cpu_p2_textvqa.py:855-870`). The reference is retained as supplied in the dry plan and execution provenance (`:903-927`, `:958-977`). The handoff correctly describes it as an operator assertion; code does not validate an external reservation.

## Finding

### P2-1 — Non-finite load value can bypass the load threshold if the snapshot is corrupted or substituted

- **Path and lines:** `scripts/run_board_cpu_p2_textvqa.py:115-120` and `:452-453`.
- **Condition:** Both host and board gates convert the first load token to `float` and reject only when it compares greater than the configured maximum. A token such as `nan` (or `-inf`) parses successfully and compares false to `1.5`, so the load gate does not add a blocking reason. Ordinary malformed tokens that raise `ValueError` are blocked by the host parser; the board worker’s direct parser may abort into its error path.
- **Consequence:** If the JSON snapshot’s `loadavg` text is corrupted or substituted with a non-finite value while other gates pass, the load check fails open.
- **Likelihood and scope:** Both snapshot producers read `/proc/loadavg` directly (`scripts/board_cpu_preflight_remote.py:231`; worker snapshot `scripts/run_board_cpu_p2_textvqa.py:435-443`). This makes `nan` unlike a normal kernel-produced value in this flow. The finding is conditional parser hardening, not evidence of a current live-board condition and not one of the four E02 remediations.
- **Bounded fix:** Require the parsed load value to be finite and nonnegative at both gates; record an unknown/invalid-load gate reason and stop before staging or CLI launch otherwise.
- **Disposition:** P2 residual; it does not block integration of the four scoped changes. The board run remains subject to its independent readiness gates.

### P2-2 — Malformed CPU row can escape the structured preflight block path

- **Path and lines:** `scripts/run_board_cpu_p2_textvqa.py:149-184` and `:1025-1034`.
- **Condition:** If `process_cpu_rows` contains a dict missing `pid` or `cpu_cores` while the separate sample-state fields still validate, the schema-validation branch appends `PROCESS_STATE_UNKNOWN` at lines 149-170. The following threshold clause independently checks only that the collection contains dicts before indexing `row["pid"]` and `row["cpu_cores"]` at lines 180-184. That can raise `KeyError` before `main` writes the structured preflight result.
- **Consequence:** This is fail-closed for board safety: the exception occurs before image directory creation and staging at lines 1036 onward. It bypasses the intended `PREFLIGHT_BLOCKED` outcome and later nonstart records, however, and leaves the append-only local raw directory occupied, so a normal retry is refused by `checked_raw_path`.
- **Bounded fix:** Return the accumulated unknown-state gate reason immediately after CPU-row schema failure, or guard the threshold loop with complete row-key/type validation. Convert any such validation failure into the normal recorded `PREFLIGHT_BLOCKED` path.
- **Disposition:** Conditional P2 for operator auditability/recovery, not a fail-open safety defect and not a blocker to integration of the four scoped remediations.

## Handoff fidelity and limits

The E02 handoff accurately describes all four scoped changes and their hashes. It correctly keeps P2-5 continuous resource monitoring, P2-6 timeout executable identity, and P2-7 orchestration regression tests unresolved. The external ALPHA proof, live resource state and owner-window reservation also remain unverified here. This review does not establish board readiness or change P3 `NO_GO_NOW`.

No tests, syntax checks, dry plans, benchmarks, target/runtime execution, SSH, board access, inference, reboot, bitstream action, answer/annotation reads, or GitHub activity were performed. This is static review of the frozen source and handoff only.
