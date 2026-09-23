#!/usr/bin/env python3
"""Derive a host-only TextVQA development diagnostic from split raw CLI streams.

The three-case pilot is deliberately small. This program joins labels only after
reading the immutable host manifest; no reference answer belongs in board raw.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = (ROOT / "experiments/raw").resolve()
DERIVED_ROOT = (ROOT / "experiments/derived").resolve()
DEFAULT_MANIFEST = ROOT / "datasets/textvqa_v0.5.1_dev_50_seed20260923/manifest.json"
MANIFEST_SHA256 = "62c32317029e40895ffd8e476e8a845416dac9d1d9490dfd6efb5f28a4374962"
RUNTIME_COMMIT = "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2"
EVALUATOR_SHA256 = "e10a99e15c4658f8d0d83a05cc536c835922e701171fce0016718bec021b8c0a"
MODEL_SHA256 = "8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773"
MMPROJ_SHA256 = "ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293"
BOARD_CLI_SHA256 = "84bfa2f5f91f13503b5a1349e05594cda30c01613227187cfb9e48e7b805f1d7"
HOST_CLI_SHA256 = "17f33b3915301aa575af9e972cbe3bf7d34a7a96e52599918500d148f1f54312"
BUILD_ATTESTATION = RAW_ROOT / "kv260_cpu_p2_baseline_round01/cpu_build_attestation_v1.json"
BUILD_ATTESTATION_SHA256 = "48cfe4fa9c5a4647ecb193ca91c6eaa07a539abd8addb2407ec14bf4d87755c2"
BOARD_BASE = Path("/home/ubuntu/kv260-vlm-p2-cpu")
PILOT_QIDS = (38299, 37804, 35419)
PROMPT_PREFIX = "Answer the following question based only on the image. Give a short, direct answer.\nQuestion: "
PROMPT_SUFFIX = "\nAnswer:"

LOG_PREFIX = r"^\d+\.\d+\.\d+\.\d+\s+I\s+"
ENCODE_BEGIN = re.compile(LOG_PREFIX + r"encoding mtmd batch, n_chunks = (\d+) \(done = (\d+), total = (\d+)\)$")
ENCODE_END = re.compile(LOG_PREFIX + r"mtmd batch encoding done in (\d+) ms$")
DECODE_BEGIN = re.compile(LOG_PREFIX + r"decoding image batch (\d+)/(\d+), n_tokens_batch = (\d+)$")
DECODE_END = re.compile(LOG_PREFIX + r"image decoded \(batch (\d+)/(\d+)\) in (\d+) ms$")
ERROR_LOG = re.compile(r"^\d+\.\d+\.\d+\.\d+\s+E\s+", re.MULTILINE)
COMMAND_KEYS = {
    "schema", "question_id", "image_id", "image_path", "image_sha256", "image_bytes",
    "manifest_sha256", "runtime_commit", "model_sha256", "mmproj_sha256", "cli_sha256",
    "argv", "working_directory", "environment", "written_before_launch_at_utc",
}
INPUT_KEYS = {
    "schema", "question_id", "image_id", "image_path", "image_sha256", "image_bytes",
    "verification_returncode", "verified_before_cli", "verification_scope", "verified_at_utc",
}
EXECUTION_KEYS = {
    "schema", "question_id", "cli_started", "non_start_reason", "non_start_at_utc", "prior_run_id",
    "started_at_utc", "ended_at_utc",
    "elapsed_monotonic_seconds", "wrapper_returncode", "time_child_exit_status",
    "execution_complete", "raw_copy_complete", "timeout_seconds", "resource_txt_sha256",
    "command_json_sha256", "input_verification_json_sha256", "artifact_verification_json_sha256",
    "preflight_before_json_sha256", "preflight_after_json_sha256", "image_post_verification_json_sha256",
    "stdout_log_sha256", "stderr_log_sha256", "spawn_pid", "spawn_argv_sha256",
    "stdout_stderr_same_child_capture", "runner_sha256", "remote_run_dir",
    "remote_process_cleanup_verified",
}
ARTIFACT_KEYS = {
    "schema", "question_id", "runtime_commit", "verification_returncode", "verified_before_cli",
    "verified_at_utc", "cli_path", "cli_sha256", "model_path", "model_sha256",
    "mmproj_path", "mmproj_sha256", "cpu_build_attestation_sha256", "verification_scope",
    "source_archive_sha256", "cmake_cache_sha256", "cmake_cpu_only_configuration_verified",
    "elf_file_summary", "elf_readelf_machine", "ldd_no_missing", "ldd_local_library_paths",
}
ENVIRONMENT_KEYS = {
    "MTMD_TEST_RESPONSE_MARKER", "marker_removed_before_launch", "marker_was_present_before_removal",
}
SAFE_NON_LABEL_METADATA_KEYS = {"answerparseok"}
HOST_COPY_RECEIPT_NAME = "host_copy_verification.json"
HOST_COPY_RECEIPT_KEYS = {
    "schema", "question_id", "run_id", "completion_json_sha256",
    "board_files_verified", "verified_file_names", "verified_at_utc",
}
PILOT_BOARD_FILE_NAMES = {
    "command.json", "input_verification.json", "artifact_verification.json",
    "preflight_before.json", "preflight_after.json", "image_post_verification.json",
    "stdout.log", "stderr.log", "resource.txt", "result.json",
}
NON_START_REASONS = {
    "PREFLIGHT_BLOCKED", "OWNER_WINDOW_UNAVAILABLE", "PRIOR_CASE_FAILED", "INPUT_UNAVAILABLE",
    "PRIOR_CASE_STOP_RULE", "PRIOR_CASE_UNRESOLVED", "REVIEW_GATE_MISSING",
    "RUNNER_ABORTED_BEFORE_SPAWN",
}
# Every execution-only field is contradictory in a cli_started=false record.
# Keep the schema/identity and explicit non-start metadata as the only exceptions.
START_EVIDENCE_KEYS = EXECUTION_KEYS - {
    "schema", "question_id", "cli_started", "non_start_reason", "non_start_at_utc", "prior_run_id",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fail_if(condition: bool, message: str) -> None:
    if condition:
        raise ValueError(message)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    fail_if(not isinstance(value, dict), f"expected JSON object: {path}")
    return value


def exact_keys(value: dict[str, Any], allowed: set[str], name: str) -> None:
    extra = sorted(set(value) - allowed)
    fail_if(bool(extra), f"unexpected {name} keys: {extra}")


def sha_argv(argv: list[str]) -> str:
    payload = json.dumps(argv, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def utc_timestamp(value: Any) -> datetime:
    fail_if(not isinstance(value, str), "UTC timestamp missing")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    fail_if(timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0,
            "timestamp is not UTC")
    return timestamp


def has_label_keys(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if normalized in SAFE_NON_LABEL_METADATA_KEYS:
                if has_label_keys(child):
                    return True
                continue
            if any(word in normalized for word in
                   ("answer", "groundtruth", "reference", "label", "annotation", "goldresponse", "ocrsidecar")):
                return True
            if has_label_keys(child):
                return True
        return False
    if isinstance(value, list):
        return any(has_label_keys(child) for child in value)
    return False


def verify_board_completion_manifest(raw_dir: Path, qid: int) -> str:
    """Verify every board-origin file against the board completion manifest.

    The completion file is copied from the board. Host-only `runner_*` records
    are deliberately outside this manifest and cannot replace its file hashes.
    Returns the completion.json SHA-256 for the derived record.
    """
    completion_path = raw_dir / "completion.json"
    fail_if(completion_path.is_symlink() or not completion_path.is_file(),
            "board completion record missing or symlinked")
    completion = read_json(completion_path)
    exact_keys(completion, {"schema", "run_id", "manifest", "completed_at_utc", "worker_pid"},
               "board completion")
    fail_if(completion.get("schema") != "kv260_cpu_p2_textvqa_board_completion_v1",
            "board completion schema mismatch")
    expected_run_id = f"kv260_cpu_p2_tvqa_q{qid}_r01"
    fail_if(completion.get("run_id") != expected_run_id, "board completion run ID mismatch")
    utc_timestamp(completion.get("completed_at_utc"))
    fail_if(not isinstance(completion.get("worker_pid"), int) or
            isinstance(completion.get("worker_pid"), bool) or completion["worker_pid"] <= 0,
            "board completion worker PID is invalid")
    entries = completion.get("manifest")
    fail_if(not isinstance(entries, dict) or set(entries) != PILOT_BOARD_FILE_NAMES,
            "board completion file set mismatch")
    for name, metadata in entries.items():
        fail_if(not isinstance(name, str) or Path(name).name != name or name in ("", ".", ".."),
                f"unsafe board completion path: {name!r}")
        fail_if(not isinstance(metadata, dict) or set(metadata) != {"bytes", "sha256"},
                f"invalid board completion metadata: {name}")
        byte_count = metadata.get("bytes")
        digest = metadata.get("sha256")
        fail_if(not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0,
                f"invalid board completion byte count: {name}")
        fail_if(not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest),
                f"invalid board completion SHA-256: {name}")
        path = raw_dir / name
        fail_if(path.is_symlink() or not path.is_file(), f"board completion file missing: {name}")
        fail_if(path.stat().st_size != byte_count or sha256(path) != digest,
                f"board completion hash/size mismatch: {name}")
    return sha256(completion_path)


def verify_host_copy_receipt(raw_dir: Path, qid: int, completion_sha256: str) -> None:
    receipt_path = raw_dir / HOST_COPY_RECEIPT_NAME
    fail_if(receipt_path.is_symlink() or not receipt_path.is_file(),
            "host copy-verification receipt missing or symlinked")
    receipt = read_json(receipt_path)
    exact_keys(receipt, HOST_COPY_RECEIPT_KEYS, "host copy-verification receipt")
    expected_names = sorted(PILOT_BOARD_FILE_NAMES | {"completion.json"})
    fail_if(receipt.get("schema") != "kv260_cpu_p2_textvqa_host_copy_verification_v1" or
            receipt.get("question_id") != qid or
            receipt.get("run_id") != f"kv260_cpu_p2_tvqa_q{qid}_r01" or
            receipt.get("completion_json_sha256") != completion_sha256 or
            receipt.get("board_files_verified") is not True or
            receipt.get("verified_file_names") != expected_names,
            "host copy-verification receipt does not bind the verified board files")
    utc_timestamp(receipt.get("verified_at_utc"))


def inspect_raw_json_labels(raw_dir: Path) -> list[str]:
    errors: list[str] = []
    if not raw_dir.exists():
        return errors
    for path in sorted(raw_dir.rglob("*")):
        if path.is_symlink():
            errors.append(f"RAW_SYMLINK_REJECTED: {path.relative_to(raw_dir)}")
            continue
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        try:
            if has_label_keys(read_json(path)):
                errors.append(f"RAW_REFERENCE_LABEL_KEY: {path.relative_to(raw_dir)}")
        except (OSError, ValueError) as exc:
            errors.append(f"RAW_JSON_INVALID: {path.relative_to(raw_dir)}: {exc}")
    return errors


def inspect_events(stderr: str) -> dict[str, Any]:
    """Pair the pinned CLI's successful encode and image-decode INFO events."""
    enc_open: tuple[int, int, int] | None = None
    dec_open: tuple[int, int, int] | None = None
    decode_group_next: int | None = None
    decode_group_total: int | None = None
    encoded_chunk_credit = 0
    total_chunks: int | None = None
    last_encoded_chunk = -1
    encoded = 0
    decoded = 0
    decoded_tokens = 0
    event_errors: list[str] = []
    for line_no, line in enumerate(stderr.splitlines(), start=1):
        match = ENCODE_BEGIN.match(line)
        if match:
            values = tuple(map(int, match.groups()))
            n_added, done, total = values
            if (enc_open is not None or dec_open is not None or decode_group_next is not None or
                    encoded_chunk_credit != 0 or n_added <= 0 or total <= 0 or
                    done <= last_encoded_chunk or done + n_added > total or
                    (total_chunks is not None and total != total_chunks)):
                event_errors.append(f"invalid encoding start at stderr line {line_no}")
            else:
                enc_open = values
                total_chunks = total
            continue
        match = ENCODE_END.match(line)
        if match:
            if enc_open is None or dec_open is not None:
                event_errors.append(f"encoding completion without start at stderr line {line_no}")
            else:
                encoded += 1
                encoded_chunk_credit += enc_open[0]
                last_encoded_chunk = enc_open[1] + enc_open[0] - 1
                enc_open = None
            continue
        match = DECODE_BEGIN.match(line)
        if match:
            values = tuple(map(int, match.groups()))
            number, total, tokens = values
            invalid = (enc_open is not None or dec_open is not None or number < 1 or
                       total < number or tokens <= 0)
            if decode_group_next is None:
                invalid = invalid or number != 1 or encoded_chunk_credit <= 0
            else:
                invalid = invalid or number != decode_group_next or total != decode_group_total
            if invalid:
                event_errors.append(f"invalid image decode start at stderr line {line_no}")
            else:
                if decode_group_next is None:
                    encoded_chunk_credit -= 1
                    decode_group_total = total
                dec_open = values
            continue
        match = DECODE_END.match(line)
        if match:
            number, total, _ms = map(int, match.groups())
            if dec_open is None or (number, total) != dec_open[:2]:
                event_errors.append(f"image decode completion mismatch at stderr line {line_no}")
            else:
                decoded += 1
                decoded_tokens += dec_open[2]
                dec_open = None
                if number == total:
                    decode_group_next = None
                    decode_group_total = None
                else:
                    decode_group_next = number + 1
    if enc_open is not None:
        event_errors.append("unterminated encoding event")
    if dec_open is not None:
        event_errors.append("unterminated image decode event")
    if decode_group_next is not None:
        event_errors.append("incomplete image decode batch group")
    if encoded_chunk_credit != 0:
        event_errors.append("encoded chunks without completed image decode group")
    if ERROR_LOG.search(stderr):
        event_errors.append("ERROR-level log present")
    if encoded == 0 or decoded == 0 or decoded_tokens == 0:
        event_errors.append("positive encode and image decode events required")
    return {
        "encoding_batch_completions": encoded,
        "image_decode_batch_completions": decoded,
        "observed_positive_image_embedding_tokens": decoded_tokens,
        "event_errors": event_errors,
        "event_predicate_pass": not event_errors,
    }


