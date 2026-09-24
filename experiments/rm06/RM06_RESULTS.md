# RM06 — FFN-Down Family Real PL Validation

Status: **blocked at first board load**. Real tensor capture, multi-layer K16 C-simulation, and full-system route/bitgen/XSA validation are complete. No custom PL image has been loaded.

## Family signature and coverage

Source: the QID 37804 4-thread board optrace in RM05, with tensor `ne`, `nb`, dtype, and selected-node timing records. One request evaluates five image groups. The transformer has 27 `ffn_down-*` layers, five calls per layer; the separate ViT merger operation is listed independently.

| Family | Layers | Calls/request | K/M/N | dtype W/X/Y | W/X/Y row strides (bytes) | CPU board time | MAC |
|---|---:|---:|---|---|---|---:|---:|
| Transformer FFN-down, layer 0–6 | 7 | 35 | 4304/1152/1120 | F16/F32/F32 | 8608/17216/4608 | 145.907 s | 194.362 GMAC |
| Transformer FFN-down, layer 7–26 | 20 | 100 | 4304/1152/280 | F16/F32/F32 | 8608/17216/4608 | 104.218 s | 138.830 GMAC |
| ViT merger FFN-down | 1 op | 5 | 17216/1152/280 | F16/F32/F32 | 34432/68864/4608 | 24.129 s | 27.766 GMAC |
| **All FFN-down rows above** | **27 transformer layers + merger op** | **140** | **3 signatures** |  |  | **274.254 s** | **360.958 GMAC** |

Transformer weights, activations, and outputs are contiguous in ggml storage for all 27 layers. Their full `ne`/`nb` are identical within each group; the N=1120 group stores X/Y as 19,281,920/5,160,960 bytes, and N=280 stores X/Y as 4,820,480/1,290,240 bytes. The merger has the same contiguous layout convention but a different reduction K and strides, with 39,665,664/19,281,920/1,290,240-byte W/X/Y payloads. The current static K16 top freezes `N=1120`, so it directly covers **7/27 layers (35/135 transformer calls)**; the 20-layer `N=280` group requires a shape/extent-capable top or a separately configured image. The merger is outside this datapath.

Exact 2-D ggml layout signatures are:

| Signature | W `ne` / `nb` | X `ne` / `nb` | Y `ne` / `nb` |
|---|---|---|---|
| Transformer N=1120 | `[4304,1152]` / `[2,8608]` | `[4304,1120]` / `[4,17216]` | `[1152,1120]` / `[4,4608]` |
| Transformer N=280 | `[4304,1152]` / `[2,8608]` | `[4304,280]` / `[4,17216]` | `[1152,280]` / `[4,4608]` |
| Merger N=280 | `[17216,1152]` / `[2,34432]` | `[17216,280]` / `[4,68864]` | `[1152,280]` / `[4,4608]` |

The often-cited **42.90%** uses all transformer FFN-down nodes **plus the separate ViT merger FFN-down op**: `274.254 s / 639.300 s` of measured vision-encode plus image-decode time. Transformer blocks alone contribute `250.124 s` (39.12% of that vision interval; 37.42% of full request wall); the merger adds `24.129 s` (3.77% of vision; 3.61% of request). The 274.254 s total is also 47.0% of the selected 845 matmul-node interval total (`583.783 s`) and 41.03% of full request wall (`668.35 s`). It is not 42.9% of all matmul time or full request wall.

An Amdahl ceiling for only the directly covered seven transformer layers can be stated without extrapolating to N=280: their board time fraction is `p=145.907/668.35=0.2183`. The old K16 OOC projection gives a compute-only subset speedup `s=145.907/(7×3.920)=5.317`; under zero boundary/fallback cost, that would give `Trequest≈550.18 s` (17.7% below 668.35 s). This is **not an observed PS–PL result**. The full 27 transformer down layers are 37.42% of request wall (or 41.03% including merger), but no measured K16 speed exists for N=280 or merger K=17216, so an end-to-end prediction for the full set is not yet supportable.

