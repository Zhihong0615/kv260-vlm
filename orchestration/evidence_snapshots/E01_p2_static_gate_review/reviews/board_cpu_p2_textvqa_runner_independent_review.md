---
review_mode: independent_static
reviewer_role: independent_reviewer
review_date_utc: 2026-09-23
runner_sha256: 2b6e38daa0f1cc1b720072dd3872bdfb3f4fa1c4a7b0d36c0baab0c6567f389f
preflight_sha256: c2a1b0a1ece4a0ae47d6253051c417c5ad009d07a42fea70efb49d4d112c3f1a
tests_sha256: 13a822c1d8694bdf4bb3faf54ef7e94f1b3d58de1e30298929ea44250010cb58
P0: 0
P1: 0
P2: 4
---

# Independent static review: P2 CPU TextVQA runner and preflight

## Scope and disposition

Independently recomputed the runner, preflight, and focused-test SHA-256 values in the frontmatter; all match the requested subjects. Reviewed those exact sources, including the embedded remote worker and read-only status program. I also inspected the adapter’s completion-manifest and host-copy-receipt checks to verify the runner handoff. No tests, SSH, or board commands were run.

No P0/P1 defect was found in the reviewed paths. The runner remains fail-closed for the key prelaunch checks: local planning is the default; `--execute` requires one qid, an explicit owner-window flag, synthetic ALPHA evidence, and hash-bound reviews; static gates precede SSH; a read-only host preflight precedes board input staging; and the remote worker repeats the resource check immediately before spawning the CPU-only command. Jupyter must be `active` with return code 0; both `apt-daily.service` and `apt-daily-upgrade.service` must be `inactive` with return code 3. Timeout/unknown states block at both gates. The board worker holds a nonblocking `flock` for its run and releases it in `finally`.

The board completion manifest and host-copy receipt are integrated: after `rsync`, the host verifies the completion manifest and every copied file, writes a receipt bound to the completion JSON digest and exact file list, and passes it to the adapter, which validates both before scoring. The current result is suitable for a carefully supervised pilot once the execution prerequisites and owner window are independently satisfied. The P2 findings below concern recoverability and the limits of what the gates prove.

## P2 findings

### P2-1 — A host timeout during the remote worker call retains hashes, not partial output

At `scripts/run_board_cpu_p2_textvqa.py:933-937`, the `TimeoutExpired` branch hashes any captured SSH stdout/stderr but does not write those bytes to `worker.stdout` and `worker.stderr`. The caller correctly records `REMOTE_STATE_UNKNOWN` and stops later qids, but it skips the read-only remote status check used on the normal return path. If the board worker completed while the host-side SSH wait expired, the locally captured final JSON or diagnostics are not available for review, and no completion-manifest copy is attempted. The qid raw directory is append-only, so a normal retry cannot reuse it.

Preserve captured bytes as well as their digests. Provide a recovery path that first checks the remote lock/process/completion state and either retrieves the verified board evidence or leaves the attempt explicitly unresolved; do not infer non-start from a transport timeout. The current status classification is conservative, so this is a recovery/evidence gap rather than a false success.

### P2-2 — The owner-window flag is an operator assertion, not a verified reservation

The execution gate requires `--owner-window-confirmed`, but `--owner-window-ref` is optional (`run_board_cpu_p2_textvqa.py:715-720, 821-823`). The record captures the local login and time, not a verifiable reservation or board-wide owner identity. The remote `.cpu_p2_runner.lock` serializes users of this runner only; it does not reserve the board against other tools or independently establish that the confirmed owner window is active. The dry plan correctly shows this as an explicit input, and the flock still prevents concurrent instances of this worker.

Treat the flag as self-attestation in provenance and require a coordination reference or other external owner confirmation at execution time if the study’s board policy requires an exclusive window. Do not describe the flock alone as global board ownership.

### P2-3 — Upgrade-service checks are snapshots, not a lease for the full inference interval

Both the host preflight and the remote pre-spawn check reject active or unknown apt service states. The worker also gathers a post-run snapshot. However, a systemd timer or another owner may activate package work after the final pre-spawn check and during the CLI’s up-to-300-second window. The post-run snapshot can detect that condition only after resource contention has occurred; the runner lock does not control systemd or unrelated owners.

This is a residual time-of-check/time-of-use boundary, not a missing service-state gate. Keep the evidence described as point-in-time preflight/postflight, and use an externally coordinated quiet window if the requirement is that package work cannot overlap the inference interval.

### P2-4 — Focused tests do not exercise the orchestration’s critical failure paths

`tests/test_board_textvqa_contract.py` checks fail-closed systemd helper cases, completion/receipt binding and mutation, a helper’s partial transport-output persistence, and syntax/hash pinning for embedded programs. It does not execute or mock the full host preflight schema-to-gate flow; run the embedded worker’s resource and lock gates; or test ordered-stop behavior across preflight, lock contention, worker timeout, status timeout, and incomplete-copy cases. In particular, the helper test for partial output does not exercise the remote-worker timeout branch described in P2-1.

Add local tests around extracted orchestration helpers or mocked subprocess boundaries so these safety and evidence guarantees are checked without board access. The present tests provide useful parser-contract coverage but do not demonstrate the complete runner failure protocol.

## Evidence and boundary notes

- `scripts/board_cpu_preflight_remote.py:17-32` bounds each `systemctl is-active` call to five seconds and represents timeout/OS errors as `UNKNOWN`. Its output records all three service states. The invoking SSH call is also bounded.
- `scripts/run_board_cpu_p2_textvqa.py:84-95, 249-268` applies the same exact Jupyter/apt state and return-code policy in the host and embedded board gate; missing or transitional states fail closed.
- Resource sequencing is conservative: host memory/CMA/swap/disk/load/process and systemd gates run before staging; the board worker repeats resource/systemd checks before `Popen`; postflight gates set the stop-after-current-request condition. Board directory/lock creation occurs inside the worker before its final pre-spawn gate, after the host preflight has passed.
- Status and copy timeout handlers now preserve partial captured bytes, record an unknown/incomplete phase, and stop later qids. The gap in P2-1 is specifically the separate `REMOTE_WORKER` invocation timeout branch.
- Normal board completion is not accepted on stdout alone: remote status requires an unlocked runner, no owned/unreadable CLI process, and a valid completion marker; then the host verifies the strict manifest and copy receipt before adapter scoring. These hashes and receipts establish consistency of the copied files, not a cryptographic signature from the board.
- The dry-plan path has no board connection, always reports `execution_ready: false`, lists missing/stale alpha/review/owner inputs, and includes the expected preflight hash. The execute path checks static prerequisites before the first SSH call.

## Review counts

P0: **0** — no demonstrated unsafe board mutation, false-positive result acceptance, or secret disclosure in the reviewed paths.

P1: **0** — no current blocking schema mismatch or unbounded preflight command found.

P2: **4** — partial worker-timeout evidence/recovery, self-attested owner-window boundary, point-in-time upgrade gate, and missing orchestration-level failure tests.
