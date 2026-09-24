# RM07 HLS root cause and schedule checkpoint

## Root cause of the K16 compute-loop II

Vitis HLS 2024.2 synthesizes the reduction loop at `vision_ffn_down.cpp:97` to an achieved **II=5**, with 269 K-group iterations and 1,360 cycles for the pipelined loop. The scheduler reports a carried dependence at the FP32 `accum[i][j][p] += w*x` update on line 116, distance 1. Each one of the 16 partial accumulators for an output is revisited on the next `kbase` iteration; the FP32 add feedback latency therefore limits the recurrence to one update every five clocks. The activation and weight arrays are banked; the report identifies the accumulator recurrence, rather than an activation port conflict, as the II limit.

The source describes `PE_M × PE_N × K_LANES = 4 × 4 × 16 = 256` products per K group, but the generated compute loop contains **52 FP32 multipliers**. The final top estimates **184 DSP** (181 in the compute module and 3 in activation staging). The 52 multiplier instances account for 156 DSP; HLS resource sharing means source-level lane count is not the hardware multiplier count.

## Dynamic extent and exact schedule derivation

Both extents use one top and the same arithmetic. HLS reports:

| Scheduled loop | Latency |
|---|---:|
| One 16-row weight tile load: 16×538 packed words, II=1 | 8,611 cycles |
| Four output groups for one 4-token group: 4×1,494-cycle loop | 5,978 cycles |
| Output pack/write loop for 32 rows | 68 cycles |
| Output pack/write loop for the 24-row tail | 52 cycles |
| Activation-stage loop for 32 rows | 17,231 cycles |
| Activation-stage loop for the 24-row tail | 12,927 cycles |

Consequently, one 128-output compute command schedules to:

```text
N=1120 tile (32 rows): 8 × (8611 + 8×5978 + 68) = 452,024 cycles
N=280 tail (24 rows):  8 × (8611 + 6×5978 + 52) = 356,248 cycles
```

The N=280 last tile executes six four-row groups; it does not execute the two missing groups. The full-operation estimates in `RM07_RESULTS.md` compose these command schedules across the 35 and 9 token tiles, respectively. These are HLS scheduled cycles at the requested 200 MHz target. They are not measured DDR latency or board timing. An RTL co-simulation attempt did not complete its first compute transaction within six minutes and was stopped; full-shape timing must therefore retain the explicit no-DRAM-stall assumption until board or faster cycle-accurate evidence exists.

The final HLS resource run changes only the weight-cache banking from 16 row banks to four banks matching the four output-row PEs. Numeric semantics and the K-loop schedule stay the same; the final report is the source of truth for resource totals.
