# Scheduler State — KV260 + MiniCPM-V 4.6

Updated: 2026-09-24
Coordinator branch: `orchestration/dispatch-20260924`
Coordinator worktree: `/home/zhiro/research/kv260-vlm-orchestration`
Coordinator head before this state refresh: `23f8ab1961d3045b438289d269e93e5551f5b746`
Primary evidence checkout: `/home/zhiro/research/kv260-vlm`, branch `master`, baseline `094edc130489dc59dd9333e4ae6b0aa4c8013149`.

## Stage and decision

- P0: the previously authorized normal reboot/reconnect and immediate CPU-runner CMA recovery gate passed. No new reboot is authorized.
- P1: prior-art and novelty screening are integrated. R01 returned **FAIL**; no method candidate is selected.
- P2: host CPU baseline, selected-request traces, and software gate preparation continue in isolated worktrees.
- P3: **NO_GO_NOW**. No research RTL, research bitstream, or board VLM inference.
- P4–P8: not started.

This is an active end-to-end research project. E02 (offline source remediation) and B05 (offline trace analysis) are delivered. R04 is independently reviewing E02; R05 is queued behind R04. These tasks cannot advance the board gate or change the novelty decision by themselves.

## Board and host evidence

- After the user-authorized reboot, the KV260 returned over Wi-Fi SSH with a new boot ID; the reboot marker was absent, APT idle, Jupyter and the starter-kit app active, and XRT reported the board ready.
- Three post-reboot snapshots recorded `CmaFree=1,014,300 KiB`, above the existing 700,000 KiB CPU-runner floor. The earlier low-CMA allocation owner remains unknown. This does not authorize another reboot or inference run.
- A validated AArch64 CPU CLI build and input-hash checks exist, but **no board VLM inference has run**.
- Board inference remains gated on current-SHA parser/runner review at the runner's configured paths, synthetic ALPHA evidence, live resources, and an inference-specific owner window. Physical recovery and image-specific rollback are not verified.
- Host TextVQA dev50 CPU baseline: 0.644 MMF soft accuracy, 0.68 exact normalized match, median fresh-process wall time 8.558 s and P95 12.548 s. These are development host results, not KV260 results.
- Existing host evidence includes four selected-request graph traces, four allocator-metadata requests, three selected timelines, and a 50-request visual-token log. None gives board traffic, PL time, physical occupancy, or measured DDR bytes.
- B03 traces contain 24 media groups and 21,936 vision-node records across four selected requests. B04 found 267 unique full per-op keys and five key-set equivalence classes. The callback runs after backend splitting, so these traces do not establish backend eligibility, selected K26 placement, or cost.

## Research decisions already reviewed

- A01/C01/R01 found no candidate that beats its strongest static control or has a measured K26 failure interval. R01's exact-SHA verdict is **FAIL**. H1–H3 remain measurement questions only; H4/H5 were screened out. No hypothesis is a contribution claim.
- B03 and R02 are integrated. R02 **PASS** (P0=0/P1=0/P2=1) validated the four trace identities, group counts, hashes, and claim limits. Its one P2 is a stale duplicate activation copy in the worker tree, not a trace-integrity failure.
- B04 and R03 are integrated. R03 **PASS** (P0=0/P1=0/P2=0). B04 shows that media-group ordinal adds no observed per-op signature-set membership beyond the full op/type/dimensions/strides key for these four requests. This rejects that narrow information-coverage claim only; allocation state, timing, placement, resource pressure, and K26 effects remain unmeasured.
- E01 reviewed the then-current parser/runner/preflight source snapshot: P0=0, P1=0, P2=7. The configured fixed review paths are still unsatisfied in the primary checkout. Its review does not imply execution readiness.
- B05's preliminary result (pending independent R05 review) finds the same five equivalence classes under full-key sets, multiplicity-preserving multisets, ordered sequences, and adjacent-transition profiles across the 24 selected media groups. It found no same-set/different-sequence pairs and recommends stopping the group-aware selector question for these traces. This says nothing about cost or hardware behavior.
- Frozen global source `status/go_no_go.md` is unchanged. Keep P3 at `NO_GO_NOW` unless new evidence passes the project gates and independent review.

## Active tasks and exact bases

- **E02 runner remediation:** delivered as `aad962435278e470d36b3a0f247e9fb5624cf0f1`, direct parent `7385c0b10033244b3e203a3b152ca63720207222`; three-file output hash check and all nine original E01 snapshot hashes passed. R04 is independently reviewing it. The proposed per-PID CPU estimate uses a conservative lower-bound interval. No tests or execution occurred. P2-5/6/7, configured review paths, ALPHA, live-resource evidence, and external owner-window proof stay unresolved.
- **B05 ordered trace audit:** delivered as `dbaf1372342b7535b33200a49a3711269d28fa07`, direct parent `f7ad31d98ba96846c2a7522f114f6e310f63b19b`; R05 is queued. It compares ordered full-key sequences and adjacent transitions against B04's per-op-key and group-set nulls using only frozen B03/B04 metadata. It cannot establish timing or novelty.
- **R04 / R05:** R04 is active against exact E02 target `aad962435278e470d36b3a0f247e9fb5624cf0f1`; R05 is frozen and queued against B05 target `dbaf1372342b7535b33200a49a3711269d28fa07`. Both reviews are isolated and prohibit tests, board access, and publication.
- Exact task, source-manifest, and activation records are in `orchestration/task_briefs/`, `orchestration/evidence_snapshots/`, and `orchestration/activations/`. `ACTIVE_TASKS.md` is the current dispatch table.

## Remaining blockers

- No measured KV260 VLM path, PS–PL transfer cost, PL timing, physical DDR traffic, or physical BRAM/URAM occupancy.
- No candidate has beaten the strongest tuned static baseline; the static control must be included in any future gated timing study.
- No frozen numeric tolerance and held-out quality contract for a PL path.
- No verified UART recovery route, research-bitstream load/rollback evidence, or new first-load authorization.
- E01's continuous-resource-monitoring, timeout executable identity, and orchestration regression-test findings remain open. This task has no authorization to add or run tests.
- `origin` is authenticated via local GitHub CLI/system Keyring and points to the user-supplied private repository. It currently has no branches/default branch. No branch, issue, PR, or project data has been pushed; do not publish without an explicit request.

## Next scheduling decisions

1. Complete R04 exact-target static review of E02. Integrate the source-only proposal only after a PASS, and keep remaining P2/external gates open.
2. Run R05 after R04 completes. If it passes, record the B05 negative result: group order adds no observed sequence class beyond the existing static controls for these four requests.
3. Use the two reviewed results to choose the next safe research task; any board timing work remains gated and needs a separately authorized window.
4. Refresh `ACTIVE_TASKS.md`, this state page, and `DECISION_LOG.md` after each reviewed integration. Do not edit the primary checkout or the frozen global no-go file.
5. Continue to label host metadata as host evidence and keep P3 `NO_GO_NOW`.
