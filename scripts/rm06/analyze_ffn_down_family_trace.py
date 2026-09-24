#!/usr/bin/env python3
"""Derive per-layer board timing and shape coverage from a saved QID trace."""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trace", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    rows: dict[str, list[dict]] = defaultdict(list)
    metadata: dict[str, list[dict]] = defaultdict(list)
    for line in args.trace.open(encoding="utf-8"):
        item = json.loads(line)
        if item.get("record") == "layer_segment" and item.get("op") == "MUL_MAT":
            name = item.get("output_name", "")
            if re.fullmatch(r"ffn_down-\d+", name):
                rows[name].append(item)
        elif item.get("record") == "node" and item.get("op") == "MUL_MAT":
            name = item.get("output", {}).get("name", "")
            if re.fullmatch(r"ffn_down-\d+", name):
                metadata[name].append(item)

    expected = {f"ffn_down-{i}" for i in range(27)}
    if rows.keys() != expected:
        raise SystemExit(
            f"expected all 27 transformer ffn_down layers; missing={sorted(expected - rows.keys())}, "
            f"unexpected={sorted(rows.keys() - expected)}"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "layer", "calls", "K", "M", "N", "weight_dtype", "activation_dtype",
            "output_dtype", "weight_ne", "weight_nb", "activation_ne", "activation_nb",
            "output_ne", "output_nb", "board_cpu_total_s", "board_cpu_median_ms",
        ])
        for index in range(27):
            name = f"ffn_down-{index}"
            calls = rows[name]
            signatures = {
                (tuple(x["src0_ne"]), tuple(x["src1_ne"]), tuple(x["output_ne"]),
                 x["src0_dtype"], x["src1_dtype"], x["output_dtype"])
                for x in calls
            }
            if len(calls) != 5 or len(signatures) != 1:
                raise SystemExit(f"{name}: expected five identical signatures, saw {len(calls)} calls")
            first = calls[0]
            wne, xne, yne, wdtype, xdtype, ydtype = next(iter(signatures))
            node_signatures = {}
            for node in metadata[name]:
                output = node["output"]
                if tuple(output["ne"]) != yne:
                    continue
                inputs = node["inputs"]
                weight = next((t for t in inputs if t.get("dtype") == wdtype), None)
                activation = next((t for t in inputs if t.get("dtype") == xdtype and t is not weight), None)
                if weight is None or activation is None:
                    continue
                if tuple(weight["ne"]) == wne and tuple(activation["ne"]) == xne:
                    node_signature = (
                        tuple(weight["ne"]), tuple(weight["nb"]),
                        tuple(activation["ne"]), tuple(activation["nb"]),
                        tuple(output["ne"]), tuple(output["nb"]),
                    )
                    node_signatures[node_signature] = (weight, activation, output)
            if len(node_signatures) != 1:
                raise SystemExit(f"{name}: metadata signature missing or inconsistent")
            weight, activation, output = next(iter(node_signatures.values()))
            times = [int(x["elapsed_ns"]) for x in calls]
            sorted_ms = sorted(x / 1e6 for x in times)
            writer.writerow([
                name, len(calls), wne[0], yne[0], yne[1], wdtype, xdtype, ydtype,
                json.dumps(weight["ne"]), json.dumps(weight["nb"]),
                json.dumps(activation["ne"]), json.dumps(activation["nb"]),
                json.dumps(output["ne"]), json.dumps(output["nb"]),
                f"{sum(times)/1e9:.9f}", f"{sorted_ms[len(sorted_ms)//2]:.6f}",
            ])
    print(f"layers={len(rows)} calls={sum(map(len, rows.values()))} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
