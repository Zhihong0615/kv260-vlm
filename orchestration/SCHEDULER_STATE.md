# Scheduler State — KV260 + MiniCPM-V 4.6

Updated: 2026-09-24
Coordinator branch: `orchestration/dispatch-20260924`
Coordinator worktree: `/home/zhiro/research/kv260-vlm-orchestration`
Coordinator head before this state refresh: `9064a56056cdcf29b1e8ed2a1a15201c05c9f6ea`
Primary evidence checkout: `/home/zhiro/research/kv260-vlm`, branch `master`, baseline `094edc130489dc59dd9333e4ae6b0aa4c8013149`.

## Stage and decision

- P0: the previously authorized normal reboot/reconnect and immediate CPU-runner CMA recovery gate passed. No new reboot is authorized.
- P1: prior-art and novelty screening are integrated. R01 returned **FAIL**; no method candidate is selected.
- P2: host CPU baseline, selected-request traces, and software gate preparation continue in isolated worktrees.
- P3: **NO_GO_NOW**. No research RTL, research bitstream, or board VLM inference.
- P4–P8: not started.

This is an active end-to-end research project. E02/R04/B05/R05 are integrated; E03 is delivered and R06 is independently reviewing it. The B05/R05 offline trace result closes the narrow media-group sequence question for four selected host requests; it cannot advance the board gate or change the novelty decision by itself.

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
- B05/R05 **PASS**: independent recomputation confirms the same five equivalence classes under full-key sets, multiplicity-preserving multisets, ordered sequences, and adjacent-transition profiles across 24 selected media groups. No same-set/different-sequence or same-multiset/different-sequence pairs occur. Stop treating group ordinal/sequence as a novelty lead on these traces; any future cost question requires a separately gated comparison against the static full-key plus ordered-sequence/replay control. No cost or hardware behavior was measured.
- E02 and R04 are integrated at coordinator merges `0779431550886d982c7244e424d246e9a648a1b0` and `9064a56056cdcf29b1e8ed2a1a15201c05c9f6ea`. R04 **PASS** applies to the four scoped remediations (P0=0/P1=0/P2=2 conditional). It found two conditional residuals: non-finite load token input could bypass the threshold if corrupted/substituted; malformed CPU-row data could throw before the structured blocked record, though still before image staging. Neither was fixed by E02.
- Frozen global source `status/go_no_go.md` is unchanged. Keep P3 at `NO_GO_NOW` unless new evidence passes the project gates and independent review.

## Active tasks and exact bases

- **E02 runner remediation:** delivered as `aad962435278e470d36b3a0f247e9fb5624cf0f1`, direct parent `7385c0b10033244b3e203a3b152ca63720207222`, integrated at `0779431550886d982c7244e424d246e9a648a1b0`. All nine original E01 snapshot hashes passed. R04 reviewed all four scoped changes and passed; conditional residuals remain. No tests or execution occurred. P2-5/6/7, configured review paths, ALPHA, live-resource evidence, and external owner-window proof stay unresolved.
- **E03 input-validation hardening:** worker `9c048ce95400a8156c919dd0d0bb4279cace47cc` directly parents frozen base `c550d3fe7e5272e6fee42d259d7f861b55ea4b2a`; it changes only the host runner and its handoff. It addresses the two conditional R04 input-validation/auditability findings; no tests or execution occurred. R06 is reviewing exact target `9c048ce95400a8156c919dd0d0bb4279cace47cc` against a five-entry frozen manifest. Do not integrate before PASS.
- **B05 ordered trace audit:** worker `dbaf1372342b7535b33200a49a3711269d28fa07`, direct parent `f7ad31d98ba96846c2a7522f114f6e310f63b19b`, integrated at `45665f9961db555a1d7f24a154c695cb55841660`. It compares ordered full-key sequences and adjacent transitions against B04's per-op-key and group-set nulls using only frozen B03/B04 metadata. It cannot establish timing or novelty.
- **R04 / R05:** R04 review commit `e187bae6d630a0bf45d7ed0de9a5bf277da17f5a` is integrated at `9064a56056cdcf29b1e8ed2a1a15201c05c9f6ea`. R05 **PASS**, P0=0/P1=0/P2=0, reviewer commit `7890ba0640ade88937f58eeb3ca2a13dca3cd5cd`, integrated at `cb9b23f31ca1b1d49f4cfe97d359233e1c41e4da`. Reviews are isolated and prohibit tests, board access, and publication.
- Exact task, source-manifest, and activation records are in `orchestration/task_briefs/`, `orchestration/evidence_snapshots/`, and `orchestration/activations/`. `ACTIVE_TASKS.md` is the current dispatch table.

## Remaining blockers

- No measured KV260 VLM path, PS–PL transfer cost, PL timing, physical DDR traffic, or physical BRAM/URAM occupancy.
- No candidate has beaten the strongest tuned static baseline; the static control must be included in any future gated timing study.
- No frozen numeric tolerance and held-out quality contract for a PL path.
- No verified UART recovery route, research-bitstream load/rollback evidence, or new first-load authorization.
- E01's continuous-resource-monitoring, timeout executable identity, and orchestration regression-test findings remain open. R04 also recorded two conditional input-validation/auditability P2s. No tests are authorized by the current task briefs.
- `origin` is authenticated via local GitHub CLI/system Keyring and points to the user-supplied private repository. It currently has no branches/default branch. No branch, issue, PR, or project data has been pushed; do not publish without an explicit request.

## Next scheduling decisions

1. Keep the B05/R05 negative result closed; do not reactivate a group-aware selector claim on these four traces.
2. Complete exact-SHA R06 review of E03; integrate only after PASS.
3. Use reviewed E02/B05 results and remaining source-only gates to choose the next safe research task; any board timing work remains gated and needs a separately authorized window.
4. Refresh `ACTIVE_TASKS.md`, this state page, and `DECISION_LOG.md` after each reviewed integration. Do not edit the primary checkout or the frozen global no-go file.
5. Continue to label host metadata as host evidence and keep P3 `NO_GO_NOW`.
