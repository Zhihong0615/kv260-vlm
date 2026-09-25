# RM09 static FFN-down extent baseline

This is a bounded baseline correction over the frozen RM07 `vision_ffn_down_tile`.
K=4304, M=1152, the FP16 weight conversion, FP32 accumulator bank and reduction
order, 32-row activation tile, four-row compute granularity, and one-pool W/X/Y
staging all remain unchanged. The source only widens the legal active-N range
to positive multiples of four through 1120. The runtime patch admits the
observed wide and narrow extents for token groups 60, 63, 64, 66, and 70.

Apply `runtime_dispatch.patch` after the RM08 runtime patch to make the host
hook dispatch those extents. HLS input bounds and runtime extent checks are
separate: the HLS top remains statically bounded by the existing 1120-row
activation cache, while the host whitelist is exact to the audited workloads.

Run `scripts/rm09/run_static_extent_csim.sh` for deterministic generated-input
goldens at N=1008, 252, 1056, and 264. Run
`scripts/rm09/run_static_extent_hls.sh` for the single HLS synthesis. Both tools
write generated projects outside the repository under `/tmp` by default.
