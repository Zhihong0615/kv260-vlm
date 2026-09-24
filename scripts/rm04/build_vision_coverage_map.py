#!/usr/bin/env python3
"""Create a qid-specific shape/call/MAC coverage map for the Dynamic8 datapath."""
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def family(weight: str, output: str) -> str:
    s = (weight + " " + output).lower()
    if "ffn_up" in s:
        return "FFN up"
    if "ffn_down" in s:
        return "FFN down"
    if any(x in s for x in ("attn_q", "attn_k", "attn_v", "attn_out", "qkv")):
        return "Attention projection"
    if "merger" in s or "mm." in s or "projector" in s:
        return "Projector / merge"
    return "Other / patch embedding"


def classify(k, m, n, in0, in1, out, mac, total):
    if in0 == "f16" and in1 == "f32" and out == "f32" and (k, m, n) == (1152, 4304, 1120):
        return "directly supported"
    if mac / total < 0.002 and n <= 70:
        return "not worth offloading"
    if in0 != "f16" or in1 != "f32" or out != "f32" or k > 4608 or m > 4608:
        return "requires different datapath"
    return "supported with parameter change"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--qid", type=int, default=37804)
    ap.add_argument("--board-vision-seconds", type=float, default=590.348,
                    help="measured QID37804 4-thread vision timer for MAC-proportional proxy only")
    args = ap.parse_args()
    doc = json.loads(args.input.read_text())
    run = next(r for r in doc["runs"] if r["question_id"] == args.qid)
    total = run["trace_cases"]["02"]["phase_nominal_mac_pairs"]["vision_encoder"]

    grouped = defaultdict(lambda: {"calls": 0, "mac": 0, "weights": set(), "outputs": set()})
    for row in run["exact_inventory"]:
        if row["phase"] != "vision_encoder":
            continue
        k, m = row["src0"]["ne"][:2]
        n = row["src1"]["ne"][1]
        in0, in1, out = row["src0"]["dtype"], row["src1"]["dtype"], row["output"]["dtype"]
        calls = row.get("calls", 1)
        mac = k * m * n * calls
        fam = family(row["src0"]["name"], row["output"]["name"])
        key = (fam, k, m, n, in0, in1, out)
        grouped[key]["calls"] += calls
        grouped[key]["mac"] += mac
        grouped[key]["weights"].add(row["src0"]["name"])
        grouped[key]["outputs"].add(row["output"]["name"])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    totals = defaultdict(int)
    for (fam, k, m, n, in0, in1, out), agg in grouped.items():
        category = classify(k, m, n, in0, in1, out, agg["mac"], total)
        totals[category] += agg["mac"]
        rows.append({
            "qid": args.qid, "family": fam, "representative_weights": ";".join(sorted(agg["weights"])),
            "representative_outputs": ";".join(sorted(agg["outputs"])),
            "K": k, "M": m, "N": n, "input0_dtype": in0, "input1_dtype": in1,
            "output_dtype": out, "graph_node_calls": agg["calls"], "nominal_MAC": agg["mac"],
            "vision_MAC_share": agg["mac"] / total,
            "board_CPU_time_MAC_proxy_seconds": args.board_vision_seconds * agg["mac"] / total,
            "coverage_class": category,
            "CPU_time_proxy_status": "MAC-proportional estimate; family time not isolated",
        })
    rows.sort(key=lambda r: (-r["nominal_MAC"], r["family"], r["K"], r["M"], r["N"]))
    csv_path = args.output_dir / f"vision_operator_coverage_q{args.qid}.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    trace_counts = run["trace_cases"]["02"]
    dtype_calls = trace_counts["phase_dtype_pair_calls"]["vision_encoder"]
    report = {
        "qid": args.qid,
        "source_inventory": str(args.input),
        "source_sha256": sha(args.input),
        "trace_matmul_observations": trace_counts["phase_matmul_node_observations"]["vision_encoder"],
        "dtype_pair_node_observations": dtype_calls,
        "vision_nominal_MAC": total,
        "board_vision_seconds": args.board_vision_seconds,
        "board_vision_timer_is_request_level_not_family_isolated": True,
        "coverage_by_class": {
            k: {"nominal_MAC": v, "share": v / total,
                "CPU_time_MAC_proxy_seconds": args.board_vision_seconds * v / total}
            for k, v in totals.items()
        },
        "shape_rows": len(rows),
        "csv": csv_path.name,
    }
    json_path = args.output_dir / f"vision_operator_coverage_q{args.qid}.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n")

    lines = [f"# Vision operator coverage map — QID {args.qid}", "",
             f"Input inventory SHA-256: `{report['source_sha256']}`.",
             f"Observed {report['trace_matmul_observations']} vision MUL_MAT graph nodes; dtype split: `{json.dumps(dtype_calls, sort_keys=True)}`.",
             f"Nominal vision work: {total / 1e12:.6f} TMAC. Per-family CPU seconds below are only a proportional proxy from the measured {args.board_vision_seconds:.3f}s board vision timer; no family was timed independently.", "",
             "Dynamic8’s direct point is F16×F32→F32, K=1152, M=4304, N=1120 with contiguous GGML strides. Compile-time shape changes retain the same arithmetic datapath but need their own synthesis and numeric checks.", "",
             "| Class | MAC share | MAC-proportional board CPU proxy |", "|---|---:|---:|"]
    for cat, val in sorted(report["coverage_by_class"].items(), key=lambda kv: -kv[1]["nominal_MAC"]):
        lines.append(f"| {cat} | {val['share']:.3%} | {val['CPU_time_MAC_proxy_seconds']:.2f}s |")
    lines += ["", "The CSV provides shape, dtype, family, call count, MAC, proxy and class for each aggregated shape family.", ""]
    (args.output_dir / f"vision_operator_coverage_q{args.qid}.md").write_text("\n".join(lines))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
