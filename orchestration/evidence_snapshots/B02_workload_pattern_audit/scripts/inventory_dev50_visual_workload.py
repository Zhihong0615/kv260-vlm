#!/usr/bin/env python3
"""Inventory already recorded TextVQA dev50 visual batch shapes without inference.

The `n_tokens_batch` values come from runtime image-encode logs. They are
post-processor observations, not a proven pre-dispatch selector interface.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "experiments/raw/textvqa_val_dev50_host_q4_cpu_round01/run.json"
DATASET = ROOT / "datasets/textvqa_v0.5.1_dev_50_seed20260923/manifest.json"
OUTPUT = ROOT / "experiments/derived/textvqa_dev50_visual_workload_inventory.json"
NOTE = ROOT / "experiments/derived/textvqa_dev50_visual_workload_inventory_ANALYSIS_NOTE.md"
TRACED_QUESTION_IDS = {37804, 37852, 38169, 38299}

BATCH_RE = re.compile(r"decoding image batch (\d+)/(\d+), n_tokens_batch = (\d+)")
DONE_RE = re.compile(r"image decoded \(batch (\d+)/(\d+)\) in (\d+) ms")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def within_root(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"path escapes project root: {relative}")
    return path


def main() -> None:
    run = json.loads(RUN.read_text())
    dataset = json.loads(DATASET.read_text())
    cases = run["cases"]
    assert len(cases) == dataset["image_count"] == len(dataset["samples"]) == 50
    dataset_by_qid = {int(row["question_id"]): row for row in dataset["samples"]}
    assert len(dataset_by_qid) == 50
    assert len({row["image_id"] for row in dataset["samples"]}) == 50

    rows = []
    for case in cases:
        qid = int(case["question_id"])
        reference = dataset_by_qid[qid]
        assert case["image_id"] == reference["image_id"]
        assert case["image_sha256"] == reference["image_sha256"]
        assert case["prediction_parse_ok"] and case["returncode"] == 0
        image = within_root(case["image"])
        log = within_root(case["raw_log"])
        assert sha256(image) == case["image_sha256"]
        with Image.open(image) as opened:
            width, height = opened.size
        content = log.read_text(errors="replace")
        batches = [tuple(map(int, match)) for match in BATCH_RE.findall(content)]
        completed = [tuple(map(int, match)) for match in DONE_RE.findall(content)]
        assert batches and len(batches) == len(completed), qid
        assert all(a == 1 and b == 1 for a, b, _ in batches), qid
        assert all(a == 1 and b == 1 for a, b, _ in completed), qid
        tokens = [item[2] for item in batches]
        rows.append({
            "question_id": qid,
            "image_id": case["image_id"],
            "image_width": width,
            "image_height": height,
            "ordered_image_batch_tokens": tokens,
            "image_batch_count": len(tokens),
            "logged_image_token_sum": sum(tokens),
            "prompt_eval_count_runtime_diagnostic": case["libllama_perf_metrics"]["prompt_eval"]["count"],
            "process_wall_seconds_descriptive_only": case["runner_wall_seconds_including_process_start_model_load_image_and_generation"],
            "already_allocator_traced": qid in TRACED_QUESTION_IDS,
            "image_sha256": sha256(image),
            "inference_log": case["raw_log"],
            "inference_log_sha256": sha256(log),
        })

    assert len(rows) == 50 and len({row["question_id"] for row in rows}) == 50
    assert TRACED_QUESTION_IDS <= {row["question_id"] for row in rows}
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row["ordered_image_batch_tokens"])].append(row)
    buckets = []
    for pattern, members in sorted(groups.items(), key=lambda item: (len(item[0]), sum(item[0]), item[0])):
        existing = sorted(row["question_id"] for row in members if row["already_allocator_traced"])
        untraced = sorted(row["question_id"] for row in members if not row["already_allocator_traced"])
        buckets.append({
            "ordered_image_batch_tokens": list(pattern),
            "image_batch_count": len(pattern),
            "logged_image_token_sum": sum(pattern),
            "request_count": len(members),
            "question_ids": sorted(row["question_id"] for row in members),
            "already_allocator_traced_question_ids": existing,
            "first_untraced_question_id": untraced[0] if untraced else None,
            "selected_for_new_pattern_probe": not existing and bool(untraced),
        })

    selected = [bucket["first_untraced_question_id"] for bucket in buckets if bucket["selected_for_new_pattern_probe"]]
    result = {
        "evidence_level": "HOST_RECORDED_LOG_INVENTORY",
        "purpose": "development-only visual-shape coverage for future host trace selection",
        "source_run": str(RUN.relative_to(ROOT)),
        "source_run_sha256": sha256(RUN),
        "source_dataset": str(DATASET.relative_to(ROOT)),
        "source_dataset_sha256": sha256(DATASET),
        "script": str(Path(__file__).resolve().relative_to(ROOT)),
        "script_sha256": sha256(Path(__file__).resolve()),
        "selection_rule": "For each exact ordered image-encode token pattern absent from the four allocator-traced development requests, choose the smallest untraced question ID. This selects development probes, not held-out evaluation data.",
        "already_allocator_traced_question_ids": sorted(TRACED_QUESTION_IDS),
        "selected_development_question_ids": selected,
        "buckets": buckets,
        "requests": sorted(rows, key=lambda row: row["question_id"]),
        "limitations": [
            "Image-encode token counts are parsed from existing logs after preprocessing; availability before the first model dispatch has not been established.",
            "One representative per pattern does not establish within-pattern timing or memory variability.",
            "The fresh-process wall includes loading, processing, and generation; output lengths vary, so this table is not a causal crop-cost comparison.",
            "TextVQA dev50 is development material only. No board, PL, held-out, or new inference measurement was performed.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")

    lines = [
        "# TextVQA dev50 recorded visual workload inventory",
        "",
        "This is a read-only reanalysis of the existing 50-request host CPU baseline. The log's ordered `n_tokens_batch` sequence is a post-processor image-encode observation, not yet a proven pre-dispatch selector feature. Request wall times include loading and generated-output differences.",
        "",
        f"Source run SHA-256: `{result['source_run_sha256']}`. Dataset manifest SHA-256: `{result['source_dataset_sha256']}`. Script SHA-256: `{result['script_sha256']}`.",
        "",
        "| Ordered image batch token counts | Requests | Existing allocator traces | First untraced development example |",
        "|---|---:|---|---:|",
    ]
    for bucket in buckets:
        pattern = ", ".join(map(str, bucket["ordered_image_batch_tokens"]))
        existing = ", ".join(map(str, bucket["already_allocator_traced_question_ids"])) or "none"
        first = bucket["first_untraced_question_id"]
        lines.append(f"| {pattern} | {bucket['request_count']} | {existing} | {first if first is not None else 'none'} |")
    lines += [
        "",
        "Deterministic additional development probes for previously unseen patterns: " + ", ".join(map(str, selected)) + ". The rule selects the smallest untraced question ID in each uncovered exact token pattern. These four cases should be rechecked for image identity and runtime metadata before any heavy timing; they do not define the final evaluation split.",
        "",
        "Seven exact patterns occurred in dev50; the four allocator-traced requests cover three patterns. An exact pattern may include different raw image dimensions. The JSON contains each request's dimensions, source log/image hashes, and runtime prompt count for audit. Runtime prompt count is descriptive and may include multimodal tokens; it is not a selector feature validated at the required boundary.",
        "",
        "No new inference, board action, or held-out data use was performed for this inventory.",
    ]
    NOTE.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
