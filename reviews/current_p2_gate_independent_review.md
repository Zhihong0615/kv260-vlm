---
review_mode: independent_static
reviewer_role: independent_reviewer
review_date_utc: 2026-09-24
input_snapshot_commit: 880096cc50f4d37692012136ef7d204856df40ca
parser_sha256: cdaa479d61a946e9bd243398389452e3337e2714b696ac73f1a380bae05ad032
runner_sha256: 38e6d81b04fbf78c5ff398940e1bc934f224a621595311145e5b1a074fcce526
preflight_sha256: fad954fbef94946d12de9a22d67e82a15951a7d715a02201a7c92d968192aa02
tests_sha256: 8d89eed8cd92c3041a4b1170dad8b13f5e4c0b07fce7388e428d0fab3a84e3a9
P0: 0
P1: 0
P2: 7
---

# Current P2 TextVQA gate: independent static review

## Scope and result

Reviewed only the frozen files under `orchestration/evidence_snapshots/E01_p2_static_gate_review/` from input snapshot commit `880096cc50f4d37692012136ef7d204856df40ca`. Before inspection, verified the coordinator at `8f650a4da72f81aa1287aa349969bf38aff841fc`, the clean reviewer worktree at `agent/E01-p2-gate-review` / `d5ab097050a74bf0eeec35a6d3b635e238ea25e9`, and all nine entries in the frozen `SOURCE.sha256`; every entry passed. Recomputed the four source hashes above from the snapshot. The two included earlier reviews were treated as context only.

No P0 or P1 defect was found in the parser's attempted-state denominator, strict argv and input binding, image-event pairing, or the runner's last pre-spawn resource check, board lock, subprocess cleanup, completion manifest, and host copy receipt. The parser is deliberately conservative for incomplete evidence: a missing/contradictory attempt record stays unknown, while a confirmed start with failed evidence remains attempted and scores an empty answer. The runner stops later qids on failed or unresolved cases.

Seven P2 findings remain. They concern pre-staging occupancy coverage, one inaccurate provenance field, a worker-transport recovery gap, owner-window evidence, point-in-time resource checks, PATH-based timeout resolution, and missing orchestration-level tests. They do not demonstrate false acceptance of a completed scored case or an unbounded child process under the reviewed worker's own 330-second wait and cleanup path. This is a source review, not dynamic proof of board execution or configured external evidence.

## Findings

### P2-1 — Host preflight does not apply the per-process CPU gate before staging

**Evidence:** `scripts/board_cpu_preflight_remote.py:90-119` records selected process names but does not sample process CPU deltas. `scripts/run_board_cpu_p2_textvqa.py:98-137` gates host-preflight memory, load, systemd, package state, and a fixed busy-name set, but not CPU use by arbitrary processes. The host flow stages the image after that gate at `scripts/run_board_cpu_p2_textvqa.py:924-995`. The remote worker does perform a two-second process-tick gate later at `scripts/run_board_cpu_p2_textvqa.py:391-421`, before `Popen` at lines 504-539.

**Condition and consequence:** A process using at least 0.25 core can be present while load1 remains at or below 1.5 and its `comm` is outside the fixed busy-name set. The first gate can then pass and the runner can create the board input directory and transfer a JPEG while the board is busy. The second gate should block CLI launch if that process is still busy then, so this is a staging-policy gap rather than evidence that inference starts through the later gate.

**Bounded fix:** Apply the same two-second per-process CPU threshold, with malformed or unobservable state failing closed, in the read-only preflight before image staging. Keep the existing fresh remote pre-spawn check as a second gate.

### P2-2 — `marker_was_present_before_removal` describes the host environment, not the board child environment

**Evidence:** `scripts/run_board_cpu_p2_textvqa.py:890-905` samples `MTMD_TEST_RESPONSE_MARKER` from the host process and puts that boolean in remote-worker config. The remote worker writes it as `command.json` metadata at lines 511-522, but creates the CLI environment from the board worker's own `os.environ` and removes the marker at lines 534-538.

**Condition and consequence:** If the host and board worker environments differ, the record's `marker_was_present_before_removal` value is wrong for the environment from which the CLI marker was removed. The actual removal still occurs, so the reviewed code does not establish marker contamination; it does make the recorded board-side environment provenance unreliable.

**Bounded fix:** Sample the marker presence inside the remote worker immediately before removing it from the CLI environment, then write that observed boolean into the board command record.

### P2-3 — A host timeout during the remote worker call drops captured output and skips recovery

**Evidence:** The `TimeoutExpired` branch at `scripts/run_board_cpu_p2_textvqa.py:1010-1014` stores digests of captured SSH output but does not persist the captured bytes. The subsequent branch at lines 1023-1026 marks the run unresolved and stops later qids without invoking the remote status check at lines 1034-1055 or attempting verified copy recovery.

**Condition and consequence:** If the board worker completes near the host wait timeout, its final status and diagnostics may be present in the exception's partial stdout/stderr but are lost locally; the immutable raw directory is left unresolved even if remote completion evidence exists. The code fails closed and stops later qids, so this is evidence recovery, not a false-success path.

**Bounded fix:** Persist partial stdout/stderr bytes along with their digests. On worker-transport timeout, make one bounded read-only remote status check and, only for a valid completed manifest, use the existing strict copy verification path; otherwise retain `REMOTE_STATE_UNKNOWN` and do not retry the run ID.

