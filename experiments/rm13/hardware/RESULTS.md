# RM13 native W4A8 K26 evidence

Frozen semantics are in `../quantization_contract.json` (symmetric signed W4/A8, group=128; low nibble is even local K; per-group int32 reduction, ordered F32 scale merge, no bias). The kernel is compiled for K=4304, M tile=16, N tile=16, PE_M=8, PE_N=16. It supports the down projection K at runtime N/M extents; it does not support up K=1152 in this build.

## Correctness

- Synthetic K=4304 C simulation: exact group int32 partials (714), exact activation scales (102), all 21 active outputs bitwise equal to golden; includes +/− group accumulator boundary checks and final K tail with 80 valid elements.
- C/RTL co-simulation: PASS, 3/3 transactions, exact 714 partials and 102 scales, 21/21 outputs bitwise equal, edge checks pass. Log/report under `evidence/hls/cosim-k4304-m16n16/`.
- Real FFN-up fixture (K=1152, M=7, N=1) C simulation: 63 exact partials, 9 exact activation scales, 7/7 outputs bitwise equal. Independently regenerated first seven real weight rows match Q's packed W4 cache exactly. This validates arithmetic/packing only; current synthesis/route candidate is down-only K=4304.
- The offline packed-weight validator rejects reserved code −8; the PL hot loop omits the 32-way runtime nibble scan that caused the initial timing failure. The packer never emits −8.

## HLS candidates

All values below are HLS estimates, not routed results.

| Candidate | MAC lanes | Est. delay / Fmax | DSP | LUT | FF | BRAM18 | URAM | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Initial PE4×4, tile 16×4 | 16 | 15.222 ns / 65.69 MHz | 100 | 26,409 | 19,853 | 35 | 32 | Fails 100 MHz |
| Initial PE8×16 with runtime −8 scan | 128 | 15.222 ns / 65.69 MHz | 140 | 51,352 | 45,465 | 51 | 48 | Fails 100 MHz; serialized reserved-code guard was critical path |
| Fixed PE8×16, tile 16×16, no debug outputs | 128 | 4.664 ns / 214.41 MHz | 140 | 47,733 | 45,251 | 51 | 48 | Meets HLS estimate; route pending |

Fixed design uses 128 signed 4×8 MAC instances, plus conversion/control and F32 scale merge. Density is 0.914 integer MAC/DSP and 2.68 MAC/1k LUT. The K-group schedule reports 291 cycles/group, including ordered scale merge; one M sub-tile is approximately 10,030 cycles. It is therefore about 56 effective MAC/cycle, not 128 sustained MAC/cycle.

## Full down-shape compute projection

Projection at 100 MHz uses 72 M tiles and N tiles of 16, and includes scheduled F32 group merge. It excludes F32→A8 activation staging, AXI/memory transfer, launches/control, host packing, and all CPU work.

- K4304/M1152/N1120: 101,102,400 cycles = 1.011 s.
- K4304/M1152/N280: 25,997,760 cycles = 0.260 s.
- 35×N1120 + 100×N280 family: 61.3836 s compute-only.
- RM10 measured complete down family: 83.082 s. This leaves at most 21.6984 s for all incremental staging/transfer/launch/packing overhead to beat RM10. No full-call speedup is established here.

## Bytes and bounded staging

For one K4304 tile M16×N16: W4 codes 34,816 B, F32 W scales 2,176 B, source F32 X read once per N tile 275,456 B, internal A8 activation cache 68,864 B, cached F32 X scales 2,176 B, current-group F32 staging 512 B, F32 Y 1,024 B, and int32 group partials 1,024 B (debug capture disabled in performance build). External W4+scales+F32 X+F32 Y traffic totals 313,472 B per compute tile, below the 1,671,168 B contiguous BO bound. DDR tensors remain ordinary weight/activation/output buffers; the bound is not a claim that all DDR tensors are resident together.

Full compressed down weight: 2,506,752 B padded W4 codes + 156,672 B F32 scales = 2,663,424 B. Source activation F32 for N=1120 is 19,281,920 B; F32 output is 5,160,960 B. Thus packed W alone does not imply a corresponding complete-call traffic reduction.

## Provenance and next gate

HLS source SHA-256: `292ae7a4d266518b55269581bc2cc2a2ff48f941eec6b907f8f1f0ae3a4cef15`. The fixed no-debug HLS report and simulation evidence are checksummed in `evidence/hls/SHA256SUMS`. The full-system KV260 route is to run on the committed source. Do not load or run any image on board from this worker result. A route pass is necessary but not sufficient: quality, integer correctness, route, credible ≤21.7 s incremental-call budget, and separate artifact-specific authorization are required before any board experiment.
