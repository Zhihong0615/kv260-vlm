#!/usr/bin/env python3
"""Score an RM13 TextVQA campaign with the vendored MMF evaluator and gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GATE_PATH = ROOT / "experiments/rm13/quality_gate.json"
SPLIT_PATH = ROOT / "experiments/rm13/quality_split_manifest.json"
VENDOR_PATH = ROOT / "experiments/rm13/vendor/m4c_evaluators.py"
sys.path.insert(0, str(VENDOR_PATH.parent))
from m4c_evaluators import TextVQAAccuracyEvaluator  # noqa: E402


VARIANTS = [
    "original",
    "W8A8_up_only",
    "W8A8_down_only",
    "W8A8_both",
    "W4A8_up_only",
    "W4A8_down_only",
    "W4A8_both",
]
GATE_SHA256 = "3fc90a42b75b49198db6e90ea38809fc157ce657834be2cf1b12c01baeae0648"
SPLIT_SHA256 = "5b798932b1ad08c85c6328cceab046f191e9dfbbc0a2df01f971f523eeb2e7b6"
VENDOR_SHA256 = "e10a99e15c4658f8d0d83a05cc536c835922e701171fce0016718bec021b8c0a"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def empirical_percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(probability * len(ordered)))
    return ordered[rank - 1]


def paired_bootstrap(
    deltas: list[float],
    replicates: int,
    seed: int,
    low_probability: float,
    high_probability: float,
) -> dict:
    if not deltas:
        raise ValueError("cannot bootstrap an empty paired sample")
    rng = random.Random(seed)
    size = len(deltas)
    means = []
    for _ in range(replicates):
        means.append(sum(deltas[rng.randrange(size)] for _ in range(size)) / size)
    return {
        "replicates": replicates,
        "seed": seed,
        "unit": "paired per-QID score delta; sample QID indices with replacement",
        "interval_method": "two-sided percentile, empirical nearest-rank order statistics",
        "confidence_level": 0.95,
        "lower": empirical_percentile(means, low_probability),
        "upper": empirical_percentile(means, high_probability),
        "bootstrap_mean_delta": statistics.mean(means),
    }


def read_campaign(campaign_dir: Path) -> tuple[dict, list[dict], str]:
    metadata_path = campaign_dir / "campaign.json"
    journal_path = campaign_dir / "events.jsonl"
    if not metadata_path.is_file() or not journal_path.is_file():
        raise SystemExit(f"campaign metadata or append-only journal missing: {campaign_dir}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    records = []
    seen: set[tuple[str, int]] = set()
    with journal_path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise SystemExit(f"invalid journal JSON at {journal_path}:{line_number}: {error}") from error
            if event.get("event") != "case_completed":
                continue
            key = (event.get("variant"), int(event["question_id"]))
            if key in seen:
                raise SystemExit(f"campaign journal contains duplicate completed case: {key}")
            seen.add(key)
            records.append(event)
    return metadata, records, sha256_file(journal_path)


def normalize(evaluator: TextVQAAccuracyEvaluator, text: str) -> str:
    return evaluator.answer_processor(text)


def score_case(evaluator: TextVQAAccuracyEvaluator, record: dict) -> dict:
    failed = record.get("returncode") != 0 or not record.get("prediction_parse_ok") or not record.get("prediction", "").strip()
    prediction = "" if failed else record["prediction"]
    references = record.get("reference_answers")
    if not isinstance(references, list) or len(references) != 10:
        raise SystemExit(f"QID {record.get('question_id')} does not have exactly 10 human answers")
    score = evaluator.eval_pred_list([{"pred_answer": prediction, "gt_answers": references}])
    flags = record.get("unusual_output_flags", {})
    return {
        "question_id": int(record["question_id"]),
        "image_id": str(record["image_id"]),
        "question": record["question"],
        "prediction": record.get("prediction", ""),
        "score_prediction_used": prediction,
        "normalized_prediction": normalize(evaluator, prediction),
        "textvqa_soft_accuracy": score,
        "failed_or_unparsed": failed,
        "returncode": record.get("returncode"),
        "prediction_parse_ok": bool(record.get("prediction_parse_ok")),
        "unusual_output_flags": flags,
        "reference_answers": references,
        "raw_log": record.get("raw_log"),
        "attempt": record.get("attempt"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--raw-root", type=Path, default=ROOT / "experiments/rm13/data/raw")
    parser.add_argument("--output-root", type=Path, default=ROOT / "experiments/rm13/data/derived")
    parser.add_argument("--output", type=Path, help="optional new output path; existing files are never overwritten")
    args = parser.parse_args()

    if sha256_file(GATE_PATH) != GATE_SHA256 or sha256_file(SPLIT_PATH) != SPLIT_SHA256:
        raise SystemExit("frozen RM13 quality gate or split manifest SHA-256 mismatch")
    if sha256_file(VENDOR_PATH) != VENDOR_SHA256:
        raise SystemExit("vendored official MMF evaluator SHA-256 mismatch")
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    bootstrap_config = gate["bootstrap"]
    campaign_dir = args.raw_root.resolve() / args.run_id
    metadata, records, journal_hash = read_campaign(campaign_dir)
    config = metadata.get("configuration", {})
    split = config.get("split")
    qids = [int(qid) for qid in config.get("selected_question_ids", [])]
    if split not in {"calibration", "final_test", "development"} or not qids:
        raise SystemExit("campaign configuration has no recognized split or selected QIDs")
    expected_count = {"calibration": 20, "final_test": 200}.get(split)
    if expected_count is not None and len(qids) != expected_count:
        raise SystemExit(f"campaign metadata selects {len(qids)} QIDs for frozen split {split}, expected {expected_count}")
    if config.get("quality_gate_sha256") != GATE_SHA256 or config.get("split_manifest_sha256") != SPLIT_SHA256:
        raise SystemExit("campaign was not run against the frozen RM13 gate and split")
    expected_keys = {(variant, qid) for variant in VARIANTS for qid in qids}
    actual_keys = {(row.get("variant"), int(row["question_id"])) for row in records}
    if actual_keys - expected_keys:
        raise SystemExit("raw campaign includes an unexpected variant or QID")
    missing = sorted(expected_keys - actual_keys)
    if missing:
        raise SystemExit(f"campaign is incomplete; {len(missing)} variant/QID cases are missing (first: {missing[:3]})")

    by_variant: dict[str, dict[int, dict]] = {variant: {} for variant in VARIANTS}
    raw_by_variant: dict[str, dict[int, dict]] = {variant: {} for variant in VARIANTS}
    evaluator = TextVQAAccuracyEvaluator()
    for record in records:
        variant = record["variant"]
        if record.get("variant_environment_value") != variant:
            raise SystemExit(f"QID {record['question_id']} lacks matching RM13_QVARIANT provenance")
        qid = int(record["question_id"])
        if record.get("question_id_environment_value") != str(qid):
            raise SystemExit(f"QID {qid} lacks matching RM13_QID provenance")
        raw_by_variant[variant][qid] = record
        by_variant[variant][qid] = score_case(evaluator, record)

    runtime_application = {}
    runtime_application_complete = True
    for variant in VARIANTS:
        if variant == "original":
            expected_ops: list[str] = []
        elif variant.endswith("_up_only"):
            expected_ops = ["ffn_up"]
        elif variant.endswith("_down_only"):
            expected_ops = ["ffn_down"]
        else:
            expected_ops = ["ffn_up", "ffn_down"]
        applied_counts = {op: 0 for op in ("ffn_up", "ffn_down")}
        fallback_counts = {op: 0 for op in ("ffn_up", "ffn_down")}
        fallback_reasons: dict[str, int] = {}
        case_counts = {"with_applied_marker": 0, "with_fallback_marker": 0}
        missing_expected_operator_qids = {op: [] for op in expected_ops}
        mismatched_marker_identity_count = 0
        for qid in qids:
            record = raw_by_variant[variant][qid]
            applied = record.get("q_runtime_marker_fields", {}).get("applied", [])
            fallbacks = record.get("q_runtime_marker_fields", {}).get("fallback", [])
            if applied:
                case_counts["with_applied_marker"] += 1
            if fallbacks:
                case_counts["with_fallback_marker"] += 1
            applied_seen = set()
            for marker in applied:
                if marker.get("qid") != str(qid) or marker.get("variant") != variant:
                    mismatched_marker_identity_count += 1
                op = re.sub(r"-\d+$", "", marker.get("op", ""))
                if op in applied_counts:
                    applied_counts[op] += 1
                    applied_seen.add(op)
            for marker in fallbacks:
                if marker.get("qid") != str(qid) or marker.get("variant") != variant:
                    mismatched_marker_identity_count += 1
                op = re.sub(r"-\d+$", "", marker.get("op", ""))
                if op in fallback_counts:
                    fallback_counts[op] += 1
                reason = marker.get("reason", "unspecified")
                fallback_reasons[reason] = fallback_reasons.get(reason, 0) + 1
            for op in expected_ops:
                if op not in applied_seen:
                    missing_expected_operator_qids[op].append(qid)
        has_expected_application = all(not missing_expected_operator_qids[op] for op in expected_ops)
        runtime_application_complete &= has_expected_application and mismatched_marker_identity_count == 0
        runtime_application[variant] = {
            "expected_quantized_operators": expected_ops,
            "applied_invocation_count_by_operator": applied_counts,
            "fallback_invocation_count_by_operator": fallback_counts,
            "fallback_reason_counts": fallback_reasons,
            "qids_with_applied_markers": case_counts["with_applied_marker"],
            "qids_with_fallback_markers": case_counts["with_fallback_marker"],
            "qids_missing_expected_operator_application": missing_expected_operator_qids,
            "marker_identity_mismatch_count": mismatched_marker_identity_count,
            "application_evidence_complete": has_expected_application and mismatched_marker_identity_count == 0,
        }

    ordered_qids = sorted(qids)
    scores = {
        variant: [by_variant[variant][qid] for qid in ordered_qids]
        for variant in VARIANTS
    }
    original = scores["original"]
    by_variant_qid = {variant: by_variant[variant] for variant in VARIANTS}
    original_failure_qids = [qid for qid in ordered_qids if by_variant_qid["original"][qid]["failed_or_unparsed"]]
    comparisons: dict[str, dict] = {}
    all_quantized_no_additional_failures = True
    for variant in VARIANTS[1:]:
        paired_deltas = [
            by_variant_qid[variant][qid]["textvqa_soft_accuracy"]
            - by_variant_qid["original"][qid]["textvqa_soft_accuracy"]
            for qid in ordered_qids
        ]
        additional_failure_qids = [
            qid for qid in ordered_qids
            if by_variant_qid[variant][qid]["failed_or_unparsed"]
            and not by_variant_qid["original"][qid]["failed_or_unparsed"]
        ]
        all_quantized_no_additional_failures &= not additional_failure_qids
        bootstrap = paired_bootstrap(
            paired_deltas,
            int(bootstrap_config["replicates"]),
            int(bootstrap_config["seed"]),
            0.025,
            0.975,
        )
        mean_delta = statistics.mean(paired_deltas)
        changed = []
        review_queue = []
        for qid in ordered_qids:
            base = by_variant_qid["original"][qid]
            candidate = by_variant_qid[variant][qid]
            score_drop = base["textvqa_soft_accuracy"] - candidate["textvqa_soft_accuracy"]
            if (
                candidate["normalized_prediction"] != base["normalized_prediction"]
                or candidate["textvqa_soft_accuracy"] != base["textvqa_soft_accuracy"]
            ):
                changed.append({
                    "question_id": qid,
                    "image_id": candidate["image_id"],
                    "original_prediction": base["prediction"],
                    "quantized_prediction": candidate["prediction"],
                    "original_normalized_answer": base["normalized_prediction"],
                    "quantized_normalized_answer": candidate["normalized_prediction"],
                    "original_score": base["textvqa_soft_accuracy"],
                    "quantized_score": candidate["textvqa_soft_accuracy"],
                })
            if variant == "W4A8_both" and (candidate["failed_or_unparsed"] and not base["failed_or_unparsed"] or score_drop >= 0.3):
                suggested = []
                if candidate["failed_or_unparsed"]:
                    suggested.append("no-output/parser")
                if candidate["unusual_output_flags"].get("three_repeats_of_identical_token_sequence_at_least_three_tokens"):
                    suggested.append("repetition/noise")
                if not suggested:
                    suggested = ["OCR/perception", "semantic error"]
                review_queue.append({
                    "question_id": qid,
                    "image_id": candidate["image_id"],
                    "score_drop": score_drop,
                    "original_prediction": base["prediction"],
                    "quantized_prediction": candidate["prediction"],
                    "original_normalized_answer": base["normalized_prediction"],
                    "quantized_normalized_answer": candidate["normalized_prediction"],
                    "original_score": base["textvqa_soft_accuracy"],
                    "quantized_score": candidate["textvqa_soft_accuracy"],
                    "suggested_categories_for_manual_review": suggested,
                    "manual_category": None,
                    "manual_review_status": "pending",
                })

        comparison = {
            "variant": variant,
            "sample_count": len(ordered_qids),
            "mean_original_accuracy": statistics.mean(row["textvqa_soft_accuracy"] for row in original),
            "mean_quantized_accuracy": statistics.mean(row["textvqa_soft_accuracy"] for row in scores[variant]),
            "mean_paired_delta_quantized_minus_original": mean_delta,
            "mean_accuracy_drop_original_minus_quantized": -mean_delta,
            "paired_bootstrap_95_percent_interval_for_delta": bootstrap,
            "additional_hard_failure_count": len(additional_failure_qids),
            "additional_hard_failure_qids": additional_failure_qids,
            "original_hard_failure_qids": original_failure_qids,
            "changed_normalized_answer_or_soft_score_count": len(changed),
            "changed_normalized_answer_or_soft_score": changed,
            "representative_failure_review_queue": review_queue,
            "mean_score": statistics.mean(row["textvqa_soft_accuracy"] for row in scores[variant]),
        }
        comparisons[variant] = comparison

    quality_budget = gate["quality_budget"]
    primary = comparisons["W4A8_both"]
    primary_budget = quality_budget["primary_W4A8_both"]
    primary["numeric_gate_pass"] = (
        primary["mean_accuracy_drop_original_minus_quantized"] <= primary_budget["max_allowed_mean_accuracy_drop"]
        and primary["paired_bootstrap_95_percent_interval_for_delta"]["lower"]
        >= primary_budget["minimum_bootstrap_95_percent_interval_lower_bound"]
        and primary["additional_hard_failure_count"] == 0
    )
    reference = comparisons["W8A8_both"]
    reference_budget = quality_budget["reference_W8A8_both"]
    reference["numeric_gate_pass"] = (
        reference["mean_accuracy_drop_original_minus_quantized"] <= reference_budget["max_allowed_mean_accuracy_drop"]
        and reference["paired_bootstrap_95_percent_interval_for_delta"]["lower"]
        >= reference_budget["minimum_bootstrap_95_percent_interval_lower_bound"]
        and reference["additional_hard_failure_count"] == 0
    )
    representative_review_count = len(primary["representative_failure_review_queue"])
    if split == "final_test":
        if not runtime_application_complete:
            quality_status = "INCONCLUSIVE_RUNTIME_APPLICATION_EVIDENCE"
        elif not primary["numeric_gate_pass"] or not reference["numeric_gate_pass"] or not all_quantized_no_additional_failures:
            quality_status = "FAIL"
        elif representative_review_count:
            quality_status = "PENDING_REPRESENTATIVE_REVIEW"
        else:
            quality_status = "PASS"
    else:
        quality_status = "DEVELOPMENT_OR_CALIBRATION_DIAGNOSTIC_ONLY"

    details = []
    for qid in ordered_qids:
        details.append({
            "question_id": qid,
            "image_id": by_variant_qid["original"][qid]["image_id"],
            "variants": {variant: by_variant_qid[variant][qid] for variant in VARIANTS},
        })
    output = {
        "analysis_created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "raw_campaign_directory": str(campaign_dir),
        "campaign_metadata_sha256": sha256_file(campaign_dir / "campaign.json"),
        "raw_events_jsonl_sha256": journal_hash,
        "quality_gate_sha256": GATE_SHA256,
        "quality_split_manifest_sha256": SPLIT_SHA256,
        "vendored_evaluator": {
            "name": "MMF TextVQAAccuracyEvaluator / EvalAIAnswerProcessor",
            "source_path": "experiments/rm13/vendor/m4c_evaluators.py",
            "source_sha256": VENDOR_SHA256,
            "upstream_commit": gate["scoring"]["upstream_commit"],
            "metric": gate["scoring"]["metric"],
            "consensus_rule": gate["scoring"]["consensus_rule"],
            "failed_or_unparsed_answer_scored_as_empty_string": True,
        },
        "split": split,
        "split_sample_count": len(qids),
        "question_ids_sorted": ordered_qids,
        "original_failed_or_unparsed_count": len(original_failure_qids),
        "all_quantized_variants_have_no_additional_hard_failures": all_quantized_no_additional_failures,
        "all_expected_runtime_operators_applied_for_every_quantized_variant_qid": runtime_application_complete,
        "runtime_application_evidence_by_variant": runtime_application,
        "quality_status": quality_status,
        "representative_review_status": "pending" if representative_review_count else "not_required_by_review_queue",
        "representative_review_count": representative_review_count,
        "bootstrap": {
            **bootstrap_config,
            "implementation": "Python random.Random seeded from gate; paired row indices sampled with replacement; percentile nearest-rank empirical order statistics",
        },
        "comparisons": comparisons,
        "per_question_detail": details,
    }
    output_path = args.output.resolve() if args.output else args.output_root.resolve() / f"{args.run_id}_scored.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("x", encoding="utf-8") as stream:
            json.dump(output, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
    except FileExistsError as error:
        raise SystemExit(f"refusing to overwrite derived score: {output_path}") from error
    print(json.dumps({
        "run_id": args.run_id,
        "split": split,
        "n": len(qids),
        "quality_status": quality_status,
        "W4A8_both_accuracy_drop": primary["mean_accuracy_drop_original_minus_quantized"],
        "W4A8_both_ci": primary["paired_bootstrap_95_percent_interval_for_delta"],
        "W4A8_both_additional_hard_failures": primary["additional_hard_failure_count"],
        "W4A8_both_manual_review_items": representative_review_count,
        "derived": str(output_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
