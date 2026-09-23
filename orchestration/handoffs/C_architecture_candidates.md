# C01 architecture candidate screen and handoff

Date: 2026-09-24  
Status: initial frozen-evidence screen complete; no accelerator method candidate passes.  
Verdict: **NONE OF THEM IS STRONG ENOUGH.** P3 remains `NO_GO_NOW`.

## Decision boundary and provenance

- Worktree: `/home/zhiro/research/kv260-vlm-workers/C01-architecture-candidates`
- Branch: `agent/C01-architecture-candidates`
- Required starting HEAD: `094edc130489dc59dd9333e4ae6b0aa4c8013149`; worktree was clean before edits.
- Source evidence was read from `/home/zhiro/research/kv260-vlm` only. Every one of the nine listed source files matched its entry in `/home/zhiro/research/kv260-vlm-orchestration/orchestration/source_snapshots/TASK_C01.sha256`. No source-checkout file was modified.
- Pinned project baseline: MiniCPM-V 4.6; `llama.cpp` `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`; project HEAD `094edc130489dc59dd9333e4ae6b0aa4c8013149`.
- The coordinator handoff directory `/home/zhiro/research/kv260-vlm-orchestration/orchestration/handoffs/` contained no files when checked after this independent analysis began. Thus this initial ranking does not incorporate A/B evidence.
- This is an architecture screen, not an RTL, board, contribution, or P3 decision. There is no measured KV260 VLM execution, PL job, PS–PL transfer, physical BRAM/URAM occupancy, PL traffic/stall trace, or candidate-versus-static full-request comparison. P3 status is unchanged.

The full comparison matrix is in [`spec/architecture_candidate_matrix_C01.md`](../../spec/architecture_candidate_matrix_C01.md). It details the three retained falsification cases. H4/H5 were screened but not promoted because their proposed failure intervals are not present in evidence.

## Evidence summary

- Host metadata records image-prefill `ffn_up-0` widths `N=60×1, 64×4, 66×1, 70×10` across 16 selected graph-node observations. These are graph shapes, not board jobs or a measured latency cliff. An arithmetic-only padding screen reports useful-column occupancy of 97.3% for fixed tile `T=8`, versus 62.6% for `T=64`; it does not measure tile speed.
- The pinned runtime audit establishes that the backend sees node dimensions during eligibility before scheduler compute-buffer allocation. A normal N-to-tile or N-to-mode lookup is therefore an available static control. ReCoVLM also directly uses visual-token normalization to two fixed shapes; its paper's Orin/VU9P results do not transfer to K26.
- Host online timelines for three selected development requests report vision-plus-projector spans around 83.7–84.6% of online input-to-done medians; this combined host span cannot be assigned to an individual op or projected to K26. The Q4_K image-prefill host node interval is about 0.61–0.71 ms in two selected requests and includes dispatch/synchronization. None of these values is a board kernel cost or a PL saving.
- Seven logged visual-workload patterns contain 3/5/7 image-encode groups, but the logs do not prove that these correspond to independently executable PL jobs or repeated external weight reads. No PS–PL submission gap, copy at the vision/language handoff, or request-correlated CMA allocation cliff has been measured.
- K26's aggregate BRAM+URAM bit capacity is about 2.883 MiB, but usable capacity after logic, banking, ports, staging and buffering is unknown. A CPU-only board build/loader result is not a VLM timing result. Earlier low CMA observations occurred during updater activity; post-reboot snapshots report `CmaFree=1,014,300 KiB`, and no inference was run.

Primary frozen sources: `/home/zhiro/research/kv260-vlm/status/PROJECT_STATUS.md`, `status/go_no_go.md`, `literature/kv260_vlm_falsifiable_hypotheses_20260923.md`, `literature/independent_novelty_review.md`, `literature/notes/recovlm.md`, `spec/p3_candidate_decision_fixed_bitstream_draft.md`, `spec/vision_vs_q4_pl_mvp_screen.md`, `spec/runtime_shape_visibility_audit_20260923.md`, and `reviews/pl_mvp_interface_independent_review.md`. Relevant source evidence reports and their measurement limits are cited inline in the matrix.

## Candidate disposition

H1 (tile-tail cost), H2 (cross-group weight reuse), and H3 (PS–PL command replay) are the only cases retained for detailed comparison. Each has a finite *workload interval* worth measuring, but none has a finite observed *failure interval*: no target-board excess cost has been established, and no decision variable has been shown to beat the strongest static control. The matrix marks this distinction explicitly and supplies proposed numeric gates only for a future, separately authorized experiment.

H4 (vision-to-language materialization threshold) is not promoted: there is no real boundary trace proving an extra copy or local-memory spill. H5 (CMA admission cliff) is not promoted: there is no clean inference-time CMA failure or latency tail correlated with input shape, and the historical low-CMA observations are confounded by system update activity. H4/H5 are not candidate claims.

## Sole next-measurement recommendation

After the existing CPU-only board-run gates are independently cleared and a separate Scheduler brief authorizes measurement, collect one bounded KV260 CPU-only per-request trace for the frozen development request set already named in the P2 plan. Record the original-image/question-to-first-visible-token and to-completion boundaries, actual phase and target-node timings, raw graph shape and metadata available at the real selector point, request failures/fallbacks, and clock/temperature/memory context. Interleave repeated runs and retain all outcomes.

This one measurement establishes the K26 CPU Amdahl ceiling and whether candidate selector metadata is available at decision time. It does not prove a PL benefit or distinguish these mechanisms; do not begin a board experiment from this C01 handoff. The current C01 task ran no experiment and touched no board.

## Deliverable and review status

- Added `orchestration/handoffs/C_architecture_candidates.md` and `spec/architecture_candidate_matrix_C01.md`.
- No RTL/HLS, tests, board work, source-overlay edits, raw trace changes, or global status/novelty/go-no-go edits.
- Checks: required branch/base/clean starting state verified; all nine frozen source hashes matched; coordinator A/B handoff directory checked after analysis began and was empty at that time.
- Initial reasoning content commit: `f99b964cf4efecaae5bf924b150cb16bdcf064c6` (`Add C01 architecture candidate screen`). Later A/B incorporation, if warranted, must be a separate commit.
- No A/B evidence has been incorporated. Revisit only if committed A/B handoffs materially change the ranking; any such incorporation belongs in a separate update commit with exact A/B and C SHAs.

## Unresolved dependencies

There is no board PL workload/traffic evidence, no implemented accelerator, no exact measured dispatch-time selector capture, and no frozen held-out quality budget. Board CPU inference remains subject to its outstanding review and owner-window gates. Any PL measurement would require a separate Scheduler task brief and the applicable board/design authorization.
