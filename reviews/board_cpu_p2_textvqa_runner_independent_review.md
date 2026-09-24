review_mode: independent_static
reviewer_role: independent_reviewer
target_commit: 9b34056ec27a54c2e7c1265d78b002715a4cca6d
required_direct_parent: dced7666bcb3c5f79efd2d983045bac35932d89b
runner_sha256: 418c72316a055d0260ba88ccf85e31dba98cc0e0256d499fefa96063aa82e694
test_sha256: 55b87f3afae7eab92f811209ecea5a5794699a615d048ed77238aa3f74a330c1
parser_context_sha256: 48c834d6b803eb6a06f4be39f287913c461701ec606956c66493fe7f10d7e209
activation_sha256: dd3222319af445b7d91ad647e0bac79bfa6563885710344c447325303e321977
source_manifest_sha256: a5d70126b315afe441f50c3b37b82a59bcc34c107e4e31e97cf6d1d673c5e0f3
verdict: PASS
P0: 0
P1: 0
P2: 0
---

# Independent exact-target review: E13 remote process-scan hardening

## Verdict

**PASS** for runner SHA-256 `418c72316a055d0260ba88ccf85e31dba98cc0e0256d499fefa96063aa82e694` at exact target commit `9b34056ec27a54c2e7c1265d78b002715a4cca6d`, whose direct parent is `dced7666bcb3c5f79efd2d983045bac35932d89b`. The targeted change closes R16 P2-1 at source and synthetic-test level. Findings: P0=0, P1=0, P2=0.

This is not a board-readiness verdict and does not authorize a board run.

## Frozen inputs and method

The review ran in clean worktree `/home/zhiro/research/kv260-vlm-workers/R19-E13-process-scan-review`, branch `agent/R19-E13-process-scan-review`. Before source review or testing, I verified the exact target and direct parent, clean worktree, R19 brief SHA-256 `2b35465ed72f85e5508e0d5a1f4b6febdbd72f121b43bdbecf25caa5f5c049b2`, activation SHA-256 `dd3222319af445b7d91ad647e0bac79bfa6563885710344c447325303e321977`, source manifest SHA-256 `a5d70126b315afe441f50c3b37b82a59bcc34c107e4e31e97cf6d1d673c5e0f3`, and every manifest entry. All manifest entries passed `sha256sum -c`. The preserved R16 audit archive still matches SHA-256 `725afd51970d77fc9430584d374f2ccb28600400da1833e50baab5d11ac1ae64`.

The target diff changes only `scripts/run_board_cpu_p2_textvqa.py`, adds `tests/test_p2_remote_process_scan_errors.py`, and adds the E13 handoff. I traced both production scans and the gates consuming their results, checked production defaults and the `FileNotFoundError` behavior, and reviewed the E13 builder handoff. The parser context is pinned at SHA-256 `48c834d6b803eb6a06f4be39f287913c461701ec606956c66493fe7f10d7e209`; the preflight helper remains at SHA-256 `16d5bf8a2158dd16f409fb6708fe60440cc95585e98f41044ce5732b192c9616`.

## Findings and checks

1. **Both per-process scans fail closed on inspection errors.** In the embedded worker's `owned_cli_processes()` and generated `remote_status_source()`, `FileNotFoundError` is handled as a process-disappearance race. The following generic `OSError` handler records the PID as unreadable; `PermissionError` is covered because it subclasses `OSError`, and non-permission errors such as `IsADirectoryError` are covered by the same branch.
2. **Cleanup verification cannot accept an unknown scan.** Worker cleanup requires no found CLI, no unreadable PIDs, and no unproven termination. An unreadable PID therefore prevents `remote_process_cleanup_verified=True` and blocks successful completion through the normal cleanup gate.
3. **Remote status cannot say `COMPLETE` on an incomplete scan.** The generated status source starts at `REMOTE_STATE_UNKNOWN`, records unreadable PIDs, and sets `COMPLETE` only when the lock is free, completion evidence validates, and both found and unreadable lists are empty. A top-level procfs iteration error propagates from the generated source, so it cannot produce an empty successful status. A found CLI PID is exposed and also prevents `COMPLETE`.
4. **Normal cases and defaults are preserved.** Empty and non-CLI scans remain admissible; a vanished `cmdline` is ignored as specified. The worker's default procfs root remains `/proc`; generated status defaults remain `/proc` and `/home/ubuntu/kv260-vlm-p2-cpu`. Existing result/status fields and parser context were not changed.
5. **Scope is bounded.** The runner diff changes only the two intended scan sites and their injectable test inputs. It does not alter the CPU sampler, resource thresholds, timeout, result schema, owner-window reuse, or later non-start conflict handling. The last two R16 findings remain open.

The focused tests exercise the actual embedded worker helper and generated status source with synthetic temporary directories. They cover found and non-CLI processes, a disappearing entry, an unreadable `cmdline` that raises a non-permission `OSError`, refusal to complete on unreadable/found processes, normal completion, and a top-level procfs iteration failure. The test suite does not separately synthesize `PermissionError`; its handling is confirmed by the shared generic `OSError` branch in both production scans.

## Independent test record

Exactly one authorized invocation was run in the frozen reviewer worktree:

```text
$ python3 -m unittest discover -s tests -p test_p2_remote_process_scan_errors.py
.....
----------------------------------------------------------------------
Ran 5 tests in 0.005s

OK
```

Exit code: 0. This test used synthetic temporary directories only; it did not read host `/proc` or contact a board.

The frozen E13 handoff records the builder's first authorized attempt exiting 1 due to test-fixture mistakes and the corrected second attempt passing all five tests. Those builder invocations were not repeated during this review.

## Limits

This review establishes the exact source and synthetic-test behavior only. It does not establish live `/proc` visibility, board cleanup success, board readiness, SSH behavior, runtime/parser success, inference results, or performance. R16 P2-2 (cross-invocation owner-window enforcement) and P2-3 (durable later non-start conflicts) remain open. P3 remains `NO_GO_NOW`.

No host `/proc`, board, SSH, network, runtime, inference, benchmark, reboot, bitstream, or user data was accessed. No parser or runner command was executed. The only test command was the single authorized focused unittest invocation above.
