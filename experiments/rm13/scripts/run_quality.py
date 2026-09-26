#!/usr/bin/env python3
"""Run the frozen RM13 TextVQA configurations as an append-only campaign.

The campaign is resumable: completed (configuration, QID) pairs are skipped and
each process attempt is journaled before launch. Final-test inference requires
the explicit --final-test-approved release switch.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GATE_PATH = ROOT / "experiments/rm13/quality_gate.json"
SPLIT_PATH = ROOT / "experiments/rm13/quality_split_manifest.json"
CONTRACT_PATH = ROOT / "experiments/rm13/quantization_contract.json"
DEFAULT_DATASET_MANIFEST = ROOT / "experiments/rm13/data/textvqa_v0.5.1_calibration20_final200/manifest.json"
DEFAULT_OUTPUT_ROOT = ROOT / "experiments/rm13/data/raw"
DEFAULT_MODEL = Path("/home/zhiro/research/kv260-vlm/models/gguf/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf")
DEFAULT_MMPROJ = Path("/home/zhiro/research/kv260-vlm/models/gguf/mmproj-MiniCPM-V-4.6-f16.gguf")
VARIANTS = [
    "original",
    "W8A8_up_only",
    "W8A8_down_only",
    "W8A8_both",
    "W4A8_up_only",
    "W4A8_down_only",
    "W4A8_both",
]
RUN_PRIORITY = [
    "original",
    "W4A8_both",
    "W8A8_both",
    "W8A8_up_only",
    "W8A8_down_only",
    "W4A8_up_only",
    "W4A8_down_only",
]
PROMPT_TEMPLATE = (
    "Answer the following question based only on the image. Give a short, direct answer.\n"
    "Question: {question}\nAnswer:"
)
GENERATION = {
    "compute_threads": 8,
    "batch_threads": 8,
    "context_tokens": 4096,
    "max_generated_tokens": 48,
    "seed": 42,
    "temperature": 0,
    "top_p": 1,
    "top_k": 0,
    "device": "none",
    "gpu_layers": 0,
    "mmproj_offload": False,
    "warmup": False,
    "perf": True,
    "log_verbosity": 4,
}
PARSER_DESCRIPTION = "text between final timestamped log line before first libllama perf summary and that summary"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_dependency_manifest(cli: Path, env: dict[str, str]) -> dict:
    completed = subprocess.run(
        ["ldd", str(cli)], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
    )
    if completed.returncode != 0:
        raise SystemExit(f"ldd failed for pinned CLI: {completed.stdout.strip()}")
    dependencies = {}
    for line in completed.stdout.splitlines():
        match = re.match(r"\s*(\S+)\s+=>\s+(\S+)", line)
        if not match:
            continue
        soname, target = match.groups()
        if target == "not":
            raise SystemExit(f"pinned CLI has an unresolved shared library: {line.strip()}")
        if not any(name in soname for name in ("ggml", "llama", "mtmd")):
            continue
        resolved = Path(target).resolve()
        if not resolved.is_file():
            raise SystemExit(f"pinned CLI dependency is not a regular file: {resolved}")
        dependencies[soname] = {"resolved_path": str(resolved), "sha256": sha256_file(resolved)}
    cpu_dependencies = [name for name in dependencies if name.startswith("libggml-cpu.so")]
    if not cpu_dependencies:
        raise SystemExit("pinned CLI did not resolve the RM13 libggml-cpu shared library")
    stable_ldd = "\n".join(
        re.sub(r"\s+\(0x[0-9a-fA-F]+\)$", "", line)
        for line in completed.stdout.splitlines()
    ) + "\n"
    return {"ldd_output": stable_ldd, "relevant_shared_libraries": dependencies}


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def append_jsonl(path: Path, record: dict) -> None:
    encoded = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def load_events(path: Path) -> tuple[set[tuple[str, int]], dict[str, list[dict]]]:
    complete: set[tuple[str, int]] = set()
    attempts: dict[str, list[dict]] = {}
    if not path.exists():
        return complete, attempts
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise SystemExit(f"invalid append-only journal at {path}:{line_number}: {error}") from error
            if event.get("event") == "attempt_started":
                attempts.setdefault(event["case_key"], []).append(event)
            elif event.get("event") == "case_completed":
                key = (event["variant"], int(event["question_id"]))
                if key in complete:
                    raise SystemExit(f"duplicate completed case already exists in journal: {key}")
                complete.add(key)
            else:
                raise SystemExit(f"unrecognized journal event at {path}:{line_number}")
    return complete, attempts


def generated_text(log: str) -> tuple[str, bool]:
    lines = log.splitlines()
    perf_starts = [i for i, line in enumerate(lines) if "llama_perf_context_print:" in line]
    if not perf_starts:
        return "", False
    end = perf_starts[0]
    timestamped_log_lines = [
        i for i, line in enumerate(lines[:end])
        if re.match(r"^\d+\.\d+\.\d+\.\d+\s+[A-Z]\s", line)
    ]
    if not timestamped_log_lines:
        return "", False
    start = timestamped_log_lines[-1] + 1
    prediction = "\n".join(line.rstrip() for line in lines[start:end]).strip()
    return prediction, bool(prediction)


def parse_perf(log: str) -> dict:
    result: dict[str, dict] = {}
    for name, pattern in {
        "load": r"load time\s*=\s*([\d.]+) ms",
        "prompt_eval": r"prompt eval time\s*=\s*([\d.]+) ms /\s*(\d+) tokens",
        "eval": r"eval time\s*=\s*([\d.]+) ms /\s*(\d+) runs",
        "total": r"total time\s*=\s*([\d.]+) ms /\s*(\d+) tokens",
    }.items():
        match = re.search(pattern, log)
        if match:
            result[name] = {"milliseconds": float(match.group(1))}
            if match.lastindex and match.lastindex >= 2:
                result[name]["count"] = int(match.group(2))
    return result


def parse_env(items: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--env expects KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise SystemExit(f"invalid environment variable name: {key!r}")
        if key in {"RM13_QVARIANT", "RM13_QCACHE_DIR", "RM13_QID"}:
            raise SystemExit(f"set {key} through its dedicated runner option")
        env[key] = value
    return env


def load_samples(manifest_path: Path, split: str) -> tuple[list[dict], str, str]:
    if not manifest_path.is_file():
        raise SystemExit(f"dataset manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = sha256_file(manifest_path)
    if manifest.get("kind") == "rm13_textvqa_v0.5.1_quality_dataset_v1":
        expected_split_hash = "5b798932b1ad08c85c6328cceab046f191e9dfbbc0a2df01f971f523eeb2e7b6"
        if manifest.get("frozen_split_manifest_sha256") != expected_split_hash:
            raise SystemExit("quality dataset manifest does not bind to the frozen RM13 split")
        if split == "development":
            raise SystemExit("development split requires the existing dev subset manifest")
        samples = manifest.get("splits", {}).get(split, [])
        frozen = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
        expected_pairs = [
            (int(row["question_id"]), str(row["image_id"]))
            for row in frozen["splits"][split]
        ]
        actual_pairs = [(int(row["question_id"]), str(row["image_id"])) for row in samples]
        if actual_pairs != expected_pairs:
            raise SystemExit(f"dataset manifest QID/image pairs do not exactly match frozen {split} order")
    elif manifest.get("kind") == "textvqa_v0.5.1_validation_development_subset":
        if split != "development":
            raise SystemExit("the dev50 manifest is development-only and cannot feed calibration or final_test")
        samples = manifest.get("samples", [])
    else:
        raise SystemExit("unrecognized TextVQA dataset manifest kind")
    expected_count = {"calibration": 20, "final_test": 200}.get(split)
    if expected_count is not None and len(samples) != expected_count:
        raise SystemExit(f"frozen {split} split requires exactly {expected_count} QIDs")
    if not samples:
        raise SystemExit(f"dataset split {split} is empty")
    seen_qids: set[int] = set()
    seen_images: set[str] = set()
    for sample in samples:
        qid = int(sample["question_id"])
        image_id = str(sample["image_id"])
        if qid in seen_qids or image_id in seen_images:
            raise SystemExit(f"split {split} is not image/QID-disjoint at QID {qid}")
        seen_qids.add(qid)
        seen_images.add(image_id)
        image = manifest_path.parent / sample["image"]
        if not image.is_file() or sha256_file(image) != sample["image_sha256"]:
            raise SystemExit(f"missing or changed TextVQA JPEG for QID {qid}: {image}")
        if len(sample.get("answers", [])) != 10:
            raise SystemExit(f"QID {qid} must carry exactly 10 reference answers")
    return samples, digest, str(manifest.get("kind"))


def make_command(cli: Path, model: Path, mmproj: Path, image: Path, prompt: str, cwd: Path) -> list[str]:
    return [
        str(cli),
        "-m", str(model),
        "--mmproj", str(mmproj),
        "--image", str(image),
        "-p", prompt,
        "-t", "8",
        "-tb", "8",
        "-c", "4096",
        "-n", "48",
        "--seed", "42",
        "--temp", "0",
        "--top-p", "1",
        "--top-k", "0",
        "--device", "none",
        "-ngl", "0",
        "--no-mmproj-offload",
        "--no-warmup",
        "--perf",
        "-lv", "4",
    ]


def execute_case(job: dict) -> dict:
    """Execute one CLI process and return its record; the caller owns the journal."""
    t0 = time.perf_counter()
    returncode: int | None
    timed_out = False
    resource_log = job["resource_log"]
    measured_command = ["/usr/bin/time", "-v", "-o", str(resource_log), *job["command"]]
    with job["log_path"].open("xb") as log_stream:
        process = subprocess.Popen(
            measured_command,
            cwd=job["cwd"],
            env=job["env"],
            stdout=log_stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            returncode = process.wait(timeout=900)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            returncode = process.returncode
        log_stream.flush()
        os.fsync(log_stream.fileno())
    elapsed = time.perf_counter() - t0
    log_text = job["log_path"].read_text(encoding="utf-8", errors="replace")
    resource_text = resource_log.read_text(encoding="utf-8", errors="replace") if resource_log.is_file() else ""
    prediction, parse_ok = generated_text(log_text)
    perf = parse_perf(log_text)
    runtime_markers = {
        "applied": [line.strip() for line in log_text.splitlines() if "RM13_QSIM_APPLIED " in line],
        "fallback": [line.strip() for line in log_text.splitlines() if "RM13_QSIM_FALLBACK " in line],
        "diagnostic": [line.strip() for line in log_text.splitlines() if "RM13_QSIM_DIAG " in line],
    }
    runtime_marker_fields = {"applied": [], "fallback": [], "diagnostic": []}
    marker_names = {
        "applied": "RM13_QSIM_APPLIED",
        "fallback": "RM13_QSIM_FALLBACK",
        "diagnostic": "RM13_QSIM_DIAG",
    }
    for marker_kind, marker_lines in runtime_markers.items():
        marker_name = marker_names[marker_kind]
        for marker_line in marker_lines:
            suffix = marker_line.split(marker_name, 1)[-1].strip()
            fields = {}
            for field in suffix.split():
                if "=" in field:
                    field_name, field_value = field.split("=", 1)
                    fields[field_name] = field_value
            runtime_marker_fields[marker_kind].append(fields)
    token_count = perf.get("eval", {}).get("count")
    if token_count is None:
        token_count = perf.get("total", {}).get("count")
    visible = "".join(character for character in prediction if character.isprintable()).strip()
    unusual = {
        "empty_or_whitespace_only_answer": not visible,
        "answer_shorter_than_two_visible_characters": bool(visible) and len(visible) < 2,
        "parser_failure_or_nonzero_exit": not parse_ok or returncode != 0,
        "three_repeats_of_identical_token_sequence_at_least_three_tokens": has_triple_repetition(prediction),
        "generated_token_count_reaches_48_token_cap": token_count is not None and token_count >= 48,
    }
    sample = job["sample"]
    variant = job["variant"]
    qid = int(sample["question_id"])
    return {
        "event": "case_completed",
        "started_at_utc": job["started_at_utc"],
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "variant": variant,
        "variant_environment_variable": "RM13_QVARIANT",
        "variant_environment_value": variant,
        "question_id_environment_variable": "RM13_QID",
        "question_id_environment_value": str(qid),
        "cache_environment_variable": "RM13_QCACHE_DIR",
        "cache_environment_value": job["env"].get("RM13_QCACHE_DIR"),
        "question_id": qid,
        "image_id": sample["image_id"],
        "question": sample["question"],
        "image_path": str(job["image_path"]),
        "image_sha256": sample["image_sha256"],
        "reference_answers": sample["answers"],
        "prompt": job["prompt"],
        "command": job["command"],
        "resource_measurement_command": measured_command,
        "runtime_cli_path": str(job["cli"]),
        "runtime_cli_sha256": job["cli_sha256"],
        "runtime_shared_library_sha256s": {
            name: item["sha256"]
            for name, item in job["runtime_dependency_manifest"]["relevant_shared_libraries"].items()
        },
        "runtime_source_sha256": job["runtime_source_sha256"],
        "model_sha256": job["model_sha256"],
        "mmproj_sha256": job["mmproj_sha256"],
        "extra_environment_overrides": job["env_overrides"],
        "returncode": returncode,
        "timed_out": timed_out,
        "prediction": prediction,
        "prediction_parser": PARSER_DESCRIPTION,
        "prediction_parse_ok": parse_ok,
        "runner_wall_seconds_including_process_start_model_load_image_and_generation": round(elapsed, 6),
        "libllama_perf_metrics": perf,
        "process_peak_rss_kib": int(re.search(r"Maximum resident set size \(kbytes\): (\d+)", resource_text).group(1)) if re.search(r"Maximum resident set size \(kbytes\): (\d+)", resource_text) else None,
        "process_swap_count": int(re.search(r"Swaps: (\d+)", resource_text).group(1)) if re.search(r"Swaps: (\d+)", resource_text) else None,
        "q_runtime_marker_lines": runtime_markers,
        "q_runtime_marker_fields": runtime_marker_fields,
        "generated_token_count_observed": token_count,
        "unusual_output_flags": unusual,
        "raw_log": str(job["log_path"].relative_to(job["campaign_dir"])),
        "attempt": job["attempt"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, required=True, help="pinned llama-mtmd-cli built by the Q runtime worker")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--mmproj", type=Path, default=DEFAULT_MMPROJ)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_DATASET_MANIFEST)
    parser.add_argument("--split", choices=("calibration", "final_test", "development"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--cwd", type=Path, default=ROOT, help="CLI working directory")
    parser.add_argument("--qcache-dir", type=Path, help="passed to RM13_QCACHE_DIR for the quantization cache")
    parser.add_argument("--runtime-source-sha256", help="Q worker supplied source/patch identity for the CLI build")
    parser.add_argument("--jobs", type=int, choices=(1, 2), default=1, help="independent CLI processes; maximum two")
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE", help="extra environment for the pinned Q CLI; repeatable")
    parser.add_argument("--limit", type=int, help="development-only pilot limit")
    parser.add_argument("--resume", action="store_true", help="continue an existing campaign without replacing evidence")
    parser.add_argument("--final-test-approved", action="store_true", help="release final_test inference after runtime readiness and main-agent approval")
    args = parser.parse_args()

    if args.split == "final_test" and not args.final_test_approved:
        raise SystemExit("final_test is sealed; obtain runtime readiness and main-agent approval, then pass --final-test-approved")
    if args.split != "development" and args.limit is not None:
        raise SystemExit("--limit is available only for development pilots")
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")
    env_overrides = parse_env(args.env)
    inherited_qcache = os.environ.get("RM13_QCACHE_DIR")
    if args.qcache_dir is not None:
        env_overrides["RM13_QCACHE_DIR"] = str(args.qcache_dir.resolve())
    elif inherited_qcache is not None:
        env_overrides["RM13_QCACHE_DIR"] = inherited_qcache
    qcache_base = env_overrides.get("RM13_QCACHE_DIR")
    worker_qcache_dirs = {
        str(slot): (
            str((Path(qcache_base) / args.run_id / f"worker-{slot}").resolve())
            if args.jobs == 2 and qcache_base
            else qcache_base
        )
        for slot in range(args.jobs)
    }

    for path, expected, label in (
        (GATE_PATH, "3fc90a42b75b49198db6e90ea38809fc157ce657834be2cf1b12c01baeae0648", "quality gate"),
        (SPLIT_PATH, "5b798932b1ad08c85c6328cceab046f191e9dfbbc0a2df01f971f523eeb2e7b6", "quality split"),
    ):
        if sha256_file(path) != expected:
            raise SystemExit(f"frozen {label} SHA-256 mismatch")
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    model = args.model.resolve()
    mmproj = args.mmproj.resolve()
    cli = args.cli.resolve()
    cwd = args.cwd.resolve()
    for path in (cli, model, mmproj):
        if not path.is_file():
            raise SystemExit(f"required inference artifact is missing: {path}")
    expected_hashes = {
        "model": gate["generation"]["model"]["sha256"],
        "vision_projector": gate["generation"]["vision_projector"]["sha256"],
    }
    actual_model_hash = sha256_file(model)
    actual_mmproj_hash = sha256_file(mmproj)
    if actual_model_hash != expected_hashes["model"] or actual_mmproj_hash != expected_hashes["vision_projector"]:
        raise SystemExit("model or projector SHA-256 does not match the frozen quality gate")
    base_env = os.environ.copy()
    base_env.update(env_overrides)
    base_env.pop("RM13_QVARIANT", None)
    dependency_manifest = runtime_dependency_manifest(cli, base_env)
    if not Path("/usr/bin/time").is_file():
        raise SystemExit("/usr/bin/time is required to capture process peak RSS")
    samples, dataset_hash, dataset_kind = load_samples(args.manifest.resolve(), args.split)
    if args.limit is not None:
        samples = samples[: args.limit]
    if args.split == "development" and not args.limit:
        print("NOTICE: development data only; results cannot substitute for calibration/final quality evidence", file=sys.stderr)

    output_root = args.output_root.resolve()
    campaign_dir = output_root / args.run_id
    metadata_path = campaign_dir / "campaign.json"
    journal_path = campaign_dir / "events.jsonl"
    logs_dir = campaign_dir / "logs"
    config = {
        "run_id": args.run_id,
        "split": args.split,
        "split_manifest_sha256": sha256_file(SPLIT_PATH),
        "quality_gate_sha256": sha256_file(GATE_PATH),
        "contract_sha256": sha256_file(CONTRACT_PATH),
        "dataset_manifest": str(args.manifest.resolve()),
        "dataset_manifest_sha256": dataset_hash,
        "dataset_manifest_kind": dataset_kind,
        "selected_question_ids": [int(row["question_id"]) for row in samples],
        "configurations": VARIANTS,
        "execution_order": RUN_PRIORITY,
        "cli_path": str(cli),
        "cli_sha256": sha256_file(cli),
        "runtime_source_sha256": args.runtime_source_sha256,
        "model_path": str(model),
        "model_sha256": actual_model_hash,
        "mmproj_path": str(mmproj),
        "mmproj_sha256": actual_mmproj_hash,
        "working_directory": str(cwd),
        "environment_overrides": env_overrides,
        "jobs": args.jobs,
        "worker_qcache_directories": worker_qcache_dirs,
        "runtime_dependency_manifest": dependency_manifest,
        "generation": GENERATION,
        "prompt_template": PROMPT_TEMPLATE,
        "measurement_boundary": "one CPU llama-mtmd-cli process per image; process start through exit",
        "final_test_release_flag_present": bool(args.final_test_approved),
    }
    if not args.resume and campaign_dir.exists():
        raise SystemExit(f"campaign evidence already exists; use --resume: {campaign_dir}")
    if args.resume and not metadata_path.is_file():
        raise SystemExit("--resume requires an existing campaign.json")
    campaign_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    if args.resume:
        prior = json.loads(metadata_path.read_text(encoding="utf-8"))
        if canonical_json(prior.get("configuration")) != canonical_json(config):
            raise SystemExit("resume configuration differs from the immutable campaign configuration")
    else:
        metadata = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "configuration": config,
            "status_semantics": "A completed case records raw stdout, parser status, exit status and the per-case RM13_QVARIANT. Scoring is a separate command.",
        }
        with metadata_path.open("x", encoding="utf-8") as stream:
            json.dump(metadata, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

    completed_keys, prior_attempts = load_events(journal_path)
    expected_keys = {(variant, int(row["question_id"])) for variant in VARIANTS for row in samples}
    unexpected = completed_keys - expected_keys
    if unexpected:
        raise SystemExit(f"journal includes cases outside this campaign: {sorted(unexpected)[:3]}")
    total = len(expected_keys)
    progress = len(completed_keys)
    try:
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            for variant in RUN_PRIORITY:
                pending = [
                    (index, sample)
                    for index, sample in enumerate(samples, start=1)
                    if (variant, int(sample["question_id"])) not in completed_keys
                ]
                for batch_start in range(0, len(pending), args.jobs):
                    batch = pending[batch_start : batch_start + args.jobs]
                    batch_jobs = []
                    for slot, (index, sample) in enumerate(batch):
                        qid = int(sample["question_id"])
                        key = (variant, qid)
                        case_key = f"{variant}:q{qid}"
                        attempts = prior_attempts.get(case_key, [])
                        attempt = len(attempts) + 1
                        image_path = (args.manifest.resolve().parent / sample["image"]).resolve()
                        prompt = PROMPT_TEMPLATE.format(question=sample["question"])
                        command = make_command(cli, model, mmproj, image_path, prompt, cwd)
                        log_name = f"{variant}_{index:03d}_q{qid}_attempt{attempt:02d}.log"
                        log_path = logs_dir / log_name
                        resource_log_path = logs_dir / f"{variant}_{index:03d}_q{qid}_attempt{attempt:02d}.time.txt"
                        started = datetime.now(timezone.utc).isoformat()
                        case_env = base_env.copy()
                        case_env["RM13_QVARIANT"] = variant
                        case_env["RM13_QID"] = str(qid)
                        cache_path = worker_qcache_dirs[str(slot)]
                        if cache_path:
                            Path(cache_path).mkdir(parents=True, exist_ok=True)
                            case_env["RM13_QCACHE_DIR"] = cache_path
                        append_jsonl(journal_path, {
                            "event": "attempt_started",
                            "event_time_utc": started,
                            "case_key": case_key,
                            "variant": variant,
                            "variant_environment_value": variant,
                            "question_id": qid,
                            "question_id_environment_value": str(qid),
                            "image_id": sample["image_id"],
                            "image_sha256": sample["image_sha256"],
                            "cache_environment_value": case_env.get("RM13_QCACHE_DIR"),
                            "attempt": attempt,
                            "command": command,
                            "log_path": str(log_path.relative_to(campaign_dir)),
                            "resource_log_path": str(resource_log_path.relative_to(campaign_dir)),
                        })
                        batch_jobs.append({
                            "variant": variant,
                            "sample": sample,
                            "command": command,
                            "cwd": cwd,
                            "env": case_env,
                            "log_path": log_path,
                            "resource_log": resource_log_path,
                            "started_at_utc": started,
                            "attempt": attempt,
                            "image_path": image_path,
                            "prompt": prompt,
                            "cli": cli,
                            "cli_sha256": config["cli_sha256"],
                            "runtime_dependency_manifest": dependency_manifest,
                            "runtime_source_sha256": args.runtime_source_sha256,
                            "model_sha256": actual_model_hash,
                            "mmproj_sha256": actual_mmproj_hash,
                            "env_overrides": env_overrides,
                            "campaign_dir": campaign_dir,
                        })
                    records = list(executor.map(execute_case, batch_jobs))
                    for record in records:
                        append_jsonl(journal_path, record)
                        key = (record["variant"], int(record["question_id"]))
                        completed_keys.add(key)
                        progress += 1
                        print(
                            f"{progress}/{total} variant={record['variant']} qid={record['question_id']} "
                            f"rc={record['returncode']} parse={record['prediction_parse_ok']} "
                            f"wall={record['runner_wall_seconds_including_process_start_model_load_image_and_generation']:.2f}s "
                            f"answer={record['prediction'][:90]!r}",
                            flush=True,
                        )
    except KeyboardInterrupt:
        print("Interrupted. The attempt-start event and any partial CLI log remain; use --resume to continue.", file=sys.stderr)
        return 130
    print(json.dumps({"campaign_dir": str(campaign_dir), "completed_cases": progress, "expected_cases": total}, indent=2))
    return 0 if progress == total else 1


def has_triple_repetition(text: str) -> bool:
    tokens = re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?", text.lower())
    for width in range(3, min(16, len(tokens) // 3) + 1):
        for start in range(0, len(tokens) - 3 * width + 1):
            sequence = tokens[start : start + width]
            if tokens[start + width : start + 2 * width] == sequence and tokens[start + 2 * width : start + 3 * width] == sequence:
                return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
