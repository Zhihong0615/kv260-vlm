#!/usr/bin/env python3
"""Recompute RM05 CPU and RM08 board GMAC/s by exact FFN orientation."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CPU_PROFILE = ROOT / "experiments/rm05/results/q37804_vision_family_timing/q37804_vision_family_cpu_timing.csv"
BOARD_TRACE = ROOT / "experiments/rm08/evidence/rm08-vlm-q37804-20260925T063228Z/rm08_pl_trace.txt"
SHAPES = {
    (1152, 4304, 1120): "FFN up",
    (1152, 4304, 280): "FFN up",
    (4304, 1152, 1120): "FFN down",
    (4304, 1152, 280): "FFN down",
}


def main() -> None:
    cpu = {}
    with CPU_PROFILE.open(newline="") as f:
        for row in csv.DictReader(f):
            shape = (int(row["K"]), int(row["M"]), int(row["N"]))
            family = row["family"]
            if shape in SHAPES and family == SHAPES[shape]:
                calls = int(row["calls_per_request"])
                macs = int(row["total_MAC"])
                rate = macs / float(row["board_cpu_time_s"]) / 1e9
                assert calls > 0 and abs(rate - float(row["measured_GMAC_per_s"])) < 1e-9
                cpu[(family, shape)] = (calls, rate)

    board = defaultdict(lambda: {"calls": 0, "macs": 0, "kernel_ms": 0.0, "wall_ms": 0.0})
    for line in BOARD_TRACE.read_text().splitlines():
        if not line.startswith("RM08_PL_CALL ") or " status=PL " not in line:
            continue
        fields = dict(re.findall(r"([A-Za-z_]+)=([^ ]+)", line))
        shape = (int(fields["K"]), int(fields["M"]), int(fields["N"]))
        if shape not in SHAPES or SHAPES[shape] != "FFN down":
            continue
        agg = board[("FFN down", shape)]
        agg["calls"] += 1
        agg["macs"] += shape[0] * shape[1] * shape[2]
        agg["kernel_ms"] += float(fields["kernel_ms"])
        agg["wall_ms"] += float(fields["wall_ms"])

    print("family,K,M,N,RM05_CPU_calls,RM05_CPU_GMAC_s,RM08_PL_calls,RM08_kernel_GMAC_s,RM08_call_GMAC_s")
    for shape, family in sorted(((shape, fam) for fam, shape in cpu), key=lambda x: (x[1], x[0])):
        cpu_calls, cpu_rate = cpu[(family, shape)]
        agg = board.get((family, shape), {"calls": 0, "macs": 0, "kernel_ms": 0.0, "wall_ms": 0.0})
        if agg["calls"]:
            kernel_rate = agg["macs"] / agg["kernel_ms"] / 1e6
            call_rate = agg["macs"] / agg["wall_ms"] / 1e6
            board_values = f"{agg['calls']},{kernel_rate:.6f},{call_rate:.6f}"
        else:
            board_values = "NA,NA,NA"
        print(
            f"{family},{shape[0]},{shape[1]},{shape[2]},{cpu_calls},{cpu_rate:.6f},"
            f"{board_values}"
        )


if __name__ == "__main__":
    main()
