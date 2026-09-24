---
review_mode: independent_static
reviewer_role: independent_reviewer
runner_sha256: 0ff88fd1780fa52ae5a30a6a47fe89827887d4360e20a14e9dc3269e6fb6ba92
target_commit: 74dc08eb3114d6221eea5eadcc2fee2630cccc26
required_direct_parent: 9485eef4e975f7082d98d651bb156effd5221505
test_sha256: 7093a6680444f17aaf72b65977fa83d698a36582a5b7eb7c45276ddd892c3aea
preflight_sha256: 16d5bf8a2158dd16f409fb6708fe60440cc95585e98f41044ce5732b192c9616
parser_sha256: 0e28f81cc26ec47cfe2488c680623c74accd1bef92d9a4f3a31ae2fa73ba3b8d
verdict: PASS_WITH_P2_FINDINGS
P0: 0
P1: 0
P2: 3
---

# Independent exact-target review: CPU P2 TextVQA runner

## Verdict

**PASS_WITH_P2_FINDINGS** for runner SHA-256 `0ff88fd1780fa52ae5a30a6a47fe89827887d4360e20a14e9dc3269e6fb6ba92` at commit `74dc08eb3114d6221eea5eadcc2fee2630cccc26` (direct parent `9485eef4e975f7082d98d651bb156effd5221505`). I found no P0 or P1 issue in the E11 remote process-sampling repair. The three R15 P2 findings remain open and are listed below.

P0: 0
P1: 0
P2: 3

This source-level verdict satisfies the runner review gate's zero-P0/P1 condition for this exact runner hash. It is not a board-readiness verdict and does not authorize execution.

## Frozen inputs and method

The reviewer worktree was `agent/R16-E11-review` at `/home/zhiro/research/kv260-vlm-workers/R16-E11-review`. Before review or test execution, I verified the target and direct parent, a clean worktree, the activation and task brief, the frozen source-manifest digest, and every manifest entry. The manifest SHA-256 was `71617bd074bc990e82a3c3ece9d54e1475064b998e66d5405c523c31171180cf`; all entries passed `sha256sum -c`. The runner, focused test, E11 handoff, R15 report and preserved archive, R14 adapter review, parser, pinned preflight helper, task brief, and taskbook matched their frozen hashes.

I traced the production `REMOTE_WORKER` source from `process_cpu_snapshot()` and `sample_process_cpu()` through `rich_snapshot()` and `gate()` to the final prelaunch branch in `main()`. I checked the changes against each R15 P1 condition and verified that the pinned host preflight source remained byte-identical. I did not inspect dataset answers or annotations. I did not invoke the runner, remote worker, dry plan, board, SSH, network, runtime, inference, benchmark, or bitstream tools.

## R15 P1 audit

1. **Procfs read and parse failures are surfaced.** `process_cpu_snapshot()` returns top-level `/proc` iteration failures and records per-PID `OSError`, `ValueError`, `IndexError`, `StopIteration`, or `TypeError` failures. `sample_process_cpu()` combines both samples' errors and sets `PROCESS_STATE_UNKNOWN` whenever any error exists.
2. **The paired PID sets must match.** `sample_process_cpu()` compares `set(before)` and `set(after)`; a difference records `sample_pid_set_changed` and makes the state unknown. The gate treats any non-`OK` state or nonempty/missing error list as `PROCESS_STATE_UNKNOWN`.
3. **PID reuse and identity changes block.** The sampler checks each shared PID's `(comm, uid, starttime_ticks)` tuple and records `identity_changed` on a mismatch. It also checks the PID embedded in each stat record against its procfs directory name.
4. **CPU counters and timing are validated.** Negative deltas, a nonpositive clock tick rate, invalid/nonpositive per-process intervals, non-finite or negative CPU rates, and invalid overall sample duration mark the sample unknown. Gate-side type/range checks independently reject malformed values. A per-process interval shorter than the actual counter-to-counter gap is used as the denominator, which errs toward overstating CPU use rather than understating it.
5. **Unknown state blocks before CLI launch.** The final worker sample is taken at `pre = rich_snapshot()` after the board CLI help/artifact checks. A nonempty `pre["gate_reasons"]` returns at lines 859–862, before the subsequent `subprocess.Popen()` at line 911. Thus every sampler failure reaches the existing fail-closed launch branch.

The focused test extracts the literal embedded `REMOTE_WORKER` assignment from the production runner AST and executes its actual `rich_snapshot()`/`gate()` definitions with a temporary synthetic procfs tree, injected clock, sleeper, tick rate, and snapshot provider. It covers unreadable and malformed entries, appearing/disappearing PIDs, start-time change, negative delta, invalid tick rate, invalid elapsed time, stable below-threshold samples, and a busy process. The stable case also checks that valid low activity remains admissible; the busy case checks threshold rejection. This is a good targeted regression test for the identified helper logic. It does not dynamically run the worker's full `main()` or intercept its production `Popen`; that ordering was confirmed statically in the exact source.

## Thresholds and pinned preflight

The E11 diff does not alter the runner's configured resource thresholds or timeout limits: MemAvailable 2,750,000 KiB, CMA free 700,000 KiB, home free space 1 GiB, load1 maximum 1.5, per-process CPU threshold 0.25 cores, sample wait 2 seconds, CLI timeout 300 seconds, remote watchdog 540 seconds, and host wait 600 seconds. The separately pinned `scripts/board_cpu_preflight_remote.py` is unchanged at SHA-256 `16d5bf8a2158dd16f409fb6708fe60440cc95585e98f41044ce5732b192c9616`.

## Independent test record

Exactly one authorized invocation was run in the frozen reviewer worktree:

```text
$ python3 -m unittest discover -s tests -p test_p2_remote_process_gate.py
......
----------------------------------------------------------------------
Ran 6 tests in 0.004s

OK
```

Exit code: 0. The test used synthetic temporary procfs fixtures; it did not read the host's `/proc` or contact a board.

## Remaining P2 findings

These are the three findings carried forward from the preserved R15 review; E11 did not target them:

1. **Cleanup/status scans treat some process-inspection errors as absence.** The worker's owned-CLI scan and the remote status source can ignore non-permission `OSError` while reading command lines, so an unresolved scan may look like no process found. See the preserved R15 audit at `reviews/audit/R15_current_runner_BLOCKED_20260924.md`.
2. **One fresh CLI per owner window is not enforced across invocations.** The owner-window reference is recorded but is not durably checked for reuse across separate runs.
3. **Later non-start recording conflicts are not persisted.** A conflict found while recording a later qid may remain only in memory, leaving the raw evidence ambiguous even though the existing directory is not overwritten.

## Limitations

This review and test establish only the exact source behavior inspected and the focused synthetic test result. Two endpoint samples cannot observe a process that starts and exits entirely between scans; the CPU gate is a bounded point-in-time sample and retains an unavoidable post-sample time-of-check/time-of-use window before `Popen()`. No live board resource values, process visibility under the board's permissions, owner window, runtime/parser success, inference result, or benchmark result were checked. P3 remains `NO_GO_NOW`; this review makes no claim of board readiness.