## RM06 corrected K16 static baseline

The RM06-specific HLS source now freezes the real `ffn_down-0` orientation `K/M/N=4304/1152/1120`, with `F16×F32→F32`, K16, PE 4×4, and 16×32 output tiles. HLS C-simulation passed its synthetic tile golden with zero mismatch. Full-shape HLS synthesis and IP export completed:

| Metric | RM06 HLS result |
|---|---:|
| Full-op cycles | 164,188,802 |
| Compute-loop II | 5 (269 reduction iterations) |
| Inferred FP32 multipliers | 52 (compute-loop report) |
| HLS estimated Fmax | 265.32 MHz |
| Target clock | 200 MHz |
| DSP / LUT / FF | 182 / 72,918 / 59,980 |
| BRAM18K / URAM | 54 / 40 |
| Packaged HLS IP SHA-256 | `55327cfd5c17e742ac3538fd1637e5fcf9208fe710d40b37bb60d23689ef216f` |

These are synthesis results, not a board measurement. The HLS implementation has 4×4 output PEs and K16 lanes, but its actual reduction-loop II remains 5; the measured throughput must use the 164,188,802 full-op schedule rather than nominal 16-lane parallelism. Full-system routing is reported below.

## Real tensor K16 C-simulation

Vitis HLS C-simulation ran the actual K16 top over 12 16×32 tiles per layer (9 fixed-grid positions plus 3 seeded pseudo-random positions), comparing against the captured CPU output. This is a sampled numerical check, not a full-tensor run or end-to-end VLM quality test.

| Layer | Shape K/M/N | Output elements sampled | Max abs error | RMSE | Cosine similarity | Bitwise equal |
|---|---|---:|---:|---:|---:|---:|
| `ffn_down-0` (early) | 4304/1152/1120 | 6,144 | 2.38419e-6 | 1.90119e-7 | 0.999999999999953 | 570/6144 |
| `ffn_down-13` (middle) | 4304/1152/280 | 6,144 | 8.04663e-7 | 1.08989e-7 | 0.999999999999903 | 453/6144 |
| `ffn_down-26` (late) | 4304/1152/280 | 6,144 | 4.00543e-5 | 2.80388e-6 | 0.999999999999960 | 641/6144 |

All three real-tensor HLS C-sim runs completed with zero testbench errors. The layer-26 maximum error is larger than the earlier two samples but remains small relative to its near-unit cosine; this is still tile-sampled and does not establish a task-level quality bound. The C-sim runner and testbench are `scripts/rm06/run_k16_real_tensor_csim.sh` and `experiments/rm06/source/k16_down/tb_real_tensor_multitile.cpp`.

## Real tensor capture run

- Board: KV260; request QID 37804; four A53 threads; CPU-only.
- Model/mmproj/runtime/image inputs match the RM05 frozen request. The image SHA-256 is `3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f`; runtime commit is `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`.
- Capture targets: `ffn_down-0` (early, N=1120), `ffn_down-13` (middle, N=280), `ffn_down-26` (late, N=280).
- An initial capture attempt was discarded after checking ggml scheduler semantics: activation reads must occur after a node-completion synchronization callback. The corrected binary forces that synchronization at each target and writes W/X/Y only after the output is complete.
- Corrected AArch64 capture binary SHA-256: `e019f99ff8c736f75785556438350d0fea8c05896cdf8adf044c60cacedbb34c`.
- Corrected capture completed all three layers and the request successfully (`G`); the answer matches the frozen QID 37804 CPU request. The instrumented run took 668.03 s wall time and peaked at 1,875,420 KiB RSS; this is not substituted for the frozen CPU baseline.
- During capture, `MemAvailable` was about 1.89 GiB and `CmaFree` fell to roughly 13 MiB. The three full-tensor payload sizes are about 32.77 MiB for N=1120 W/X/Y and 15.29 MiB for N=280 W/X/Y. They cannot all be allocated from the observed in-request free CMA; the actual standalone PL buffer plan and footprint remain unmeasured.
- Captured tensor files are local, ignored experiment artifacts under `experiments/rm04_system/local_tensors/rm06_ffn_down/q37804/`; their SHA-256 values are recorded below, while the model-derived payloads remain uncommitted.

