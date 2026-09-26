#!/usr/bin/env python3
"""Generate the frozen, image-disjoint RM13 quality split from TextVQA val."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ANNOTATION_SHA256 = "4ceb5aadc1a41719d0a3e4dfdf06838bcfee1db569a9a65ee67d31c99893081d"
SEED = "rm13-textvqa-split-v1-20260926"
DEV_MANIFEST = Path(
    "/home/zhiro/research/kv260-vlm/datasets/"
    "textvqa_v0.5.1_dev_50_seed20260923/manifest.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def keyed_hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def select_image_question(rows: list[dict[str, Any]], image_id: str) -> dict[str, Any]:
    row = min(
        rows,
        key=lambda item: keyed_hash(
            f"{SEED}|question|{image_id}|{int(item['question_id'])}"
        ),
    )
    return {
        "question_id": int(row["question_id"]),
        "image_id": image_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if sha256_file(args.annotation) != ANNOTATION_SHA256:
        raise SystemExit("TextVQA annotation SHA-256 does not match the frozen source")
    if sha256_file(DEV_MANIFEST) != (
        "62c32317029e40895ffd8e476e8a845416dac9d1d9490dfd6efb5f28a4374962"
    ):
        raise SystemExit("existing development manifest SHA-256 changed")

    annotation = json.loads(args.annotation.read_text(encoding="utf-8"))
    if (annotation.get("dataset_name"), annotation.get("dataset_version"),
            annotation.get("dataset_type")) != ("textvqa", "0.5.1", "val"):
        raise SystemExit("unexpected TextVQA annotation identity")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in annotation["data"]:
        groups[str(row["image_id"])].append(row)

    dev_manifest = json.loads(DEV_MANIFEST.read_text(encoding="utf-8"))
    dev = [
        {"question_id": int(row["question_id"]), "image_id": row["image_id"]}
        for row in dev_manifest["samples"]
    ]
    if len(dev) != 50 or len({row["question_id"] for row in dev}) != 50:
        raise SystemExit("expected 50 unique development question IDs")
    required_dev_qids = {37804, 38299, 35419}
    if not required_dev_qids.issubset({row["question_id"] for row in dev}):
        raise SystemExit("previously reused QIDs must remain development only")
    dev_images = {row["image_id"] for row in dev}
    if len(dev_images) != 50:
        raise SystemExit("development QIDs must use distinct image IDs")

    available = sorted(set(groups) - dev_images)
    if len(available) < 220:
        raise SystemExit("not enough unique image IDs remain for calibration and final sets")
    calibration_images = sorted(
        available,
        key=lambda image_id: keyed_hash(f"{SEED}|calibration|{image_id}"),
    )[:20]
    calibration_set = set(calibration_images)
    final_images = sorted(
        (image_id for image_id in available if image_id not in calibration_set),
        key=lambda image_id: keyed_hash(f"{SEED}|final|{image_id}"),
    )[:200]

    calibration = [select_image_question(groups[image_id], image_id)
                   for image_id in calibration_images]
    final_test = [select_image_question(groups[image_id], image_id)
                  for image_id in final_images]

    all_splits = [dev, calibration, final_test]
    qid_sets = [{row["question_id"] for row in split} for split in all_splits]
    image_sets = [{row["image_id"] for row in split} for split in all_splits]
    if any(qid_sets[i] & qid_sets[j] for i in range(3) for j in range(i + 1, 3)):
        raise SystemExit("question ID overlap across splits")
    if any(image_sets[i] & image_sets[j] for i in range(3) for j in range(i + 1, 3)):
        raise SystemExit("image ID overlap across splits")
    if len(final_test) != 200 or len(calibration) != 20:
        raise SystemExit("unexpected held-out or calibration split size")

    output = {
        "contract_id": "rm13-textvqa-quality-split-v1",
        "created_from": "experiments/rm13/make_quality_split.py",
        "dataset": {
            "name": "TextVQA",
            "version": "0.5.1",
            "source_split": "validation",
            "annotation_url": "https://dl.fbaipublicfiles.com/textvqa/data/TextVQA_0.5.1_val.json",
            "annotation_sha256": ANNOTATION_SHA256,
            "license": "CC BY 4.0",
        },
        "selection": {
            "seed": SEED,
            "unit": "unique image ID",
            "question_per_image": "lowest SHA-256 of seed|question|image_id|question_id",
            "calibration_image_order": "ascending SHA-256 of seed|calibration|image_id",
            "final_image_order": "ascending SHA-256 of seed|final|image_id after removing development and calibration images",
            "development_source": str(DEV_MANIFEST),
            "development_manifest_sha256": sha256_file(DEV_MANIFEST),
            "development_image_ids_excluded_from_calibration_and_final": True,
        },
        "purpose_and_limit": (
            "The existing 50-QID profiling subset is development only. Calibration and final sets "
            "are sampled from the full TextVQA validation annotations with unique image IDs and "
            "are disjoint from each other and the profiling subset. This is a held-out validation "
            "screen, not a claim on the official TextVQA test split or population-wide accuracy."
        ),
        "splits": {
            "development": dev,
            "calibration": calibration,
            "final_test": final_test,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "development_qids": len(dev),
        "calibration_qids": len(calibration),
        "final_test_qids": len(final_test),
        "final_test_first_10": [row["question_id"] for row in final_test[:10]],
        "split_sha256": sha256_file(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
