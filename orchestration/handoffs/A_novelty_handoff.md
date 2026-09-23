# A01 prior-art / novelty handoff

## Direct answer

No method claim currently survives; the current evidence supports “none.”
The close papers already cover the broad mechanisms: phase assignment, fixed-shape normalization, phase-aware execution, memory movement, streaming/fusion, command aggregation, mode switching, and persistent state.
What remains are four empirical questions about MiniCPM-V's actual K26 path, not contributions: width-tail cost, cross-crop weight rereads, visual embedding handoff, and PS–PL command gaps.
The verified local record contains host traces and arithmetic screens, but no board MiniCPM-V run or physical PS–PL/DDR measurement.
A generic N-keyed GEMM/GEMV or phase selector is rejected as a distinct claim because static shape lookup is available before backend allocation and is already the strong control.
No global go/no-go or novelty verdict was changed.

## Evidence and research output

- The paper-by-paper analysis in [idea_derivation_chains_A01_20260924.md](../../literature/idea_derivation_chains_A01_20260924.md) records eight links for ReCoVLM, StreamTensor, TRINE, Persistent-State Dataflow, Hummingbird, MEADOW, TeLLMe, VersaVLM, UniVLM, Memory-Centric VLM Deployment, GLITCHES, and LUT-LLM.
- The falsifiable experiment sheet in [kv260_minicpmv_falsifiable_questions_A01_20260924.md](../../literature/kv260_minicpmv_falsifiable_questions_A01_20260924.md) specifies the actual trace, closest prior work, strongest static control, proposed numeric criterion, and rejection rule for each of four remaining questions.
- Read-only MiniCPM-V evidence used: /home/zhiro/research/kv260-vlm/literature/kv260_vlm_falsifiable_hypotheses_20260923.md, /home/zhiro/research/kv260-vlm/literature/idea_derivation_chains_20260923.md, /home/zhiro/research/kv260-vlm/spec/runtime_shape_visibility_audit_20260923.md, and cited host reports under /home/zhiro/research/kv260-vlm/experiments/derived/.
- Paper links and measurement boundaries are in the chain document. Primary sources include FCCM/IEEE/ACM proceedings or DOI records, full author preprints, the MLSys proceedings paper, and the HPEC conference-hosted PDF. Local access/hash records for AICAS and ReCoVLM remain in the read-only source checkout; no PDFs or traces were copied.
- Exact local research milestones:
  - **d21dfde3cc74ff17b05c5cdf1b9a52c4df6194fd** — frozen A01 brief copy and prior-art chains.
  - **0eb90ef5af999282c5507fc5f52ef93927dd8e91** — falsifiable MiniCPM-V/K26 questions.
  - This handoff is committed as the final A01 milestone immediately after those two; its commit is the branch HEAD reported with delivery.

## Source and evidence qualifications

- The frozen brief hash matches the coordinator copy: dfb6ff15751553ade16dbc76f57577e790fd7371f97ce557009e0d57afb6575b.
- All 10 paths listed in /home/zhiro/research/kv260-vlm-orchestration/orchestration/source_snapshots/TASK_A01.sha256 passed sha256sum -c before reading.
- The initial worker state matched the brief: branch agent/A01-prior-art, clean status, HEAD 094edc130489dc59dd9333e4ae6b0aa4c8013149.
- Board evidence is explicitly absent. Host graph shapes, logical buffer estimates, callback spans, and arithmetic padding are not physical traffic, lifetimes, or PL timing.
- Reported paper metrics retain their platform/model/measurement boundaries. In particular: ReCoVLM uses Orin Nano + PCIe + VU9P and asymmetric full-system baselines; Persistent-State's fastest H_iter=8 latency is cycle-derived while H_iter=2 is the placed/routed point; TeLLMe end-to-end latency uses PYNQ timing while the breakdown is simulation-derived; GLITCHES combines measured transfers with simulated FPGA/system performance; the Memory-Centric AICAS prefill result has submitted-build/extended-build distinction.
- Proposed pass bars in the experiment sheet are not frozen and do not authorize board work.

## Rejected alternatives and blockers

- Broad PhaseMap novelty, generic phase specialization, generic shape/mode dispatch, generic stream/fusion/layout planning, generic buffer reuse, persistent state, bank/port placement, and command aggregation are rejected as stand-alone contribution claims by the closest prior art.
- The local T=8 padding screen already weakens a wide-tile-only H1 story; it is arithmetic evidence, not a measured runtime conclusion.
- No candidate has shown a K26 MiniCPM-V discontinuity or beaten its strongest static control. P3 remains NO_GO_NOW in the source checkout.
- Independent review is required before any Scheduler change to a global research decision.
- Remaining blockers are actual K26 execution traces, physical DMA/AXI and buffer evidence, held-out request evaluation, and frozen numerical/quality criteria. No board work, global status edit, or novelty promotion was performed.

## Changed files and checks

Changed files in this branch:

- orchestration/task_briefs/TASK_A01.md — exact frozen brief copy.
- literature/idea_derivation_chains_A01_20260924.md.
- literature/kv260_minicpmv_falsifiable_questions_A01_20260924.md.
- orchestration/handoffs/A_novelty_handoff.md.

Git identity was unset; each commit uses per-command Codex <codex@localhost> identity without persistent Git configuration.
Checks performed: initial branch/clean/HEAD verification; 10-source-hash verification; copied-brief SHA comparison; git diff --cached --check passed for both authored research documents. The frozen brief contains its original Markdown hard-break trailing spaces; it was kept byte-identical to the frozen coordinator copy. No tests were run or requested. No status files, board state, raw traces, model files, remotes, issues, or pull requests were touched.
