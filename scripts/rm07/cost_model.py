#!/usr/bin/env python3
"""Schedule and transfer model for the frozen 27-layer FFN-down family."""

import argparse
import math

K = 4304
M = 1152
TOKEN_TILE = 32
OUT_TILE = 16
OUT_TILES_PER_BATCH = 8
M_BATCHES = M // (OUT_TILE * OUT_TILES_PER_BATCH)
K_WORDS = K // 8
N1120_CALLS = 35
N280_CALLS = 100
CPU_FAMILY_S = 250.124
REQUEST_CPU_S = 668.35

# Measured in the final Vitis HLS 2024.2 reports. The n-loop executes one
# 5,978-cycle schedule for each four-token group; tile_rows=24 therefore uses6
# groups instead of padding to eight.
WEIGHT_TILE_LOAD_CYCLES = 8611
TOKEN_GROUP_CYCLES = 5978
OUTPUT_PACK_OVERHEAD_CYCLES = 4
ACTIVATION_STAGE_OVERHEAD_CYCLES = 15


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clock-mhz", type=float, required=True,
                        help="RM07 post-route PL clock from Vivado")
    args = parser.parse_args()
    clock = args.clock_mhz * 1e6

    def compute_cmd_cycles(rows):
        return OUT_TILES_PER_BATCH * (
            WEIGHT_TILE_LOAD_CYCLES
            + (rows // 4) * TOKEN_GROUP_CYCLES
            + rows * (OUT_TILE // 8)
            + OUTPUT_PACK_OVERHEAD_CYCLES
        )

    def stage_cycles(rows):
        return rows * K_WORDS + ACTIVATION_STAGE_OVERHEAD_CYCLES

    full_rows = TOKEN_TILE
    tail_rows = 280 % TOKEN_TILE
    assert tail_rows == 24
    compute_full = compute_cmd_cycles(full_rows)
    compute_tail = compute_cmd_cycles(tail_rows)
    stage_full = stage_cycles(full_rows)
    stage_tail = stage_cycles(tail_rows)

    n1120_tiles = math.ceil(1120 / TOKEN_TILE)
    n280_tiles = math.ceil(280 / TOKEN_TILE)
    n1120_op = n1120_tiles * stage_full + n1120_tiles * M_BATCHES * compute_full
    n280_op = ((n280_tiles - 1) * stage_full + stage_tail
               + (n280_tiles - 1) * M_BATCHES * compute_full
               + M_BATCHES * compute_tail)
    family_cycles = N1120_CALLS * n1120_op + N280_CALLS * n280_op
    family_schedule_s = family_cycles / clock

    # Only K reduction-loop pipeline cycles are counted as arithmetic body;
    # other schedule cycles are kept in the residual rather than hidden.
    k_loop_iters_1120 = N1120_CALLS * n1120_tiles * M_BATCHES * OUT_TILES_PER_BATCH * (full_rows // 4) * (OUT_TILE // 4)
    k_loop_iters_280 = N280_CALLS * (
        (n280_tiles - 1) * M_BATCHES * OUT_TILES_PER_BATCH * (full_rows // 4) * (OUT_TILE // 4)
        + M_BATCHES * OUT_TILES_PER_BATCH * (tail_rows // 4) * (OUT_TILE // 4)
    )
    k_loop_cycles = (k_loop_iters_1120 + k_loop_iters_280) * 1360
    k_loop_s = k_loop_cycles / clock

    weight_batch_bytes = OUT_TILES_PER_BATCH * OUT_TILE * K_WORDS * 16
    activation_tile_bytes = TOKEN_TILE * K * 4
    output_batch_bytes = OUT_TILES_PER_BATCH * TOKEN_TILE * OUT_TILE * 4
    payload = {"W": 0, "X": 0, "Y": 0}
    for n, calls in ((1120, N1120_CALLS), (280, N280_CALLS)):
        ntiles = math.ceil(n / TOKEN_TILE)
        payload["W"] += calls * ntiles * M_BATCHES * weight_batch_bytes
        payload["X"] += calls * n * K * 4
        payload["Y"] += calls * n * M * 4
    pl_payload = sum(payload.values())

    one_pool = weight_batch_bytes + activation_tile_bytes + output_batch_bytes
    double_pool = 2 * weight_batch_bytes + 2 * activation_tile_bytes + 2 * output_batch_bytes
    page = 4096
    one_pool_pages = (math.ceil(weight_batch_bytes / page)
                      + math.ceil(activation_tile_bytes / page)
                      + math.ceil(output_batch_bytes / page))
    double_pool_pages = (2 * math.ceil(weight_batch_bytes / page)
                         + 2 * math.ceil(activation_tile_bytes / page)
                         + 2 * math.ceil(output_batch_bytes / page))

    weight_port = 16 * clock
    xy_port = 32 * clock
    min_pl_transfer = payload["W"] / weight_port + (payload["X"] + payload["Y"]) / xy_port
    core_s = family_schedule_s - min_pl_transfer

    print(f"shape N=1120: {n1120_op:,} cycles/op, {n1120_op/clock:.6f} s/op")
    print(f"shape N=280:  {n280_op:,} cycles/op, {n280_op/clock:.6f} s/op (8×32 rows + 1×24 rows)")
    print(f"compute commands={N1120_CALLS*n1120_tiles*M_BATCHES + N280_CALLS*n280_tiles*M_BATCHES:,}; activation-stage commands={N1120_CALLS*n1120_tiles + N280_CALLS*n280_tiles:,}")
    print(f"family scheduled cycles={family_cycles:,}, {family_schedule_s:.3f} s @ {args.clock_mhz:.3f} MHz")
    print(f"K-loop arithmetic body={k_loop_cycles:,} cycles, {k_loop_s:.3f} s; residual schedule={family_schedule_s-k_loop_s:.3f} s")
    print(f"payload bytes W={payload['W']:,}, X={payload['X']:,}, Y={payload['Y']:,}, total={pl_payload:,} ({pl_payload/1e9:.3f} GB)")
    print(f"one-buffer DMA pool={one_pool:,} B ({one_pool/2**20:.3f} MiB), page-rounded={one_pool_pages*page:,} B ({one_pool_pages} pages)")
    print(f"optional double pool={double_pool:,} B ({double_pool/2**20:.3f} MiB), page-rounded={double_pool_pages*page:,} B ({double_pool_pages} pages)")
    print(f"HLS port minimum transfer={min_pl_transfer:.3f} s; no-stall schedule residual/core={core_s:.3f} s")
    print("bandwidth scenarios (serial single-buffer schedule; command submit/sync not included):")
    print("GB/s | PL transfer s | host copy s | family s | request s | request speedup | submit budget ms/call")
    for bw in (0.5, 1.0, 2.0, 4.0):
        B = bw * 1e9
        pl_transfer = payload["W"] / min(B, weight_port) + (payload["X"] + payload["Y"]) / min(B, xy_port)
        host_copy = 2 * pl_payload / B
        family = core_s + pl_transfer + host_copy
        request = REQUEST_CPU_S - CPU_FAMILY_S + family
        budget_ms = 1000 * (CPU_FAMILY_S - family) / (
            N1120_CALLS * n1120_tiles * (1 + M_BATCHES)
            + N280_CALLS * n280_tiles * (1 + M_BATCHES)
        )
        print(f"{bw:4.1f} | {pl_transfer:13.3f} | {host_copy:11.3f} | {family:8.3f} | {request:10.3f} | {REQUEST_CPU_S/request:15.3f} | {budget_ms:19.3f}")

    break_even = (3 * pl_payload) / (CPU_FAMILY_S - core_s)
    print(f"break-even effective DDR bandwidth including 3 total DDR touches: {break_even/1e9:.3f} GB/s (assuming B<3.0 GB/s and zero submit overhead)")
    print(f"break-even PL-only bandwidth excluding CPU staging copies: {pl_payload/(CPU_FAMILY_S-core_s):.0f} B/s")


if __name__ == "__main__":
    main()
