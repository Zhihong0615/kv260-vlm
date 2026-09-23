#!/usr/bin/env python3
"""Summarize only saved graph and media-batch metadata from the B03 traces."""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "experiments/raw/textvqa_selected_optrace_B03/run.json"
OUTPUT = ROOT / "experiments/derived/selected_qid_optrace_B03_group_shapes.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite existing derived summary: {OUTPUT}")
    run = json.loads(RUN.read_text(encoding="utf-8"))
    if run.get("status") != "PASS" or run.get("answer_labels_read") is not False:
        raise SystemExit("B03 run is not a clean PASS or answer-label boundary is missing")
    request_summaries = []
    for case in run["cases"]:
        trace_path = ROOT / case["trace_file"]
        groups = {
            row["group"]: {
                "group": row["group"],
                "chunk_index": row["chunk_index"],
                "chunks_added": row["chunks_added"],
                "chunks_total": row["chunks_total"],
                "vision_node_count": 0,
                "im2col_shapes": set(),
                "mul_mat_shapes": Counter(),
            }
            for row in case["encoded_media_batch_records"]
        }
        request_mul_mat_shapes = set()
        with gzip.open(trace_path, "rt", encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if row.get("record") != "node" or row.get("phase") != "vision_encoder":
                    continue
                group_id = row["group"]
                if group_id not in groups:
                    raise SystemExit(f"qid {case['question_id']} has node with unknown media group {group_id}")
                group = groups[group_id]
                group["vision_node_count"] += 1
                if row["op"] == "IM2COL":
                    input_raw = next((tensor for tensor in row["inputs"] if tensor["name"] == "inp_raw"), None)
                    group["im2col_shapes"].add(json.dumps({
                        "output_dtype": row["output"]["dtype"],
                        "output_ne": row["output"]["ne"],
                        "output_nb": row["output"]["nb"],
                        "input_raw_dtype": input_raw["dtype"] if input_raw else None,
                        "input_raw_ne": input_raw["ne"] if input_raw else None,
                        "input_raw_nb": input_raw["nb"] if input_raw else None,
                    }, sort_keys=True, separators=(",", ":")))
                if row["op"] == "MUL_MAT":
                    shape = json.dumps({
                        "output_dtype": row["output"]["dtype"],
                        "output_ne": row["output"]["ne"],
                        "output_nb": row["output"]["nb"],
                        "inputs": [{"dtype": tensor["dtype"], "ne": tensor["ne"], "nb": tensor["nb"]} for tensor in row["inputs"]],
                    }, sort_keys=True, separators=(",", ":"))
                    group["mul_mat_shapes"][shape] += 1
                    request_mul_mat_shapes.add(shape)

        ordered_groups = []
        for group_id in sorted(groups):
            group = groups[group_id]
            shape_rows = [json.loads(shape) for shape in sorted(group["im2col_shapes"])]
            shape_rows = [{
                **shape,
                "input_width": shape["input_raw_ne"][0] if shape["input_raw_ne"] else None,
                "input_height": shape["input_raw_ne"][1] if shape["input_raw_ne"] else None,
            } for shape in shape_rows]
            ordered_groups.append({
                "group": group["group"],
                "chunk_index": group["chunk_index"],
                "chunks_added": group["chunks_added"],
                "chunks_total": group["chunks_total"],
                "vision_node_count": group["vision_node_count"],
                "unique_im2col_shapes": shape_rows,
                "unique_vision_mul_mat_shape_count": len(group["mul_mat_shapes"]),
                "vision_mul_mat_shape_set_sha256": hashlib.sha256("\n".join(sorted(group["mul_mat_shapes"])).encode()).hexdigest(),
            })
        request_summaries.append({
            "question_id": case["question_id"],
            "image_id": case["image_id"],
            "image_size": case["image_size"],
            "image_sha256": case["image_sha256"],
            "n_tokens_batch_from_B02": case["n_tokens_batch_from_B02"],
            "encoded_media_batch_count": len(ordered_groups),
            "token_batch_count_matches_media_batch_count": len(case["n_tokens_batch_from_B02"]) == len(ordered_groups),
            "ordered_media_batches": ordered_groups,
            "unique_request_vision_im2col_shape_count": len({
                json.dumps(shape, sort_keys=True, separators=(",", ":"))
                for group in ordered_groups for shape in group["unique_im2col_shapes"]
            }),
            "unique_request_vision_mul_mat_shape_count": len(request_mul_mat_shapes),
        })
    result = {
        "evidence_level": "DERIVED_HOST_CPU_MEDIA_BATCH_TO_GRAPH_SHAPE_SUMMARY",
        "source_run_sha256": sha256(RUN),
        "source_trace_sha256_compressed": {
            str(case["question_id"]): case["trace_sha256_compressed"] for case in run["cases"]
        },
        "request_count": len(request_summaries),
        "all_token_batch_counts_match_media_batch_counts": all(
            case["token_batch_count_matches_media_batch_count"] for case in request_summaries
        ),
        "requests": request_summaries,
        "interpretation": [
            "Each media_batch group is one mtmd_batch_encode call and is ordered by the media chunk index in the CLI graph; it is not a crop identity.",
            "The equal counts align B02's ordered n_tokens_batch records with the traced media batches, but this summary does not claim a crop-level mapping.",
            "The IM2COL input/output shapes show per-batch preprocessing-dependent vision graph shape variation for the selected requests.",
            "These are CPU logical graph shapes. They reveal neither K26 backend choice nor physical memory traffic, timing, or resource occupancy.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "all_token_batch_counts_match_media_batch_counts": result["all_token_batch_counts_match_media_batch_counts"],
        "requests": [{
            "qid": r["question_id"],
            "media_batches": r["encoded_media_batch_count"],
            "unique_vision_im2col_shapes": r["unique_request_vision_im2col_shape_count"],
            "unique_vision_mul_mat_shapes": r["unique_request_vision_mul_mat_shape_count"],
        } for r in request_summaries],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
