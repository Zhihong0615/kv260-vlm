# RM13 checkpoint — 2026-09-26 21:47 CST

## Frozen work and source of truth

- Integration branch/worktree: `codex/rm13-integration` at `/home/zhiro/research/kv260-vlm-workers/RM13-integration`. Prior integrated head: `c58479a`; this checkpoint commit supersedes it.
- Contract: `experiments/rm13/quantization_contract.json`, SHA-256 `d3f8cf14c286dc9c3df0b18c16e4ca4471eff08df0c34a1f6ddff47a0a467058`. Scope is vision transformer FFN-up/down, symmetric signed W4A8 primary and W8A8 reference, group 128, per-channel/group weight scale and per-token/group activation scale, ordered F32 group merge. Language Q4_K_M unchanged.
- Frozen quality gate SHA-256 `3fc90a42b75b49198db6e90ea38809fc157ce657834be2cf1b12c01baeae0648`; frozen split manifest SHA-256 `5b798932b1ad08c85c6328cceab046f191e9dfbbc0a2df01f971f523eeb2e7b6`. Final set has 200 image-disjoint TextVQA validation QIDs. Do not tune on final outputs or revise these files during this campaign.
- Q runtime source SHA-256 `f9efcc80ccef45404b7549757c0eb3b16f6f876e2f912b065eefd89031affdc1`, CLI SHA-256 `44dfe61a953ec51f91f2bf4724353c9beab5c31c356022956ec972b54d94f6f3`, shared CPU library SHA-256 `00c207ecbf5cc160fc40d0664a7d54ca0fd1d05fd409a4db8be2a22eed5546b9`. Host fake quant is a quality vehicle, not an optimized A53 or PL speed result.

## In-flight host-only experiments

- Quality campaign run ID `rm13_final200_qsim_20260926_r01` in `/home/zhiro/research/kv260-vlm-workers/RM13-data-scorer/experiments/rm13/data/raw/rm13_final200_qsim_20260926_r01`. At checkpoint, 146/1400 cases completed (all original variant); completed records had exit 0 and parsed output. Earlier memory-pressure pause left two partial attempts; resume reran them as attempt02 without changing run ID. Append-only `events.jsonl` and raw logs are the evidence. The live runner PID at capture was 204311, but PIDs are not durable identifiers.
- The campaign is already running. If it exits before all cases complete, resume from the D worktree `/home/zhiro/research/kv260-vlm-workers/RM13-data-scorer` with: `python3 experiments/rm13/scripts/run_quality.py --cli /home/zhiro/research/kv260-vlm-workers/RM13-Q-quality/work/llama.cpp-rm13/build-rm13/bin/llama-mtmd-cli --manifest experiments/rm13/data/textvqa_v0.5.1_calibration20_final200/manifest.json --split final_test --final-test-approved --run-id rm13_final200_qsim_20260926_r01 --qcache-dir /home/zhiro/research/kv260-vlm-workers/RM13-data-scorer/experiments/rm13/data/qcache-final --runtime-source-sha256 f9efcc80ccef45404b7549757c0eb3b16f6f876e2f912b065eefd89031affdc1 --jobs 2 --resume`. First verify no orphan runner/CLI. Do not create another run ID or modify the frozen runtime.
- HLS source SHA-256 `292ae7a4d266518b55269581bc2cc2a2ff48f941eec6b907f8f1f0ae3a4cef15`. Fixed W4A8 down K4304 PE8×16 HLS: II=1 for integer K loop, 128 source MAC lanes; estimate 214.41 MHz, 140 DSP, 47,733 LUT, 45,251 FF, 51 BRAM18, 48 URAM. Synthetic K4304 C/RTL cosim passes; real up K1152 C-sim passes arithmetic/packing, but this routed image supports down K4304 only.
- Offline full-system Vivado run: `/tmp/rm13-w4a8-down-route-20260926T132239Z-f371cf79/full_system/`. At checkpoint, `route_design` succeeded with 0 critical warnings/errors; `write_bitstream` was underway and final post-route timing/resource reports were not yet captured. Do not load this image onto KV260.
- Post-place provisional full-system occupancy: 61,556 LUT, 65,806 FF, 12 DSP, 48 URAM, 12,260/14,640 CLB sites (83.74%); post-place WNS +1.768 ns. These are not final routed values. HLS's 140 DSP estimate contradicts Vivado's 12 DSP. H Worker is verifying that all integer MACs survived and whether narrow multiplies mapped into LUT/carry fabric; do not cite a 128-MAC physical roof until this is resolved.

## Decision-critical numbers and remaining gates

- Current RM10 measured complete FFN-down family is 83.082 s. W4A8 candidate projected compute-only family is 61.3836 s. Nominal tiled payload is 12.786 GB per family. Serial compute-plus-transfer lower bounds at 0.5/1/2/4 GB/s are 86.956/74.170/67.777/64.580 s, before activation quantization, packing, submit and sync. At 1 GB/s, only 8.912 s remains for *all* other cost to beat RM10. These are budgeting estimates, not measured W4A8 calls.
- H Worker must finish full-system post-route timing/resources, explain DSP mapping, and test one real RM06 FFN-down tile against the frozen quant software reference with exact int32 partials/scales and F32 output. Preserve raw evidence and commit the handoff. No board load.
- D Worker should let the frozen final campaign finish, score with the predeclared MMF TextVQA gate, review changed/failing cases, and report W8A8/W4A8 quality. No runtime or gate revisions during final evaluation.
- After both quality and routed hardware evidence are available, review native integer profitability and choose one RM13 decision. Board loading requires a separate artifact-specific review/authorization and a credible full-call margin. No new KV260 bitstream load, clock, driver, boot, network or system-image change has occurred in RM13.

## Worker branches

- Q: `codex/rm13-q-quality`, worktree `/home/zhiro/research/kv260-vlm-workers/RM13-Q-quality`; last integrated result `bf4d0f6`.
- H: `codex/rm13-h-integer`, worktree `/home/zhiro/research/kv260-vlm-workers/RM13-H-integer`; last integrated result `f371cf7`, route result pending.
- D: `codex/rm13-data-scorer`, worktree `/home/zhiro/research/kv260-vlm-workers/RM13-data-scorer`; last integrated result `b8c2b75`, final campaign running.