| Captured layer | W SHA-256 | X SHA-256 | CPU Y SHA-256 |
|---|---|---|---|
| `ffn_down-0` | `b2e5111fdd29185654baf47e5437e322ec9433ec58f75921b2a82e2bb2117676` | `80dfa4a1d48dfa3519ae173eb551bdd22822f075e25d0a5373ace96b6cb12305` | `cabb0c46016184dc66a44177fdc9c209816c864db975fce9b1f064ca5da6c9fe` |
| `ffn_down-13` | `38311e9e31a292f0dd1f1e955e051ec3d1d97f9543a2debd47e78ec7b55ce2` | `0bc7cc1b61f1e7f1267d9b406fdc4d760f76054c0ee0c78f5dd7e537b2d6013b` | `39efbf7ee3633615bf173e66df3052f7ca141f634699f4eefe9e7c1447c264b7` |
| `ffn_down-26` | `6bf29d68d60baef712bd9435ecc57476ab2e5f7ef480fbe63b61e7d7e82d04d7` | `9446e8651a947fe10690632fdf41bb30450417983aac272f89dba0609838a520` | `9a1285c2fb62e5e5075b2681275b73291e65d8c6cccd07620b2a8e84de9a6473` |

## Full-system Vivado implementation

The HLS IP was integrated into a KV260 base design with PS AXI-Lite control, three HLS AXI4 memory-mapped masters through SmartConnect to PS HP0 DDR, and an AXI Performance Monitor. These are direct DDR masters; there is no separate AXI DMA IP. Vivado 2024.2 completed synthesis, place, route, bitgen, and XSA validation for `xck26-sfvc784-2LV-c`.

| Post-route result | Value |
|---|---:|
| Actual platform PL `clk_pl_0` | 187.512 MHz (5.333 ns; below requested 200 MHz) |
| WNS / TNS | +0.398 ns / 0 ns; 0 failing setup endpoints |
| WHS / THS | +0.010 ns / 0 ns; 0 failing hold endpoints |
| LUT / FF | 69,132 (59.03%) / 67,092 (28.64%) |
| CLB sites | 13,145 / 14,640 (89.79%) |
| DSP | 182 / 1,248 (14.58%) |
| BRAM tiles | 24 / 144 (16.67%; 15 RAMB36 + 18 RAMB18 primitives) |
| URAM | 40 / 64 (62.50%) |

The worst routed setup path starts at the weight-tile URAM clock and ends at a pipelined FP32 normalization register; data delay is 4.741 ns, split into 2.984 ns logic and 1.757 ns routing. CLB-site occupancy is 89.79%, so area headroom is tighter than the LUT percentage alone suggests.

Artifact SHA-256: bitstream `31ece1c9eee225931a860000b0a615778aa32085eeb69eb1976e0f083449abfc`; validated XSA `adcebed105372259967d1befab38ba4794d2dbbf1351728ba769d03c4ceb6e82`. Local build paths (both ignored by Git): `experiments/rm06/build/k16_down_system/kv260_rm06_k16_down.runs/impl_1/kv260_rm06_k16_down_wrapper.bit` and `experiments/rm06/build/k16_down_system/kv260_rm06_k16_down.xsa`.

The reproducible source/scripts checkpoint is commit `43a0a0ea7863feb14e4c4e4bfb6a64b099538d29` on `codex/rm06-ffn-down-pl-validation`. The final Tcl edit in that checkpoint reopens the completed implementation only to emit reports/XSA; it does not change the synthesized hardware sources.

