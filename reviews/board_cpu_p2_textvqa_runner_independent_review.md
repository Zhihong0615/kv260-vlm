---
review_mode: independent_static
reviewer_role: independent_reviewer
runner_sha256: 8f07232ef2bcfe78e3f5cd331273796de6db87402a8e502ca4980dc89682c577
---

# Independent static review: current TextVQA runner

## Verdict and severity counts

**Exact-target verdict: BLOCKED.** This review covers runner SHA-256 `8f07232ef2bcfe78e3f5cd331273796de6db87402a8e502ca4980dc89682c577`. One P1 finding remains in the remote launch-boundary resource gate. The runner's own review gate requires zero P0 and P1 findings, so this source snapshot does not pass that gate.

P0: 0
P1: 1
P2: 3

## Scope and method

I verified the assigned branch `agent/R15-current-runner-review`, starting commit `ad51e2784fbbc0697232ed265e49d2e804f18b9d`, clean initial worktree, source-manifest SHA-256 `8f5b3ed06740ee2800f63536dd870196f71b4e8d15a49ad7cd94833b39df50ff`, and every file hash in that manifest before reviewing. The exact runner, parser, and pinned preflight hashes matched.

The review was source-only. I inspected the runner's static gates, orchestration branches, embedded worker, pinned preflight helper, and parser handoff. I did not execute or import code, run tests or a dry plan, inspect answer/annotation contents, or contact a board or network service.

## Findings

### P1 — Remote launch-boundary CPU gate can accept an incomplete process sample

**References:** `scripts/run_board_cpu_p2_textvqa.py:570-588, 649-661, 747-750, 799`

The worker's `proc_rows()` catches `OSError`, `ValueError`, `IndexError`, and `StopIteration` for each `/proc/<pid>` scan and simply continues. It does not return scan errors or mark the process state unknown. `rich_snapshot()` takes `before` and `after` maps around a two-second sleep but never compares their PID sets or process start identities. In `gate()`, CPU use is checked only for rows in `_rows_after` that also have a matching PID in `before`; a newly appearing PID has `old is None` and is skipped. A row lost to a read error is also absent without an error signal. The separate selected-process check only covers the worker's fixed `interesting` names.

The last such gate runs after input staging and the worker's artifact/CLI checks, immediately before the run directory and CLI launch are prepared (`747-750`, then `799`). A generic, otherwise-unlisted CPU-heavy process that starts during that sample interval can therefore be absent from the paired delta check and from `selected_processes`, while the gate returns no `BUSY_CPU` or `PROCESS_STATE_UNKNOWN` reason and the worker launches the VLM CLI. The pinned host preflight helper fails closed on process-set changes and scan errors, but it runs before staging; it does not close this later launch-boundary gap. This makes the configured per-process CPU gate unreliable at the point it is meant to protect.

### P2 — Cleanup/status scans treat some process-inspection errors as absence

**References:** `scripts/run_board_cpu_p2_textvqa.py:679-687, 967-974`

Both the worker's `owned_cli_processes()` and the remote status source report `PermissionError` as unreadable, but silently ignore other `OSError` values while reading `/proc/<pid>/cmdline`. If an owned CLI remains present and its command line read fails with a non-permission error, both scans can report no found or unreadable CLI. The worker may then set `remote_process_cleanup_verified`, and the status helper may set `state: COMPLETE`, allowing timeout recovery to proceed to evidence copy and parser handoff. Expected process-exit races can be treated separately; other read failures should remain unresolved rather than count as absence.

### P2 — “One fresh CLI per owner window” is not enforced across invocations

**References:** `scripts/run_board_cpu_p2_textvqa.py:1073-1088, 1119-1145, 1173-1175, 1202-1205`

The runner accepts and records a non-empty `--owner-window-ref`, and a single invocation has one qid and one CLI `Popen`. However, the dry-plan field `one_fresh_cli_per_owner_window: True` is not enforced across invocations: the reference is opaque metadata, is not checked for uniqueness, and prior-case assessment checks only parse/image evidence. Multiple sequential qid invocations can reuse the same reference and each launch one CLI. Treat the one-CLI-per-window claim as an external operator condition unless the runner adds durable cross-run enforcement.

### P2 — Later non-start recording conflicts are not persisted

**References:** `scripts/run_board_cpu_p2_textvqa.py:81-97, 99-116, 1189-1200, 1460-1464`

When an ordered-stop path tries to record a later qid but finds an existing partial raw directory, `record_nonstart()` catches the `ValueError` and appends a conflict only to the in-memory `outcome`. The phase record for a preflight/stage stop is written before the non-start loop; on prior-case failure/unresolved paths, `main()` prints only the returned `decision`, not `outcome`. The existing directory is correctly left untouched, but there is no durable per-run record that the later qid's non-start could not be written. Its attempt state remains unknown, which is conservative, but the ordered-stop reason/conflict is ambiguous in the raw evidence.

## Safeguards observed

- Execution first checks the frozen manifest, ALPHA proof, build attestation, pinned preflight source, parser review, runner review, owner-window inputs, and one selected qid. Prior cases are assessed before `begin()` and before SSH.
- One invocation constructs one qid-specific argv and contains one inference `Popen`; prior failure/unresolved assessment stops the selected qid and later qids. A parser failure or remote stop rule prevents later qids from starting.
- Host preflight failures, staging failures, worker timeouts, unknown status, and incomplete copies stop progression. After a worker timeout the host queries remote status; copying requires a successful status reply with matching run id, completion marker, free runner lock, and no reported CLI or unreadable process.
- The parser rechecks the exact board completion file set and hashes, the host copy receipt, execution provenance, command/input bindings, timeout identity, and image-processing evidence before scoring. Incomplete evidence remains unscorable or unknown.
- Host JSON records use exclusive creation and new raw run directories are required. Existing attempt records are not overwritten.

## Limitations

This is not evidence of current board resource state, board identity, actual remote file contents, a live owner authorization/window, successful timeout behavior on the board, or an inference/benchmark result. A caller-supplied owner-window reference records an assertion; it does not independently establish authorization. Findings are source-level and require no claims about whether the identified races occurred in a live run. No tests or runtime checks were performed.
