# RM10 numeric worker handoff

- Branch: `codex/rm10-numeric` (isolated worktree).
- Result: all three final HLS reduction orders pass the frozen full-tensor RM09 gate on `ffn_down-0`, `ffn_down-13`, and `ffn_down-26`.
- Exact operation-order comparison passed against HLS source SHA-256 `367854f27a9d30b152e85999bc7c8d0a92cf731593062f9d6fe1bbfd9777c1c2`.
- Primary metrics: `results/captured_q37804/summary.csv`.
- Error histograms: `results/captured_q37804/absolute_error_histogram.csv` (all bins sum to the recorded element counts).
- Capture checksums: `capture_tensor_sha256.txt`; raw model-derived W/X/Y files remain outside Git.
- Full report and reproduction command: `RM10_NUMERIC_RESULTS.md`.
- Numeric validation does not establish HLS C-simulation, synthesis, routed timing, or board throughput.