## Board boundary/load state

A fresh read-only KV260 snapshot at `2026-09-24T12:51:37Z` recorded boot ID `2a931c48-99ad-4a3f-b3e1-f42634597098`, KV260 revB, kernel `5.15.0-1027-xilinx-zynqmp`, four A53s, XRT 2.13 Device Ready, `k26-starter-kits` / `XRT_FLAT` active in slot 0, FPGA Manager `operating`, `CmaTotal=1,024,000 KiB`, `CmaFree=557,112 KiB`, `MemAvailable=3,323,040 KiB`, swap 0, apt and apt-upgrade inactive, and no matching VLM/XRT/Vivado/apt process. PackageKit's service was active; this check did not query a PackageKit transaction. Raw output is `experiments/rm06/results/board_readonly_2026-09-24.txt`.

This is an idle-time snapshot. During the captured CPU-only QID37804 request, CMA fell to about 13 MiB. The current full-operation HLS API expects three independently contiguous full-tensor buffers for N=1120: W 9,916,416 B (9.46 MiB), X 19,281,920 B (18.39 MiB), Y 5,160,960 B (4.92 MiB), total 34,359,296 B (32.77 MiB). The largest single buffer and total working set exceed that observed in-request free CMA. No RM06 code implements a bounded host DMA buffer yet; actual CMA allocation/consumption is UNKNOWN. No standalone PL call was run.

The RM04 **Dynamic8** image (SHA-256 `041992089becb6167bafdd1d16b569a20a567de389e8e25b8bf211eb59d474d9`) is not the RM06 candidate. The RM06 K16 bitstream and XSA were generated and validated but **not loaded**. The board currently reports the starter-kit design and XRT ready; that state does not establish an independent physical recovery route or exact rollback procedure. `sudo -n xmutil listapps` works, but a load/unload method, compatible board deployment app/driver, and recovery from an unbootable board remain unverified. This is an actual hardware-recovery risk. Therefore PL cycles, DMA latency, bandwidth, effective GMAC/s, total call latency, and PS+PL VLM results are all UNKNOWN.

| Requested comparison | Evidence now available |
|---|---|
| CPU-only `ffn_down-0`, 5 calls | 20.628 s, direct KV260 measurement from RM05 |
| CPU-only full QID37804 request | 668.35 s frozen 4-thread baseline |
| CPU-only full FFN-down family | 274.254 s measured across 140 intervals in the selected request profile |
| K16 compute | HLS schedule only: 164,188,802 cycles for one N=1120 operation; not board cycles or observed latency |
| PL kernel / DMA H2PL / DMA PL2H / packing / submit-sync | UNKNOWN; image not loaded |
| PL call latency / effective GMAC/s / measured DDR bandwidth | UNKNOWN; image not loaded |
| Full-family CPU vs PL / CPU-only vs PS+PL VLM wall / answer comparison | UNKNOWN; no PS+PL execution |

The current top is full-tensor-pointer based, not bounded. For an N=1120 operation, it needs three independently contiguous 9.46/18.39/4.92 MiB buffers simultaneously (32.77 MiB total). During CPU VLM execution the observed free CMA was about 13 MiB; the available HLS interface therefore cannot be used as-is for a concurrent request without either acquiring enough contiguous memory or changing the data-transfer interface to bounded buffering. Neither actual CMA allocation nor a bounded-buffer PL path has been measured.

## Decision

Not selected. A and B require real PS–PL boundary and full-request results, while C requires a measured negative standalone/system result. Those cannot be obtained until the compatible load/run path and verified recovery route exist. The current fixed-N image matches only 7/27 transformer layers; the 20 N=280 layers require an extent-capable or separately configured implementation, and the merger is a distinct shape. No full-family PL speedup or end-to-end result is claimed.