def extract_stdout(stdout: bytes) -> tuple[str, str | None]:
    if len(stdout) > 8192:
        return "", "STDOUT_TOO_LARGE"
    try:
        value = stdout.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return "", "STDOUT_NOT_UTF8"
    if not value.startswith("\n"):
        return "", "STDOUT_SHAPE_MISMATCH"
    suffix = "\n\n\n" if value.endswith("\n\n\n") else "\n\n" if value.endswith("\n\n") else None
    if suffix is None:
        return "", "STDOUT_SHAPE_MISMATCH"
    body = value[1:-len(suffix)]
    if not body or body.startswith("\n") or body.endswith("\n"):
        return "", "STDOUT_SHAPE_MISMATCH"
    answer = body.strip()
    if not answer:
        return "", "EMPTY_ANSWER"
    if len(answer) > 512 or any(ord(c) < 32 and c not in "\n\t" for c in answer):
        return "", "ANSWER_CONTROL_OR_TOO_LONG"
    if re.search(r"^\d+\.\d+\.\d+\.\d+\s+[DIWE]\s+", answer, re.MULTILINE):
        return "", "LOG_LINE_IN_ANSWER"
    return answer, None


def expected_execution_paths(qid: int, raw_dir: Path, image_id: str, mode: str,
                             manifest_path: Path) -> dict[str, str]:
    if mode == "pilot":
        remote_run = BOARD_BASE / "runs" / raw_dir.name
        return {
            "cwd": str(BOARD_BASE),
            "resource": str(remote_run / "resource.txt"),
            "cli": str(BOARD_BASE / "build-cpu/bin/llama-mtmd-cli"),
            "model": str(BOARD_BASE / "input/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf"),
            "mmproj": str(BOARD_BASE / "input/mmproj-MiniCPM-V-4.6-f16.gguf"),
            "image": str(BOARD_BASE / "input/textvqa-dev50" / f"{image_id}.jpg"),
            "remote_run": str(remote_run),
        }
    return {
        "cwd": str(ROOT),
        "resource": str(raw_dir / "resource.txt"),
        "cli": str(ROOT / "runtime/llama.cpp/build/bin/llama-mtmd-cli"),
        "model": str(ROOT / "models/gguf/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf"),
        "mmproj": str(ROOT / "models/gguf/mmproj-MiniCPM-V-4.6-f16.gguf"),
        "image": str(manifest_path.parent / "images" / f"{image_id}.jpg"),
        "remote_run": "UNAVAILABLE_HOST_REHEARSAL",
    }


