# B01 workload profile handoff

**Task:** P2 host-evidence profile for MiniCPM-V hardware decisions.
**Detailed profile:** [`experiments/derived/minicpmv_hardware_relevant_workload_profile_b01.md`](../../experiments/derived/minicpmv_hardware_relevant_workload_profile_b01.md).
**Evidence boundary:** Existing host TextVQA dev50 records only. No new trace collection, board command/inference, or global go/no-go/novelty edit.

## Result

The host records support workload priority and future test-shape selection, not concrete K26 hardware dimensions. The strongest priority is vision encoder plus projector, then image-embedding prefill. Matrix work is graph metadata and arithmetic proxy; phase times are host-only; allocator ranges are host virtual-buffer evidence. No evidence here sets PE shape, tile, local-memory capacity, buffer depth, DMA policy, or PS–PL boundary cost.

## Changed files

- `experiments/derived/minicpmv_hardware_relevant_workload_profile_b01.md` — concise evidence and decision profile, provenance, workload ranks, and ranked measurement gaps.
- `orchestration/handoffs/B_workload_handoff.md` — this handoff.

## Starting state, checks, and reproduction

- Verified worktree `/home/zhiro/research/kv260-vlm-workers/B01-workload-profile`, branch `agent/B01-workload-profile`, clean status, initial HEAD `094edc130489dc59dd9333e4ae6b0aa4c8013149`.
- Verified all nine named source files with `sha256sum -c /home/zhiro/research/kv260-vlm-orchestration/orchestration/source_snapshots/TASK_B01.sha256`; all returned `OK`. Their hashes and additional trace provenance are in the profile.
- Reproduce with that manifest check, then follow the nine frozen note files and profile formulas. The shape occupancy screen is inherited from the already-verified analytical note; no derived source code or raw trace was modified/copied.
- No tests were added or run. Review/checks were limited to initial Git state, source hashes, existing evidence reconciliation, and final Git diff/status.
- The source status records board inference paused pending current-SHA parser/runner review, synthetic ALPHA evidence, and an inference-specific owner window. No board action was attempted.
- Deliverable-content commit (profile plus initial handoff): `c0b35f155c604b28b04cc433339d6d62446a7c3d`. The following handoff metadata commit records this identifier.

## Top hardware-relevant workloads

1. **Vision encoder/projector:** first stage to time and evaluate for PS–PL assignment. Three selected host timelines show combined 3.20–7.25 s spans and 3/5/7 encoder calls; four selected graph traces include large F16 shape families. The combined span does not isolate vision from projector, setup, scheduler, upload, or copy.
2. **Image-embedding prefill:** first tile falsification family is Q4_K `ffn_up-0`, M/K=3584/1024 and N=60/64/66/70. The arithmetic screen makes fixed T=8 a required static control; it does not show the fastest tile.
3. **Three-, five-, and seven-group visual requests:** use the seven existing ordered patterns, including mixed `[64,70,70,70,70,70,70]`, to bound future buffer, DMA, reuse, and handoff tests. Current logs do not establish executed crop semantics or physical data movement.
4. **Text prefill/decode:** lower initial PL priority from host arithmetic proxies; preserve mixed Q4_K/Q6_K support and CPU fallback. No target latency or decode partition is established.

## Remaining unknowns ranked by importance

1. **K26 critical path and executed kernel timing:** a bounded board trace across one representative 3-, 5-, and mixed 7-group request after all board gates clear; include actual assignments, per-phase/op timing, first-token/full-request time, overlap, and uncertainty. Stop if a candidate is off the critical path or ties its best static control within uncertainty.
2. **Crop semantics and supported shape keys:** first audit the four already selected uncovered-pattern examples; only if current files do not answer, take metadata-only host traces recording image/crop identity, actual graph shapes, dtype/strides, and batch axes. Stop after one verified shape record per uncovered pattern; do not infer timing populations from those samples.
3. **Physical lifetime, DMA/AXI traffic, local-store use, and repeated-weight reads:** on a future authorized fixed-PL path, trace a 5×70 and mixed 7-group request with per-tensor transfer bytes, ownership/lifetime, reuse distance, local-store high-water mark, and stalls. Stop reuse/buffer claims if there is no repeated physical read or live-range conflict, or if a tuned static pool ties.
4. **PS–PL launch/sync/handoff cost:** collect PS submit, DMA, synchronization, idle-gap/stall, and handoff-byte timing in the same bounded board trace. Stop launch-aggregation work if the measured cost is immaterial or tuned static matrix dispatch ties.
5. **Held-out representativeness and quality:** freeze held-out pattern coverage, preprocessing, scoring, output cap, quality budget, and uncertainty threshold before comparing a real candidate. Stop if it misses quality or fails to beat uncertainty.