### P2-4 — The owner-window record is self-attested and the coordination reference is optional

**Evidence:** `scripts/run_board_cpu_p2_textvqa.py:797-802` requires `--owner-window-confirmed` but leaves `--owner-window-ref` optional. Lines 903-905 record the local login, timestamp, and supplied reference without requiring or validating a reference. The remote `flock` at lines 450-455 serializes this runner, not other board workloads.

**Condition and consequence:** An invocation with the flag and no reference passes this part of execution gating. The evidence therefore cannot establish an externally coordinated exclusive owner window or show that unrelated tools will stay off the board.

**Bounded fix:** If board policy requires an exclusive window, require and record a verifiable coordination reference or equivalent owner confirmation. Continue to describe `flock` as runner-local mutual exclusion only.

### P2-5 — Resource and service checks are snapshots, not protection throughout inference

**Evidence:** The remote worker takes the final pre-spawn snapshot at `scripts/run_board_cpu_p2_textvqa.py:504-507`, starts the child at lines 534-539, and checks again after child exit at lines 541-568. There is no in-run resource monitor. The frozen protocol also states that postflight deterioration can only stop later requests (`experiments/derived/kv260_cpu_p2_textvqa_pilot_protocol_draft.md:38-41`).

**Condition and consequence:** A service or competing workload may start after the pre-spawn sample during the up-to-300-second CLI interval. The postflight sample can record the change and stop later requests, but cannot prevent contention during the current request.

**Bounded fix:** If the gate requires no overlap throughout inference, freeze and review a bounded in-run monitor with explicit sampling, stop thresholds, and cleanup behavior. Otherwise retain the point-in-time wording and do not describe pre/post snapshots as a lease or continuous guarantee.

### P2-6 — The timeout executable is selected through `PATH` and is not identity-bound

**Evidence:** `expected_argv()` records the bare executable name `timeout` at `scripts/run_board_cpu_p2_textvqa.py:780-792`; the parser accepts that exact argv at `scripts/parse_board_textvqa_pilot.py:369-381`. The board worker launches it with `Popen(a, ...)` and inherits the board environment at `scripts/run_board_cpu_p2_textvqa.py:534-539`; neither the selected executable path nor its digest is recorded. The outer remote watchdog also invokes bare `timeout` at runner lines 997-1001.

**Condition and consequence:** If the board `PATH` resolves `timeout` to a non-GNU or unexpected executable, the argv record still passes parser validation while the intended 300-second wrapper semantics are not established. The worker has a separate 330-second wait/cleanup fallback and an outer 540-second watchdog, which bound the reviewed orchestration path, but those are not proof that the configured wrapper's exact limit was applied.

**Bounded fix:** Pin both timeout invocations to the expected absolute executable, verify or attest its identity, and record the resolved path/identity used by the worker. Keep parser validation aligned with that pinned command.

### P2-7 — Focused tests cover helpers, not end-to-end stop and recovery paths

**Evidence:** `tests/test_board_textvqa_contract.py:43-167` covers parser helpers and completion/receipt mutations; lines 169-281 exercise selected gate helpers; lines 283-290 test `persist_transport_failure()` directly; lines 292-297 compile embedded programs and compare a hash. No test drives the host runner through remote-worker timeout, lock contention, status failure, incomplete copy, or ordered stop behavior. In particular, the helper test does not exercise the timeout branch at runner lines 1010-1026.

**Condition and consequence:** These tests can pass while the runner's cross-phase error handling or evidence persistence is wrong. Static inspection supports the intended fail-closed flow but does not provide dynamic regression evidence for it.

**Bounded fix:** Extract the host orchestration decisions behind injectable subprocess boundaries and add local tests for the listed outcomes, preserving the no-board/no-inference constraint.

## Runner review-gate disposition

This report contains both current parser and runner subject hashes, the required `review_mode` and `reviewer_role`, and P0=0/P1=0. Its content therefore meets the runner's mechanical review predicate for either subject (`scripts/run_board_cpu_p2_textvqa.py:217-232`). The two prior snapshot reviews do not: the adapter review binds parser SHA `06fa1518ed240d75d3c2ad90f9c41ca545f2b041182957130219c1293a44a752`, and the runner review binds runner SHA `2b6e38daa0f1cc1b720072dd3872bdfb3f4fa1c4a7b0d36c0baab0c6567f389f` and preflight SHA `c2a1b0a1ece4a0ae47d6253051c417c5ad009d07a42fea70efb49d4d112c3f1a`; all are stale relative to this snapshot.

The source-level review predicate is satisfied by this review's counts and current hashes, but the current runner reads only its configured `ADAPTER_REVIEW` and `RUNNER_REVIEW` paths (`scripts/run_board_cpu_p2_textvqa.py:32-33, 235-263`). This deliverable is at a different path, so the current configured gate remains closed until the current-hash reviews are placed at the paths the runner actually reads. This report does not establish ALPHA proof, live resource gates, an owner window, or board execution readiness.

## Review counts

P0: **0** — no demonstrated unsafe board mutation, label transfer, false-positive completed score, or secret disclosure in the reviewed scope.

P1: **0** — no demonstrated path that bypasses the remote pre-spawn resource gate or turns missing/contradictory attempt evidence into a successful score.

P2: **7** — the seven bounded findings above.
