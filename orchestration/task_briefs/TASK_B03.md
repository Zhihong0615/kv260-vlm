# TASK B03 — Selected request graph metadata traces

## Objective

Capture one metadata-only CPU graph trace for each of qids 35950, 34609, 35419, and 35005 from the existing MiniCPM-V 4.6 TextVQA dev50 baseline. Determine whether the known logged visual-token patterns correspond to distinct per-op shape inventories. This is a workload evidence task; it does not select or implement a dispatch method.

## Frozen inputs

- Task setup parent: `358234101d1d448419a907c4221a06d72220be10`. The exact clean worker base is frozen in `orchestration/activations/B03.md` before the worker is created.
- Clean project baseline: `094edc130489dc59dd9333e4ae6b0aa4c8013149`.
- Pinned llama.cpp runtime: `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`.
- B02 audit and source snapshot: coordinator `bf7cc170c9fddcf40d843a9851958fe1d24cef6f`; evidence snapshot `548d6229d9fbff67db5103933d9c837259d6b4f4`.
- Exact absolute-path file hashes are in `orchestration/evidence_snapshots/B03_selected_qid_optraces/SOURCE.sha256`. Verify every entry before build or inference and stop on any mismatch.
- The four image hashes, model/mmproj hashes, selected existing command/log/resource records, source run hash, runtime build database, linked libraries, and tracer source hashes are included in that manifest.

## Capture procedure

1. Keep `/home/zhiro/research/kv260-vlm` read-only. Work only in branch `agent/B03-selected-qid-optraces` and write outputs only below that worker checkout. Use a unique task-specific `/tmp` build directory; never reuse or overwrite the earlier optrace build directory.
2. Adapt a copy of the existing metadata tracer to read the four selected prompts from the source run record and source images from their verified paths. It may read only request id, prompt, image path/id, and image hash for those qids; it must not access dataset answer/annotation fields.
3. Run one fresh CPU-only metadata trace per request with the previously used pinned model and runtime settings (`-t 8`, `-tb 8`, `-c 4096`, `-n 48`, fixed seed/temperature, `--device none`, `-ngl 0`). Discard stdout/stderr; do not save or inspect generated answers. Do not collect per-op timing or allocator metadata in this task.
4. Record the request/image identity and prompt hash in the wrapper manifest, never the prompt text. The CLI-local media-batch id may be added to node records. Clearly label it as an encoded media-batch identity: it does not identify internal crops. Record crop/group mapping as unavailable unless the runtime exposes it directly.
5. Parse only graph metadata rows. Produce a compact per-request/per-phase shape inventory and raw JSONL traces, compressed losslessly if useful. Record original and compressed trace hashes, row counts, return codes, exact build inputs, and any missing records. Never put prediction strings or answer labels in raw or derived artifacts.

## Interpretation limits

- The ggml eval callback receives graph nodes during scheduled graph computation after backend splitting. It is not a direct record of `supports_op` eligibility checks, final K26 placement, or dynamic selection.
- `--device none -ngl 0` gives CPU workload metadata only. It establishes no PL timing, physical DDR bytes, bank/BRAM/URAM occupancy, CMA behavior, PS–PL cost, or board feasibility.
- Per-request traces are descriptive examples, not a workload distribution or statistical result. Do not infer a method advantage from them.
- A shape-keyed static lookup at backend eligibility remains the strong dispatch control. B03 only improves the workload shape evidence used to assess that control.

## Stop conditions and forbidden actions

- Stop if any frozen source hash differs, an expected image/model/runtime file is missing, the selected output path already exists, or enough disk space is unavailable.
- No primary-checkout writes, new board SSH, board inference, reboot, bitstream build/load, tests, publication, push, issue, or PR.
- Do not change P3 `NO_GO_NOW`, propose a method claim, or broaden the task to other requests.

## Deliverables

- `scripts/run_selected_optrace_B03.py` and its isolated tracer builder copy.
- `experiments/raw/textvqa_selected_optrace_B03/` containing only redacted run metadata and compressed graph traces.
- `experiments/derived/selected_qid_optrace_B03_summary.json` and a concise interpretation note.
- `orchestration/handoffs/B03_selected_qid_optrace_handoff.md` with exact source/output hashes, command settings, findings, limits, and next discriminating step.
- One commit on the worker branch, based exactly on the coordinator target; no cherry-picks or source edits outside the worker.
