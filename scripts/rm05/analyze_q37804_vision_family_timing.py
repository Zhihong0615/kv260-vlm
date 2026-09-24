#!/usr/bin/env python3
"""Aggregate board-timed vision MUL_MAT calls by operator family and shape."""
import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


def family(src0: str, src1: str) -> str:
    names = (src0 + " " + src1).lower()
    for token, label in (
        ("patch_embd", "Patch embedding"),
        ("attn_q.weight", "Q projection"),
        ("attn_k.weight", "K projection"),
        ("attn_v.weight", "V projection"),
        ("attn_out.weight", "Attention output projection"),
        ("ffn_up.weight", "FFN up"),
        ("ffn_down.weight", "FFN down"),
    ):
        if token in names:
            return label
    return "Other"


def load_rows(path: Path):
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid JSON at {path}:{line_no}: {exc}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--optrace", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--vision-seconds", type=float, default=None,
                    help="same-run measured vision timer; omit when unavailable")
    args = ap.parse_args()

    events = [r for r in load_rows(args.optrace)
              if r.get("record") == "layer_segment"
              and r.get("phase") == "vision_encoder"
              and r.get("kind") == "isolated_family_node"]
    if not events:
        raise SystemExit("no isolated_family_node timing rows found")

    per_op = defaultdict(list)
    by_shape = defaultdict(list)
    for row in events:
        src0, src1 = row["src0_name"], row["src1_name"]
        src0_ne, src1_ne, out_ne = row["src0_ne"], row["src1_ne"], row["output_ne"]
        if src0_ne[0] != src1_ne[0]:
            raise SystemExit(f"unequal reduction extents for {row['output_name']}: {src0_ne} {src1_ne}")
        k, m, n = src0_ne[0], out_ne[0], out_ne[1]
        kind = family(src0, src1)
        key = (kind, k, m, n, row["src0_dtype"], row["src1_dtype"], row["output_dtype"])
        row = dict(row)
        row["family"] = kind
        row["K"], row["M"], row["N"] = k, m, n
        row["mac"] = k * m * n
        row["seconds"] = row["elapsed_ns"] / 1e9
        by_shape[key].append(row)
        per_op[(row["output_name"], key)].append(row)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    shape_rows = []
    family_calls = defaultdict(list)
    for key, calls in by_shape.items():
        kind, k, m, n, d0, d1, dout = key
        total_s = sum(x["seconds"] for x in calls)
        total_mac = sum(x["mac"] for x in calls)
        family_calls[kind].extend(calls)
        shape_rows.append({
            "family": kind, "K": k, "M": m, "N": n,
            "src0_dtype": d0, "src1_dtype": d1, "output_dtype": dout,
            "calls_per_request": len(calls), "total_MAC": total_mac,
            "board_cpu_time_s": total_s,
            "time_per_MAC_ns": total_s * 1e9 / total_mac,
            "measured_GMAC_per_s": total_mac / total_s / 1e9,
            "median_call_ms": statistics.median(x["seconds"] for x in calls) * 1e3,
            "time_share_of_selected_ops": 0.0,
            "vision_time_share": "UNKNOWN" if args.vision_seconds is None else total_s / args.vision_seconds,
        })
    selected_s = sum(r["board_cpu_time_s"] for r in shape_rows)
    for row in shape_rows:
        row["time_share_of_selected_ops"] = row["board_cpu_time_s"] / selected_s
    shape_rows.sort(key=lambda r: -r["board_cpu_time_s"])

    shape_path = args.output_dir / "q37804_vision_family_cpu_timing.csv"
    with shape_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(shape_rows[0]))
        w.writeheader()
        w.writerows(shape_rows)

    family_rows = []
    for kind, calls in family_calls.items():
        total_s = sum(x["seconds"] for x in calls)
        total_mac = sum(x["mac"] for x in calls)
        family_rows.append({
            "family": kind,
            "shape_variants": len({(x["K"], x["M"], x["N"]) for x in calls}),
            "calls_per_request": len(calls),
            "total_MAC": total_mac,
            "board_cpu_time_s": total_s,
            "time_per_MAC_ns": total_s * 1e9 / total_mac,
            "measured_GMAC_per_s": total_mac / total_s / 1e9,
            "time_share_of_selected_ops": total_s / selected_s,
            "vision_time_share": "UNKNOWN" if args.vision_seconds is None else total_s / args.vision_seconds,
        })
    family_rows.sort(key=lambda r: -r["board_cpu_time_s"])
    family_path = args.output_dir / "q37804_vision_family_summary.csv"
    with family_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(family_rows[0]))
        w.writeheader()
        w.writerows(family_rows)

    op_rows = []
    for (output_name, key), calls in per_op.items():
        vals = [x["seconds"] * 1e3 for x in calls]
        op_rows.append({
            "family": key[0], "output_name": output_name,
            "K": key[1], "M": key[2], "N": key[3],
            "calls_per_request": len(calls),
            "total_board_cpu_time_s": sum(vals) / 1e3,
            "per_call_ms": ";".join(f"{v:.3f}" for v in vals),
        })
    op_rows.sort(key=lambda r: (r["family"], r["output_name"]))
    op_path = args.output_dir / "q37804_vision_operator_call_timing.csv"
    with op_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(op_rows[0]))
        w.writeheader()
        w.writerows(op_rows)

    print(json.dumps({
        "timed_calls": len(events), "selected_operator_seconds": selected_s,
        "vision_seconds": args.vision_seconds,
        "families_and_shapes": len(shape_rows),
        "family_summary_csv": str(family_path),
        "shape_csv": str(shape_path), "per_op_csv": str(op_path),
    }, indent=2))


if __name__ == "__main__":
    main()