def validate_full_argv(argv: list[str], paths: dict[str, str], prompt: str, mode: str) -> None:
    duration = "300s" if mode == "pilot" else "60s"
    kill_after = "10s" if mode == "pilot" else "5s"
    expected = [
        "timeout", "--verbose", "--signal=TERM", f"--kill-after={kill_after}", duration,
        "/usr/bin/time", "-v", "-o", paths["resource"], paths["cli"],
        "-m", paths["model"], "--mmproj", paths["mmproj"],
        "--image", paths["image"], "-p", prompt,
        "-t", "2", "-tb", "2", "-c", "4096", "-n", "48", "--seed", "42",
        "--temp", "0", "--top-p", "1", "--top-k", "0", "--device", "none",
        "-ngl", "0", "--no-mmproj-offload", "--no-warmup", "--perf", "-lv", "4",
    ]
    fail_if(argv != expected, "argv differs from the exact frozen wrapper/CLI/model/mmproj/image/option sequence")


def inspect_case(qid: int, raw_dir: Path, sample: dict[str, Any], manifest: dict[str, Any],
                 manifest_sha: str, manifest_path: Path, evaluator: Any, mode: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "question_id": qid,
        "image_id": sample["image_id"],
        "raw_dir": str(raw_dir),
        "attempted": None,
        "status": "ATTEMPT_STATE_UNKNOWN",
        "normal_exit": False,
        "answer_parse_ok": False,
        "image_processing_verified": False,
        "prediction": None,
        "soft_accuracy": None,
        "errors": [],
        "output_token_count": "UNAVAILABLE",
        "stop_reason_eos_or_antiprompt": "UNAVAILABLE",
        "max_new_tokens_hit": "UNAVAILABLE",
    }
    errors: list[str] = result["errors"]
    raw_json_errors = inspect_raw_json_labels(raw_dir)
    state_path = raw_dir / "result.json"
    if not state_path.is_file():
        errors.append("ATTEMPT_STATE_UNAVAILABLE")
        errors.extend(raw_json_errors)
        return result
    try:
        state = read_json(state_path)
        result["result_json_sha256"] = sha256(state_path)
        fail_if(state.get("question_id") != qid, "execution qid mismatch")
        fail_if(not isinstance(state.get("cli_started"), bool), "cli_started must be boolean")
        result["attempted"] = state["cli_started"]
        fail_if(state.get("schema") != "kv260_cpu_p2_textvqa_execution_v1", "execution schema mismatch")
        exact_keys(state, EXECUTION_KEYS, "execution")
        if not state["cli_started"]:
            fail_if(state.get("non_start_reason") not in NON_START_REASONS,
                    "non-start reason must be an enumerated code")
            fail_if("prior_run_id" not in state, "non-start state must record prior_run_id or null")
            utc_timestamp(state.get("non_start_at_utc"))
            prior_run = state.get("prior_run_id")
            if state["non_start_reason"] in ("PRIOR_CASE_FAILED", "PRIOR_CASE_STOP_RULE",
                                                "PRIOR_CASE_UNRESOLVED"):
                order = {qid: index for index, qid in enumerate(PILOT_QIDS)}
                fail_if(not isinstance(prior_run, str) or
                        not any(order[prior] < order[qid] and
                                prior_run == f"kv260_cpu_p2_tvqa_q{prior}_r01"
                                for prior in PILOT_QIDS),
                        "prior failed run ID does not precede this case")
            else:
                fail_if(prior_run is not None, "unexpected prior run ID for this non-start reason")
            contradictory = sorted(key for key in START_EVIDENCE_KEYS if key in state)
            fail_if(bool(contradictory), f"non-start state has launch/exit evidence: {contradictory}")
            for name in ("stdout.log", "stderr.log", "resource.txt"):
                path = raw_dir / name
                fail_if(path.is_file() and path.stat().st_size > 0,
                        f"non-start state has nonempty {name}")
            for name, allowed in (("command.json", COMMAND_KEYS),
                                  ("input_verification.json", INPUT_KEYS),
                                  ("artifact_verification.json", ARTIFACT_KEYS)):
                path = raw_dir / name
                if path.is_file():
                    record = read_json(path)
                    exact_keys(record, allowed, name)
                    fail_if(record.get("question_id") != qid, f"non-start {name} qid mismatch")
            fail_if(bool(raw_json_errors), f"raw JSON label/format issue: {raw_json_errors}")
            result["attempted"] = False
            result["prediction"] = None
            result["status"] = "NOT_ATTEMPTED"
            result["non_start_reason"] = state["non_start_reason"]
            return result
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if result["attempted"] is False:
            result["attempted"] = None
        errors.append(f"ATTEMPT_STATE_INVALID: {exc}")
        errors.extend(raw_json_errors)
        if result["attempted"] is True:
            result["prediction"] = ""
            result["soft_accuracy"] = 0.0
            result["status"] = "ATTEMPTED_SCORED_EMPTY"
        return result

    # Once CLI start is recorded, every failure stays in the attempted denominator.
    result["prediction"] = ""
    result["soft_accuracy"] = 0.0
    errors.extend(raw_json_errors)
    required_names = ["command.json", "input_verification.json", "stdout.log", "stderr.log", "resource.txt"]
    if mode == "pilot":
        required_names.extend(("artifact_verification.json", "preflight_before.json",
                               "preflight_after.json", "image_post_verification.json", "completion.json",
                               HOST_COPY_RECEIPT_NAME))
    paths = {name: raw_dir / name for name in required_names}
    for name, path in paths.items():
        if not path.is_file():
            errors.append(f"RAW_FILE_MISSING: {name}")
    if errors:
        result["status"] = "ATTEMPTED_UNSCORABLE"
        return result

    if mode == "pilot":
        try:
            completion_digest = verify_board_completion_manifest(raw_dir, qid)
            verify_host_copy_receipt(raw_dir, qid, completion_digest)
            result["completion_json_sha256"] = completion_digest
            result["board_completion_manifest_verified"] = True
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"BOARD_COMPLETION_MANIFEST_INVALID: {exc}")
            result["board_completion_manifest_verified"] = False
            result["status"] = "ATTEMPTED_UNSCORABLE"
            return result

    for name, path in paths.items():
        digest = sha256(path)
        result[f"{name.replace('.', '_')}_sha256"] = digest
        if name == "completion.json":
            continue
        key = "resource_txt_sha256" if name == "resource.txt" else name.replace(".", "_") + "_sha256"
        if state.get(key) != digest:
            errors.append(f"RAW_SHA_MISMATCH: {name}")
    raw_hashes_verified = not any(error.startswith("RAW_SHA_MISMATCH") for error in errors)

    try:
        command = read_json(paths["command.json"])
        inputs = read_json(paths["input_verification.json"])
        fail_if(command.get("schema") != "kv260_cpu_p2_textvqa_command_v1", "command schema mismatch")
        fail_if(inputs.get("schema") != "kv260_cpu_p2_textvqa_input_verification_v1",
                "input verification schema mismatch")
        exact_keys(command, COMMAND_KEYS, "command")
        exact_keys(inputs, INPUT_KEYS, "input verification")
        fail_if(any(has_label_keys(record) for record in (state, command, inputs)),
                "host reference labels found in raw case metadata")
        argv = command.get("argv")
        fail_if(not isinstance(argv, list) or not all(isinstance(x, str) for x in argv), "argv must be string array")
        execution_paths = expected_execution_paths(qid, raw_dir, sample["image_id"], mode, manifest_path)
        prompt = PROMPT_PREFIX + sample["question"] + PROMPT_SUFFIX
        validate_full_argv(argv, execution_paths, prompt, mode)
        fail_if(command.get("working_directory") != execution_paths["cwd"], "working directory differs")
        fail_if(command.get("question_id") != qid or command.get("image_id") != sample["image_id"],
                "command qid/image mismatch")
        fail_if(command.get("runtime_commit") != RUNTIME_COMMIT, "runtime commit mismatch")
        fail_if(command.get("manifest_sha256") != manifest_sha, "command manifest SHA mismatch")
        fail_if(command.get("model_sha256") != MODEL_SHA256 or
                command.get("mmproj_sha256") != MMPROJ_SHA256, "model or mmproj SHA mismatch")
        fail_if(command.get("image_path") != execution_paths["image"], "command image path mismatch")
        image_record = manifest["images"][sample["image_id"]]
        expected_sha = sample["image_sha256"]
        fail_if(image_record["sha256"] != expected_sha, "manifest image SHA inconsistent")
        fail_if(any(record.get("question_id") != qid or record.get("image_id") != sample["image_id"]
                    for record in (command, inputs)), "raw case ID mismatch")
        for record in (command, inputs):
            fail_if(record.get("image_path") != execution_paths["image"] or
                    record.get("image_sha256") != expected_sha or
                    record.get("image_bytes") != image_record["bytes"], "raw input SHA/path/bytes mismatch")
        fail_if(inputs.get("verification_returncode") != 0 or
                inputs.get("verified_before_cli") is not True or
                inputs.get("verification_scope") !=
                ("board_filesystem_prelaunch" if mode == "pilot" else "host_filesystem_prelaunch"),
                "prelaunch input verification missing or wrong scope")
        started_at = utc_timestamp(state.get("started_at_utc"))
        fail_if(utc_timestamp(inputs.get("verified_at_utc")) > started_at,
                "input verification timestamp is after CLI start")
        fail_if(utc_timestamp(command.get("written_before_launch_at_utc")) > started_at,
                "command timestamp is after CLI start")
        if mode == "pilot":
            artifact = read_json(paths["artifact_verification.json"])
            exact_keys(artifact, ARTIFACT_KEYS, "artifact verification")
            fail_if(artifact.get("schema") != "kv260_cpu_p2_textvqa_artifact_verification_v1" or
                    artifact.get("question_id") != qid or
                    artifact.get("runtime_commit") != RUNTIME_COMMIT or
                    artifact.get("verification_returncode") != 0 or
                    artifact.get("verified_before_cli") is not True or
                    artifact.get("verification_scope") != "board_filesystem_prelaunch",
                    "board artifact verification identity/provenance mismatch")
            fail_if(utc_timestamp(artifact.get("verified_at_utc")) > started_at,
                    "board artifact verification timestamp is after CLI start")
            fail_if(sha256(BUILD_ATTESTATION) != BUILD_ATTESTATION_SHA256,
                    "host build attestation SHA changed")
            build = read_json(BUILD_ATTESTATION)
            fail_if(build.get("schema") != "kv260_cpu_p2_build_attestation_v1" or
                    build.get("runtime_commit") != RUNTIME_COMMIT or
                    build.get("cli_sha256") != BOARD_CLI_SHA256 or
                    artifact.get("cpu_build_attestation_sha256") != BUILD_ATTESTATION_SHA256,
                    "board artifact record does not join host build attestation")
            attested_local = {str(BOARD_BASE / item["path"]) for item in build["local_shared_libraries"]}
            ldd_local = artifact.get("ldd_local_library_paths")
            fail_if(artifact.get("source_archive_sha256") != "5fe5b3133f7c31f42cc9597059ddb69f31045dbbf3fbfe8bd57236ab0626efe9" or
                    artifact.get("cmake_cache_sha256") != build.get("cmake_cache_sha256") or
                    artifact.get("cmake_cpu_only_configuration_verified") is not True or
                    "aarch64" not in str(artifact.get("elf_file_summary", "")).lower() or
                    "aarch64" not in str(artifact.get("elf_readelf_machine", "")).lower() or
                    artifact.get("ldd_no_missing") is not True or
                    not isinstance(ldd_local, list) or not ldd_local or
                    not set(ldd_local).issubset(attested_local),
                    "board source, CPU config, ELF or dynamic-link evidence missing/mismatched")
            for key, digest in (("cli", BOARD_CLI_SHA256),
                                ("model", MODEL_SHA256), ("mmproj", MMPROJ_SHA256)):
                fail_if(artifact.get(f"{key}_path") != execution_paths[key] or
                        artifact.get(f"{key}_sha256") != digest or
                        command.get(f"{key}_sha256") != digest,
                        f"{key} path/SHA not bound to prelaunch board verification")
            fail_if(state.get("remote_run_dir") != execution_paths["remote_run"] or
                    not isinstance(state.get("spawn_pid"), int) or state["spawn_pid"] <= 0 or
                    state.get("spawn_argv_sha256") != sha_argv(argv) or
                    state.get("stdout_stderr_same_child_capture") is not True or
                    state.get("remote_process_cleanup_verified") is not True,
                    "board spawn/capture provenance record missing or inconsistent")
            pre_before = read_json(paths["preflight_before.json"])
            pre_after = read_json(paths["preflight_after.json"])
            image_after = read_json(paths["image_post_verification.json"])
            started_at = utc_timestamp(state.get("started_at_utc"))
            ended_at = utc_timestamp(state.get("ended_at_utc"))
            fail_if(pre_before.get("schema") != "kv260_cpu_p2_textvqa_runtime_preflight_v3" or
                    pre_before.get("gate_reasons") != [], "prelaunch board resource gate did not pass")
            pre_stamp = utc_timestamp(pre_before.get("captured_at_utc"))
            post_stamp = utc_timestamp(pre_after.get("captured_at_utc"))
            fail_if(pre_stamp > started_at or post_stamp < ended_at,
                    "board resource snapshot timestamp is outside the CLI interval")
            memory = pre_before.get("memory_kib", {})
            fail_if(memory.get("MemAvailable", 0) < 2_750_000 or
                    memory.get("CmaFree", 0) < 700_000 or
                    memory.get("SwapTotal") != 0 or memory.get("SwapFree") != 0 or
                    pre_before.get("jupyter_active") != "active" or
                    pre_before.get("home_free_bytes", 0) < (1 << 30) or
                    float(pre_before.get("loadavg", "99").split()[0]) > 1.5,
                    "prelaunch board snapshot violates the frozen P2 gate")
            service_states = pre_before.get("systemd_service_states", {})
            jupyter_state = service_states.get("jupyter.service", {})
            fail_if(jupyter_state.get("active_state") != "active" or
                    jupyter_state.get("returncode") != 0 or jupyter_state.get("timed_out") is not False or
                    any(service_states.get(unit, {}).get("active_state") != "inactive" or
                        service_states.get(unit, {}).get("returncode") != 3 or
                        service_states.get(unit, {}).get("timed_out") is not False
                        for unit in ("apt-daily.service", "apt-daily-upgrade.service")),
                    "prelaunch systemd services are active, missing, or unknown")
            fail_if(any(row.get("comm") == "unattended-upgr" and
                        row.get("role") != "shutdown_waiter"
                        for row in pre_before.get("selected_processes", [])),
                    "prelaunch board snapshot has an active or unclassified updater process")
            packagekit = pre_before.get("packagekit_transaction_state", {})
            fail_if(not isinstance(packagekit, dict) or
                    packagekit.get("state") not in ("SERVICE_INACTIVE", "NO_ACTIVE_TRANSACTIONS") or
                    packagekit.get("timed_out") is not False,
                    "prelaunch PackageKit transaction state is active or unknown")
            fail_if(pre_after.get("schema") != "kv260_cpu_p2_textvqa_runtime_preflight_v3" or
                    not isinstance(pre_after.get("gate_reasons"), list) or
                    not isinstance(pre_after.get("systemd_service_states"), dict) or
                    not isinstance(pre_after.get("packagekit_transaction_state"), dict),
                    "post-run board resource snapshot is malformed")
            packagekit_after = pre_after["packagekit_transaction_state"]
            fail_if(packagekit_after.get("state") not in ("SERVICE_INACTIVE", "NO_ACTIVE_TRANSACTIONS") or
                    packagekit_after.get("timed_out") is not False,
                    "post-run PackageKit transaction state is active or unknown")
            result["postflight_gate_reasons"] = pre_after["gate_reasons"]
            result["postflight_resources_remain_within_gates"] = not pre_after["gate_reasons"]
            fail_if(image_after.get("schema") != "kv260_cpu_p2_textvqa_image_post_verification_v1" or
                    image_after.get("question_id") != qid or
                    image_after.get("image_id") != sample["image_id"] or
                    image_after.get("image_path") != execution_paths["image"] or
                    image_after.get("image_sha256") != sample["image_sha256"] or
                    image_after.get("image_bytes") != manifest["images"][sample["image_id"]]["bytes"] or
                    image_after.get("verified_after_cli") is not True or
                    utc_timestamp(image_after.get("verified_at_utc")) < ended_at,
                    "board post-run image immutability check missing or inconsistent")
            runner_path = ROOT / "scripts/run_board_cpu_p2_textvqa.py"
            fail_if(not runner_path.is_file() or state.get("runner_sha256") != sha256(runner_path),
                    "reviewed TextVQA runner identity missing or changed")
            result["execution_provenance_scope"] = "board_runner_records_and_prelaunch_hashes"
        else:
            for key, digest in (("cli", HOST_CLI_SHA256),
                                ("model", MODEL_SHA256), ("mmproj", MMPROJ_SHA256)):
                fail_if(command.get(f"{key}_sha256") != digest or
                        sha256(Path(execution_paths[key])) != digest,
                        f"host {key} file SHA does not match command")
            result["execution_provenance_scope"] = "host_rehearsal_direct_local_file_hashes"
        result["command_input_binding_verified"] = True
        result["resource_gates_verified"] = True
        environment = command.get("environment", {})
        fail_if(not isinstance(environment, dict), "environment record must be object")
        exact_keys(environment, ENVIRONMENT_KEYS, "environment")
        fail_if(environment.get("MTMD_TEST_RESPONSE_MARKER") != "UNSET" or
                environment.get("marker_removed_before_launch") is not True or
                not isinstance(environment.get("marker_was_present_before_removal"), bool),
                "MTMD_TEST_RESPONSE_MARKER absence not recorded at launch")
        result["marker_absence_verified"] = True
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"COMMAND_OR_INPUT_CONTRACT: {exc}")

    clean = (state.get("wrapper_returncode") == 0 and
             state.get("time_child_exit_status") == 0 and
             state.get("execution_complete") is True and
             state.get("raw_copy_complete") is True)
    result["normal_exit"] = clean
    if not clean:
        errors.append("CLI_OR_COPY_NOT_CLEAN")

    stdout = paths["stdout.log"].read_bytes()
    stderr_bytes = paths["stderr.log"].read_bytes()
    try:
        stderr = stderr_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        stderr = ""
        errors.append("STDERR_NOT_UTF8")
    events = inspect_events(stderr)
    result["image_events"] = events
    result["image_processing_verified"] = bool(
        clean and raw_hashes_verified and result.get("command_input_binding_verified") and
        result.get("resource_gates_verified") and
        events["event_predicate_pass"]
    )
    if not result["image_processing_verified"]:
        errors.append("IMAGE_PROCESSING_UNVERIFIED")
    candidate, parse_error = extract_stdout(stdout)
    result["stdout_candidate_untrusted"] = candidate
    if parse_error:
        errors.append(parse_error)
    if not errors:
        result["prediction"] = candidate
        result["answer_parse_ok"] = True
        result["soft_accuracy"] = evaluator.eval_pred_list([
            {"pred_answer": candidate, "gt_answers": sample["answers"]}
        ])
        result["normalized_prediction"] = evaluator.answer_processor(candidate)
        result["status"] = "PARSED_DEVELOPMENT_CASE"
    else:
        result["prediction"] = ""
        result["normalized_prediction"] = evaluator.answer_processor("")
        result["status"] = "ATTEMPTED_SCORED_EMPTY"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("pilot", "rehearsal"), required=True)
    parser.add_argument("--case", action="append", required=True, metavar="QID=RAW_DIR")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    if sha256(manifest_path) != MANIFEST_SHA256:
        raise SystemExit("refusing changed TextVQA development manifest")
    manifest = read_json(manifest_path)
    if manifest.get("kind") != "textvqa_v0.5.1_validation_development_subset":
        raise SystemExit("wrong dataset kind")
    mapping: dict[int, dict[str, Any]] = {}
    for sample in manifest["samples"]:
        if sample["question_id"] in PILOT_QIDS:
            if sample["question_id"] in mapping:
                raise SystemExit("duplicate pilot qid in manifest")
            if not isinstance(sample.get("answers"), list) or len(sample["answers"]) != 10:
                raise SystemExit("TextVQA pilot needs ten host-only reference answers")
            mapping[sample["question_id"]] = sample
    if set(mapping) != set(PILOT_QIDS):
        raise SystemExit("pilot qid missing from manifest")

    cases: dict[int, Path] = {}
    for item in args.case:
        if "=" not in item:
            raise SystemExit("--case must be QID=RAW_DIR")
        qid_string, dirname = item.split("=", 1)
        qid = int(qid_string)
        raw_dir = Path(dirname).resolve()
        if (qid not in PILOT_QIDS or qid in cases or not raw_dir.is_relative_to(RAW_ROOT)
                or raw_dir.parent != RAW_ROOT):
            raise SystemExit("duplicate/unknown qid or raw path outside experiments/raw")
        if args.mode == "pilot" and raw_dir != RAW_ROOT / f"kv260_cpu_p2_tvqa_q{qid}_r01":
            raise SystemExit("pilot qid does not match the frozen direct-child board raw run directory")
        cases[qid] = raw_dir
    if len(set(cases.values())) != len(cases):
        raise SystemExit("same raw directory cannot serve multiple qids")
    if args.mode == "pilot" and set(cases) != set(PILOT_QIDS):
        raise SystemExit("pilot mode requires exactly three qid raw directories")
    if args.mode == "rehearsal" and len(cases) != 1:
        raise SystemExit("rehearsal mode requires one raw directory")

    out = args.output.resolve()
    if not out.is_relative_to(DERIVED_ROOT) or out.suffix != ".json":
        raise SystemExit("output must be a JSON file under experiments/derived")
    if out.exists():
        raise SystemExit(f"refusing to overwrite derived result: {out}")
    evaluator_path = ROOT / "scripts/vendor/m4c_evaluators.py"
    if sha256(evaluator_path) != EVALUATOR_SHA256:
        raise SystemExit("pinned MMF evaluator SHA mismatch")
    sys.path.insert(0, str(evaluator_path.parent))
    from m4c_evaluators import TextVQAAccuracyEvaluator
    evaluator = TextVQAAccuracyEvaluator()

    details = [inspect_case(qid, cases[qid], mapping[qid], manifest, MANIFEST_SHA256,
                            manifest_path, evaluator,
                            args.mode)
               for qid in PILOT_QIDS if qid in cases]
    attempted = [case for case in details if case["attempted"] is True]
    unknown = [case for case in details if case["attempted"] is None]
    output = {
        "schema": "kv260_cpu_p2_textvqa_split_stream_host_adapter_v2",
        "mode": args.mode,
        "adapter_path": str(Path(__file__).resolve()),
        "adapter_sha256": sha256(Path(__file__).resolve()),
        "manifest_path": str(manifest_path),
        "manifest_sha256": MANIFEST_SHA256,
        "evaluator_path": str(evaluator_path),
        "evaluator_sha256": EVALUATOR_SHA256,
        "development_only": True,
        "planned_qids": list(PILOT_QIDS),
        "reported_case_count": len(details),
        "attempt_state_unknown_count": len(unknown),
        "attempted_count": len(attempted) if not unknown else None,
        "normal_exit_count": sum(case["normal_exit"] for case in details),
        "parseable_answer_count": sum(case["answer_parse_ok"] for case in details),
        "image_processing_verified_count": sum(case["image_processing_verified"] for case in details),
        "attempted_score_denominator": len(attempted) if not unknown else None,
        "attempted_score_sum": sum(case["soft_accuracy"] for case in attempted)
        if not unknown else None,
        "not_attempted_cases_have_no_score": True,
        "failed_attempts_use_empty_prediction_and_zero_score": True,
        "pilot_coverage_complete": args.mode == "pilot" and not unknown and len(attempted) == 3,
        "cases": details,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"output": str(out), "attempted": output["attempted_count"],
                      "parsed": output["parseable_answer_count"],
                      "image_verified": output["image_processing_verified_count"]}))
    return 0 if not unknown and all(case["attempted"] is False or case["answer_parse_ok"]
                                    for case in details) else 1


if __name__ == "__main__":
    raise SystemExit(main())
