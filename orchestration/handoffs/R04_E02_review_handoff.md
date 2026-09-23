# R04 E02 runner remediation review handoff

- **review_mode:** independent static source review
- **reviewer_role:** independent reviewer
- **Verdict:** PASS for integration of the four scoped E02 source remediations
- **Findings:** P0: 0 · P1: 0 · P2: 2 conditional residuals
- **Target:** `aad962435278e470d36b3a0f247e9fb5624cf0f1`
- **Required parent:** `7385c0b10033244b3e203a3b152ca63720207222`
- **Reviewer branch:** `agent/R04-E02-review`; review commit directly parents the target

## Verification

The R04 activation digest is `03569ce789f19b4d974cd4acb5116fb1b99515d9666e7dc0d12941c1e3f88d41`; its brief digest is `1ec6f05f4c86c380a9daa2b23eb1cc04dae5d9fae0a288e04d14655ab3968159`. R04 frozen manifest digest `5ab201c5aabdd9d1024d2064ed2a0b44e0b7ad31cd1dee45176c5a9218a50d90`: all 5 entries verified. E01 snapshot manifest digest `0a021eb8c8abd55cbf95442e83667284bc672e99831a3fd159e8610de6a9deed`: all 9 entries verified.

| File | Frozen E01 input SHA-256 | E02 output SHA-256 |
|---|---|---|
| `scripts/board_cpu_preflight_remote.py` | `fad954fbef94946d12de9a22d67e82a15951a7d715a02201a7c92d968192aa02` | `2366b7f5291fbb51e859e943a7453baa033cf41ed64668017689d97ddc9db959` |
| `scripts/run_board_cpu_p2_textvqa.py` | `38e6d81b04fbf78c5ff398940e1bc934f224a621595311145e5b1a074fcce526` | `8e3bed3ce9917db2593df88405937e28d9fb32426a4f19b1df6c3807f32b9dbd` |
| `orchestration/handoffs/E02_runner_remediation_handoff.md` | — | `3da825485a0d3f25616b63a48221af5b76821b364507c6fc4e46590b40c467bc` |

The updated preflight digest is pinned at runner line 41. The target diff contains the expected two source files plus handoff; exact target, parent, clean state, all target hashes and the direct parent requirement were checked.

## Review conclusion

The pre-staging per-PID CPU gate uses a conservative per-process interval and blocks malformed/racy process samples. Board marker provenance is captured before removal and bound into result evidence. Worker timeout partial output is persisted; recovery makes at most one bounded status request and only accepts the strict complete-manifest/copy/hash path, otherwise leaves `REMOTE_STATE_UNKNOWN` without rerunning. Execution requires and records the exact nonempty owner-window reference.

**P2-1 (conditional residual):** at `scripts/run_board_cpu_p2_textvqa.py:115-120,452-453`, `float("nan") > 1.5` is false. If a snapshot’s load token is corrupted or substituted as a non-finite value, the load gate fails open. The frozen producers read `/proc/loadavg` directly, so this is not a normal kernel-produced input in this flow. Bounded hardening is to require finite, nonnegative load values and fail closed otherwise. This conditional parser issue does not block integration of the four scoped remediations.

**P2-2 (conditional auditability/recovery residual):** at `scripts/run_board_cpu_p2_textvqa.py:149-184,1025-1034`, a malformed CPU-row dict can first add `PROCESS_STATE_UNKNOWN` and then trigger `KeyError` in the separate threshold loop when sample metadata is otherwise valid. This aborts before image staging, so it remains fail-closed for board safety, but bypasses the structured `PREFLIGHT_BLOCKED` record and leaves the append-only raw run directory occupied, preventing a normal retry. Return after schema failure or validate all row fields before threshold indexing, then record the normal blocked result. This does not block integration of the four scoped remediations.

E01 P2-5 (continuous resource monitoring), P2-6 (timeout executable identity), and P2-7 (orchestration regression tests) remain unresolved. The external ALPHA proof, current board resource state, and actual owner-window reservation were not established by this review. P3 remains `NO_GO_NOW`; this review makes no board-readiness claim.

No tests, syntax checks, dry plans, benchmarks, target/runtime execution, SSH, board access, inference, reboot, bitstream action, answer/annotation reads, or GitHub activity were performed. Review is limited to the frozen source snapshots and target handoff.
