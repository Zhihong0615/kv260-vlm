#!/usr/bin/env python3
"""Plan or run one bounded KV260 CPU-only TextVQA development request.

The default path is a local dry plan. Execution requires an earlier successful
synthetic ALPHA check, hash-bound independent reviews, a confirmed owner window,
and fresh board resource gates. One invocation starts at most one real image.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import getpass
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "experiments/raw"
DERIVED_ROOT = ROOT / "experiments/derived"
MANIFEST_PATH = ROOT / "datasets/textvqa_v0.5.1_dev_50_seed20260923/manifest.json"
ATTESTATION_PATH = RAW_ROOT / "kv260_cpu_p2_baseline_round01/cpu_build_attestation_v1.json"
PREFLIGHT_SOURCE = ROOT / "scripts/board_cpu_preflight_remote.py"
PARSER_PATH = ROOT / "scripts/parse_board_textvqa_pilot.py"
ADAPTER_REVIEW = ROOT / "reviews/kv260_cpu_p2_textvqa_output_contract_v2_independent_review.md"
RUNNER_REVIEW = ROOT / "reviews/board_cpu_p2_textvqa_runner_independent_review.md"
PINNED_RUNTIME_COMMIT = "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2"
MANIFEST_SHA256 = "62c32317029e40895ffd8e476e8a845416dac9d1d9490dfd6efb5f28a4374962"
MODEL_SHA256 = "8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773"
MMPROJ_SHA256 = "ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293"
CLI_SHA256 = "84bfa2f5f91f13503b5a1349e05594cda30c01613227187cfb9e48e7b805f1d7"
ATTESTATION_SHA256 = "48cfe4fa9c5a4647ecb193ca91c6eaa07a539abd8addb2407ec14bf4d87755c2"
PREFLIGHT_SOURCE_SHA256 = "16d5bf8a2158dd16f409fb6708fe60440cc95585e98f41044ce5732b192c9616"
BOARD_BASE = "/home/ubuntu/kv260-vlm-p2-cpu"
TIMEOUT_EXECUTABLE_PATH = "/usr/bin/timeout"
RUN_IDS = {qid: f"kv260_cpu_p2_tvqa_q{qid}_r01" for qid in (38299, 37804, 35419)}
ORDER = (38299, 37804, 35419)
SYSTEMD_UNITS = ("jupyter.service", "apt-daily.service", "apt-daily-upgrade.service")
MIN_MEM_AVAILABLE_KIB = 2_750_000
MIN_CMA_FREE_KIB = 700_000
MIN_HOME_FREE_BYTES = 1 << 30
MAX_LOAD1 = 1.5
MAX_BUSY_CORES_PER_PROCESS = 0.25
PROCESS_CPU_SAMPLE_WAIT_SECONDS = 2.0
CLI_TIMEOUT_SECONDS = 300
REMOTE_WATCHDOG_SECONDS = 540
HOST_WAIT_SECONDS = 600
RUN_ID_RE = re.compile(r"[a-z][a-z0-9_-]{7,79}\Z")


@dataclass(frozen=True)
class HostOrchestrationOps:
    """Injectable boundaries for the production host request state machine."""

    assess_previous: Callable[[int], bool]
    begin: Callable[[], None]
    preflight: Callable[[], dict[str, Any] | None]
    stage: Callable[[], dict[str, Any] | None]
    launch_worker: Callable[[], dict[str, Any]]
    query_status: Callable[[], dict[str, Any]]
    copy_and_verify: Callable[[], dict[str, Any]]
    score: Callable[[], dict[str, Any]]
    record_nonstart: Callable[[int, str, str | None], None]
    record_state: Callable[[str, dict[str, Any]], None]


def run_host_orchestration(qid: int, order: tuple[int, ...], run_ids: dict[int, str],
                           ops: HostOrchestrationOps) -> dict[str, Any]:
    """Run one qid through the production orchestration decisions and injected I/O."""
    index = order.index(qid)

    def record_nonstarts(qids: tuple[int, ...] | list[int], reason: str,
                         prior_run_id: str | None) -> None:
        for nonstart_qid in qids:
            ops.record_nonstart(nonstart_qid, reason, prior_run_id)

    for previous_qid in order[:index]:
        try:
            previous_passed = ops.assess_previous(previous_qid)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            record_nonstarts(order[index:], "PRIOR_CASE_UNRESOLVED", run_ids[previous_qid])
            return {"status": "PRIOR_CASE_UNRESOLVED", "unresolved_qid": previous_qid,
                    "new_qid_not_started": qid,
                    "assessment_error": f"{type(exc).__name__}: {exc}", "returncode": 1}
        if previous_passed is not True:
            record_nonstarts(order[index:], "PRIOR_CASE_FAILED", run_ids[previous_qid])
            return {"status": "PRIOR_CASE_FAILED", "failed_qid": previous_qid,
                    "new_qid_not_started": qid, "returncode": 1}

    ops.begin()
    failure = ops.preflight()
    if failure is not None:
        fields = failure.get("fields", {})
        phase = failure.get("phase", "preflight")
        reason = failure.get("non_start_reason", "PREFLIGHT_BLOCKED")
        ops.record_state(phase, fields)
        record_nonstarts(order[index:], reason, None)
        return {"status": fields.get("status", "PRECHECK_BLOCKED"),
                "phase": phase, "returncode": 1}
    failure = ops.stage()
    if failure is not None:
        fields = failure.get("fields", {})
        phase = failure.get("phase", "stage")
        reason = failure.get("non_start_reason", "INPUT_UNAVAILABLE")
        ops.record_state(phase, fields)
        record_nonstarts(order[index:], reason, None)
        return {"status": fields.get("status", "INPUT_UNAVAILABLE"),
                "phase": phase, "returncode": 1}

    worker_attempt = ops.launch_worker()
    if not isinstance(worker_attempt, dict):
        worker_attempt = {"timed_out": False, "remote_result": None}
    worker_timed_out = worker_attempt.get("timed_out") is True
    remote_result = worker_attempt.get("remote_result")
    if not worker_timed_out:
        if remote_result == {"status": "REMOTE_LOCK_BUSY", "cli_started": False}:
            fields = {"status": "REMOTE_LOCK_BUSY", "board_inference_attempted": False}
            ops.record_state("remote_runner_lock_busy", fields)
            ops.record_nonstart(qid, "RUNNER_LOCK_BUSY", None)
            record_nonstarts(order[index + 1:], "PRIOR_CASE_UNRESOLVED", run_ids[qid])
            return {"status": "REMOTE_LOCK_BUSY", "returncode": 1}
        if isinstance(remote_result, dict) and remote_result.get("status") == "PRECHECK_BLOCKED":
            fields = {"status": "PRECHECK_BLOCKED", "board_inference_attempted": False}
            ops.record_state("remote_precheck_blocked", fields)
            record_nonstarts(order[index:], "PREFLIGHT_BLOCKED", None)
            return {"status": "PRECHECK_BLOCKED", "returncode": 1}
        if not isinstance(remote_result, dict) or remote_result.get("status") != "REQUEST_FINISHED":
            ops.record_state("remote_unresolved", {"status": "REMOTE_STATE_UNKNOWN"})
            record_nonstarts(order[index + 1:], "PRIOR_CASE_UNRESOLVED", run_ids[qid])
            return {"status": "REMOTE_STATE_UNKNOWN", "returncode": 1}

    try:
        status_reply = ops.query_status()
    except (OSError, subprocess.TimeoutExpired) as exc:
        status_reply = {"returncode": None, "remote_status": None,
                        "transport_error": repr(exc)}
    remote_status = status_reply.get("remote_status") if isinstance(status_reply, dict) else None
    status_complete = (
        isinstance(status_reply, dict) and status_reply.get("returncode") == 0 and
        isinstance(remote_status, dict) and
        remote_status.get("state") == "COMPLETE" and
        remote_status.get("run_id") == run_ids[qid] and
        remote_status.get("run_dir_exists") is True and
        remote_status.get("runner_lock_free") is True and
        remote_status.get("completion_marker_valid") is True and
        remote_status.get("board_cli_processes") == [] and
        remote_status.get("unreadable_processes") == []
    )
    if not status_complete:
        fields = {"status": "REMOTE_STATE_UNKNOWN",
                  "remote_state": (remote_status.get("state")
                                   if isinstance(remote_status, dict) else "REMOTE_STATE_UNKNOWN"),
                  "remote_status_check_attempted_after_worker_timeout": worker_timed_out}
        if isinstance(status_reply, dict) and status_reply.get("returncode") is not None:
            fields["remote_status_returncode"] = status_reply["returncode"]
        if isinstance(status_reply, dict) and status_reply.get("transport_error"):
            fields["remote_status_transport_error"] = status_reply["transport_error"]
        ops.record_state("remote_state_unknown", fields)
        record_nonstarts(order[index + 1:], "PRIOR_CASE_UNRESOLVED", run_ids[qid])
        return {"status": "REMOTE_STATE_UNKNOWN", "returncode": 1}

    copied = ops.copy_and_verify()
    if not isinstance(copied, dict) or copied.get("verified") is not True:
        fields = {"status": ("REMOTE_STATE_UNKNOWN" if worker_timed_out
                             else "EVIDENCE_COPY_INCOMPLETE")}
        if worker_timed_out:
            fields["timeout_recovery_failed_at"] = (
                copied.get("failure_at", "raw_copy") if isinstance(copied, dict) else "raw_copy"
            )
        phase = copied.get("phase", "copy_incomplete") if isinstance(copied, dict) else "copy_incomplete"
        ops.record_state(phase, fields)
        record_nonstarts(order[index + 1:], "PRIOR_CASE_UNRESOLVED", run_ids[qid])
        return {"status": fields["status"], "returncode": 1}

    assessment = ops.score()
    passed = (isinstance(assessment, dict) and assessment.get("answer_parse_ok") is True and
              assessment.get("image_processing_verified") is True)
    stop_after = isinstance(assessment, dict) and assessment.get("stop_after_this_request") is True
    ops.record_state("final", {"stop_after_this_request": not passed or stop_after})
    if not passed:
        record_nonstarts(order[index + 1:], "PRIOR_CASE_FAILED", run_ids[qid])
        return {"status": "CASE_FAILED", "returncode": 1}
    if stop_after:
        record_nonstarts(order[index + 1:], "PRIOR_CASE_STOP_RULE", run_ids[qid])
        return {"status": "STOP_RULE", "returncode": 1}
    return {"status": "COMPLETE", "returncode": 0}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def captured_output_bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    return value.encode("utf-8", errors="replace") if isinstance(value, str) else value


def persist_transport_failure(raw_dir: Path, stem: str, exc: Exception) -> dict[str, Any]:
    """Preserve partial stdout/stderr when a bounded transport operation fails."""
    (raw_dir / f"{stem}.stdout").write_bytes(captured_output_bytes(getattr(exc, "output", None)))
    (raw_dir / f"{stem}.stderr").write_bytes(captured_output_bytes(getattr(exc, "stderr", None)))
    return {f"{stem}_transport_error": repr(exc),
            f"{stem}_timed_out": isinstance(exc, subprocess.TimeoutExpired)}


def systemd_gate_reasons(states: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    jupyter = states.get("jupyter.service", {}) if isinstance(states, dict) else {}
    if (jupyter.get("active_state") != "active" or jupyter.get("returncode") != 0 or
            jupyter.get("timed_out") is not False):
        reasons.append("JUPYTER")
    for unit in ("apt-daily.service", "apt-daily-upgrade.service"):
        state = states.get(unit, {}) if isinstance(states, dict) else {}
        if (state.get("active_state") != "inactive" or state.get("returncode") != 3 or
                state.get("timed_out") is not False):
            reasons.append("PACKAGE_UPGRADE_SERVICE")
    return reasons


def preflight_resource_gate_reasons(snapshot: dict[str, Any]) -> list[str]:
    """Apply the CPU request gates to one schema-validated remote snapshot."""
    reasons: list[str] = []
    memory = snapshot.get("memory_kib", {})
    if snapshot.get("arch", "").lower() != "aarch64" or snapshot.get("cpu_count") != 4:
        reasons.append("BOARD_IDENTITY")
    if memory.get("MemAvailable", 0) < MIN_MEM_AVAILABLE_KIB:
        reasons.append("MEMAVAILABLE")
    if memory.get("CmaFree", 0) < MIN_CMA_FREE_KIB:
        reasons.append("CMAFREE")
    if memory.get("SwapTotal") != 0 or memory.get("SwapFree") != 0:
        reasons.append("SWAP")
    if snapshot.get("home_free_bytes", 0) < MIN_HOME_FREE_BYTES:
        reasons.append("DISK")
    reasons.extend(systemd_gate_reasons(snapshot.get("systemd_service_states", {})))
    try:
        load1 = float(snapshot["loadavg"].split()[0])
    except (AttributeError, KeyError, IndexError, TypeError, ValueError):
        load1 = float("nan")
    if not math.isfinite(load1) or load1 < 0:
        reasons.append("LOAD_STATE_UNKNOWN")
    elif load1 > MAX_LOAD1:
        reasons.append("LOAD")
    timeout_identity = snapshot.get("timeout_executable")
    if (not isinstance(timeout_identity, dict) or
            set(timeout_identity) != {"path", "resolved_path", "sha256", "usable"} or
            timeout_identity.get("path") != TIMEOUT_EXECUTABLE_PATH or
            not isinstance(timeout_identity.get("resolved_path"), str) or
            not Path(timeout_identity["resolved_path"]).is_absolute() or
            not isinstance(timeout_identity.get("sha256"), str) or
            not re.fullmatch(r"[0-9a-f]{64}", timeout_identity["sha256"]) or
            timeout_identity.get("usable") is not True):
        reasons.append("TIMEOUT_EXECUTABLE_UNKNOWN")
    processes = snapshot.get("selected_processes")
    if not isinstance(processes, list) or any(
            not isinstance(row, dict) or not isinstance(row.get("comm"), str) or
            not isinstance(row.get("pid"), int) or isinstance(row.get("pid"), bool) or
            row.get("pid", 0) <= 0 or not isinstance(row.get("uid"), int) or
            isinstance(row.get("uid"), bool) or row.get("uid", -1) < 0 or
            not isinstance(row.get("role"), str) or
            not isinstance(row.get("cpu_ticks_delta"), int) or
            isinstance(row.get("cpu_ticks_delta"), bool) or row.get("cpu_ticks_delta", -1) < 0 or
            not isinstance(row.get("cpu_sample_interval_seconds"), (int, float)) or
            isinstance(row.get("cpu_sample_interval_seconds"), bool) or
            not math.isfinite(row.get("cpu_sample_interval_seconds", float("nan"))) or
            not 0 < row.get("cpu_sample_interval_seconds", 0) <= 5.0 or
            not isinstance(row.get("cpu_cores"), (int, float)) or
            isinstance(row.get("cpu_cores"), bool) or not math.isfinite(row.get("cpu_cores")) or
            row.get("cpu_cores", -1) < 0
            for row in processes):
        reasons.append("PROCESS_STATE_UNKNOWN")
    else:
        if len({row["pid"] for row in processes}) != len(processes):
            reasons.append("PROCESS_STATE_UNKNOWN")
        forbidden_names = {"llama-mtmd-cli", "llama-server", "vivado", "vitis_hls", "xbutil",
                            "cmake", "ninja", "cc1", "cc1plus", "apt", "apt-get", "dpkg",
                            "dpkg-deb", "rsync"}
        if any(row["comm"] in forbidden_names or
               (row["comm"] == "unattended-upgr" and row.get("role") != "shutdown_waiter")
               for row in processes):
            reasons.append("BUSY_PROCESS")
    cpu_rows = snapshot.get("process_cpu_rows")
    cpu_rows_well_formed = isinstance(cpu_rows, list) and not any(
            not isinstance(row, dict) or not isinstance(row.get("comm"), str) or
            not isinstance(row.get("pid"), int) or isinstance(row.get("pid"), bool) or
            row.get("pid", 0) <= 0 or
            not isinstance(row.get("cpu_ticks_delta"), int) or
            isinstance(row.get("cpu_ticks_delta"), bool) or row.get("cpu_ticks_delta", -1) < 0 or
            not isinstance(row.get("cpu_sample_interval_seconds"), (int, float)) or
            isinstance(row.get("cpu_sample_interval_seconds"), bool) or
            not math.isfinite(row.get("cpu_sample_interval_seconds", float("nan"))) or
            not 0 < row.get("cpu_sample_interval_seconds", 0) <= 5.0 or
            not isinstance(row.get("cpu_cores"), (int, float)) or
            isinstance(row.get("cpu_cores"), bool) or not math.isfinite(row.get("cpu_cores")) or
            row.get("cpu_cores", -1) < 0
            for row in cpu_rows)
    if not cpu_rows_well_formed:
        reasons.append("PROCESS_STATE_UNKNOWN")
    elif len({row["pid"] for row in cpu_rows}) != len(cpu_rows):
        reasons.append("PROCESS_STATE_UNKNOWN")
    elif (not isinstance(snapshot.get("preflight_pid"), int) or
          isinstance(snapshot.get("preflight_pid"), bool) or
          snapshot.get("preflight_pid") not in {row["pid"] for row in cpu_rows}):
        reasons.append("PROCESS_STATE_UNKNOWN")
    if (snapshot.get("process_cpu_sample_state") != "OK" or
            snapshot.get("process_cpu_sample_wait_seconds") != PROCESS_CPU_SAMPLE_WAIT_SECONDS or
            not isinstance(snapshot.get("process_cpu_sample_interval_seconds"), (int, float)) or
            isinstance(snapshot.get("process_cpu_sample_interval_seconds"), bool) or
            not math.isfinite(snapshot.get("process_cpu_sample_interval_seconds", float("nan"))) or
            not 2.0 <= snapshot.get("process_cpu_sample_interval_seconds", 0) <= 5.0 or
            not isinstance(snapshot.get("process_cpu_sample_errors"), list) or
            snapshot.get("process_cpu_sample_errors")):
        reasons.append("PROCESS_STATE_UNKNOWN")
    elif cpu_rows_well_formed:
        preflight_pid = snapshot.get("preflight_pid")
        if any(row["pid"] != preflight_pid and
               row["cpu_cores"] >= MAX_BUSY_CORES_PER_PROCESS for row in cpu_rows):
            reasons.append("BUSY_CPU")
    packagekit = snapshot.get("packagekit_transaction_state", {})
    if (not isinstance(packagekit, dict) or
            packagekit.get("state") not in ("SERVICE_INACTIVE", "NO_ACTIVE_TRANSACTIONS") or
            packagekit.get("timed_out") is not False):
        reasons.append("PACKAGEKIT_STATE")
    return reasons


def write_record(directory: Path, phase: str, value: dict[str, Any]) -> None:
    write_json(directory / f"runner_record_{phase}.json", value)


def checked_raw_path(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.parent != RAW_ROOT.resolve():
        raise ValueError("TextVQA case directories must be direct children of experiments/raw")
    if resolved.exists():
        raise ValueError("refusing to reuse existing append-only raw directory: " + str(resolved))
    return resolved


def load_manifest() -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    if sha256_file(MANIFEST_PATH) != MANIFEST_SHA256:
        raise ValueError("TextVQA development manifest SHA mismatch")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("kind") != "textvqa_v0.5.1_validation_development_subset":
        raise ValueError("unexpected TextVQA manifest kind")
    samples: dict[int, dict[str, Any]] = {}
    for sample in manifest["samples"]:
        qid = sample["question_id"]
        if qid in RUN_IDS:
            if qid in samples:
                raise ValueError(f"duplicate qid {qid} in development manifest")
            image = manifest["images"][sample["image_id"]]
            if (not isinstance(sample["answers"], list) or len(sample["answers"]) != 10 or
                    not re.fullmatch(r"[0-9a-f]{64}", image["sha256"])):
                raise ValueError(f"invalid frozen development sample {qid}")
            samples[qid] = {**sample, "image_bytes": image["bytes"],
                             "image_relative_path": image["path"]}
    if tuple(qid for qid in ORDER if qid in samples) != ORDER:
        raise ValueError("one or more frozen TextVQA qids are absent")
    return manifest, samples


def alpha_proof(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError("--alpha-proof may not be a symlink")
    proof_dir = path.resolve()
    if proof_dir.parent != RAW_ROOT.resolve() or not proof_dir.is_dir():
        raise ValueError("--alpha-proof must be a completed direct-child experiments/raw directory")
    record_path = proof_dir / "run.json"
    status_path = proof_dir / "remote_status.json"
    copy_manifest_path = proof_dir / "raw_copy_manifest.json"
    if not all(p.is_file() for p in (record_path, status_path, copy_manifest_path)):
        raise ValueError("synthetic ALPHA proof lacks final run/status/copy records")
    if any(p.is_symlink() for p in (record_path,status_path,copy_manifest_path)):
        raise ValueError("synthetic ALPHA proof files may not be symlinks")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))
    copied = json.loads(copy_manifest_path.read_text(encoding="utf-8"))
    remote = record.get("remote_result") or {}
    board_result = proof_dir / "board_complete_snapshot/result.json"
    if not board_result.is_file() or board_result.is_symlink():
        raise ValueError("synthetic ALPHA board result is missing")
    board = json.loads(board_result.read_text(encoding="utf-8"))
    if (record.get("status") != "SYNTHETIC_WIRING_PASS" or
            record.get("board_inference_attempted") is not True or
            record.get("remote_state") != "COMPLETE" or
            record.get("raw_copy_returncode") != 0 or
            record.get("raw_copy_manifest_mismatch") or
            status.get("state") != "COMPLETE" or
            status.get("completion_marker_valid") is not True or
            not copied or board.get("status") != "SYNTHETIC_WIRING_PASS" or
            board.get("wrapper_returncode") != 0 or
            board.get("time_child_exit_status") != 0 or
            board.get("remote_process_cleanup_verified") is not True or
            "inference_started_at_utc" not in board):
        raise ValueError("synthetic ALPHA evidence does not prove one clean, copied board request")
    return {"path": str(proof_dir), "run_id": record.get("run_id"),
            "run_json_sha256": sha256_file(record_path),
            "board_result_sha256": sha256_file(board_result),
            "remote_status_sha256": sha256_file(status_path),
            "copy_manifest_sha256": sha256_file(copy_manifest_path)}


def review_gate(path: Path, subject_sha: str, label: str) -> dict[str, str]:
    if not path.is_file():
        raise ValueError(f"missing independent {label} review: {path}")
    body = path.read_text(encoding="utf-8")
    if subject_sha not in body:
        raise ValueError(f"{label} review does not bind current file SHA {subject_sha}")
    if not re.search(r"(?im)^review_mode:\s*independent_static\s*$", body):
        raise ValueError(f"{label} review is not explicitly marked independent_static")
    if not re.search(r"(?im)^reviewer_role:\s*independent_reviewer\s*$", body):
        raise ValueError(f"{label} review does not identify an independent reviewer")
    if "SELF_REVIEW_ONLY" in body:
        raise ValueError(f"{label} review is self-review-only")
    for level in ("P0", "P1"):
        if not re.search(rf"{level}\s*[:：]\s*0\b", body):
            raise ValueError(f"{label} review does not report {level}=0")
    return {"path": str(path), "sha256": sha256_file(path), "subject_sha256": subject_sha}


def static_prerequisites(alpha_path: Path) -> dict[str, Any]:
    manifest, _ = load_manifest()
    if sha256_file(PREFLIGHT_SOURCE) != PREFLIGHT_SOURCE_SHA256:
        raise ValueError("read-only board preflight script SHA mismatch")
    if sha256_file(ATTESTATION_PATH) != ATTESTATION_SHA256:
        raise ValueError("successful board CPU build attestation SHA mismatch")
    attestation = json.loads(ATTESTATION_PATH.read_text(encoding="utf-8"))
    if (attestation.get("schema") != "kv260_cpu_p2_build_attestation_v1" or
            attestation.get("runtime_commit") != PINNED_RUNTIME_COMMIT or
            attestation.get("build_exit_code") != 0 or
            attestation.get("cli_sha256") != CLI_SHA256):
        raise ValueError("board CPU build attestation does not bind the pinned successful build")
    parser_sha = sha256_file(PARSER_PATH)
    runner_sha = sha256_file(Path(__file__).resolve())
    return {
        "manifest_sha256": MANIFEST_SHA256,
        "runtime_commit": PINNED_RUNTIME_COMMIT,
        "model_sha256": MODEL_SHA256,
        "mmproj_sha256": MMPROJ_SHA256,
        "cli_sha256": CLI_SHA256,
        "build_attestation_sha256": ATTESTATION_SHA256,
        "preflight_source_sha256": PREFLIGHT_SOURCE_SHA256,
        "parser_sha256": parser_sha,
        "runner_sha256": runner_sha,
        "alpha_proof": alpha_proof(alpha_path),
        "adapter_review": review_gate(ADAPTER_REVIEW, parser_sha, "TextVQA adapter"),
        "runner_review": review_gate(RUNNER_REVIEW, runner_sha, "TextVQA runner"),
        "manifest_sample_count": len(manifest["samples"]),
    }


def sha_argv(argv: list[str]) -> str:
    return hashlib.sha256(json.dumps(argv, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


REMOTE_WORKER = r'''
import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/home/ubuntu/kv260-vlm-p2-cpu")
RUNS = BASE / "runs"
TIMEOUT_EXECUTABLE_PATH = "/usr/bin/timeout"
ACTIVE = None
TERMINATION_UNPROVEN = False

def utc(): return datetime.now(timezone.utc).isoformat()
def systemd_state(unit):
    try:
        result=subprocess.run(["systemctl","is-active",unit],capture_output=True,text=True,check=False,timeout=5)
        return {"active_state":result.stdout.strip() or "UNKNOWN","returncode":result.returncode,"timed_out":False}
    except subprocess.TimeoutExpired:
        return {"active_state":"UNKNOWN","returncode":None,"timed_out":True}
    except OSError as exc:
        return {"active_state":"UNKNOWN","returncode":None,"timed_out":False,"error":type(exc).__name__}
def collect_systemd_states():
    return {unit:systemd_state(unit) for unit in ("jupyter.service","apt-daily.service","apt-daily-upgrade.service","packagekit.service")}
def packagekit_transaction_state(services):
    state=services.get("packagekit.service",{})
    if state.get("active_state")=="inactive" and state.get("returncode")==3 and state.get("timed_out") is False:
        return {"state":"SERVICE_INACTIVE","transaction_ids":[],"returncode":None,"timed_out":False}
    if state.get("active_state")!="active" or state.get("returncode")!=0 or state.get("timed_out") is not False:
        return {"state":"UNKNOWN","transaction_ids":[],"returncode":None,"timed_out":False}
    try:
        result=subprocess.run(["busctl","--system","call","org.freedesktop.PackageKit",
                               "/org/freedesktop/PackageKit","org.freedesktop.PackageKit",
                               "GetTransactionList"],capture_output=True,text=True,check=False,timeout=10)
    except subprocess.TimeoutExpired:
        return {"state":"UNKNOWN","transaction_ids":[],"returncode":None,"timed_out":True}
    except OSError as exc:
        return {"state":"UNKNOWN","transaction_ids":[],"returncode":None,"timed_out":False,
                "error":type(exc).__name__}
    words=result.stdout.split()
    if result.returncode!=0 or len(words)<2 or words[0]!="ao":
        return {"state":"UNKNOWN","transaction_ids":[],"returncode":result.returncode,"timed_out":False}
    try: count=int(words[1])
    except ValueError: count=-1
    if count<0 or len(words)!=count+2:
        return {"state":"UNKNOWN","transaction_ids":[],"returncode":result.returncode,"timed_out":False}
    tids=words[2:]
    return {"state":"NO_ACTIVE_TRANSACTIONS" if not tids else "ACTIVE_TRANSACTIONS",
            "transaction_ids":tids,"returncode":result.returncode,"timed_out":False}
def systemd_gate_reasons(states):
    reasons=[]
    j=states.get("jupyter.service",{}) if isinstance(states,dict) else {}
    if j.get("active_state")!="active" or j.get("returncode")!=0 or j.get("timed_out") is not False:
        reasons.append("JUPYTER")
    for unit in ("apt-daily.service","apt-daily-upgrade.service"):
        state=states.get(unit,{}) if isinstance(states,dict) else {}
        if state.get("active_state")!="inactive" or state.get("returncode")!=3 or state.get("timed_out") is not False:
            reasons.append("PACKAGE_UPGRADE_SERVICE")
    return reasons
def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def timeout_executable_identity():
    identity={"path":TIMEOUT_EXECUTABLE_PATH,"resolved_path":None,"sha256":None,"usable":False}
    path=Path(TIMEOUT_EXECUTABLE_PATH)
    try:
        identity["resolved_path"]=str(path.resolve(strict=True))
        if not path.is_file() or not os.access(path,os.X_OK): return identity
        identity["sha256"]=sha_file(path); identity["usable"]=True
    except (OSError,RuntimeError): pass
    return identity
def timeout_provenance_fields(expected, observed, verified, checked_at):
    return {"timeout_executable_path":expected.get("path"),
            "timeout_executable_resolved_path":expected.get("resolved_path"),
            "timeout_executable_sha256":expected.get("sha256"),
            "timeout_executable_recheck_path":observed.get("path"),
            "timeout_executable_recheck_resolved_path":observed.get("resolved_path"),
            "timeout_executable_recheck_sha256":observed.get("sha256"),
            "timeout_executable_identity_verified":verified,
            "timeout_executable_rechecked_at_utc":checked_at}
def save(path,obj):
    with Path(path).open("x",encoding="utf-8") as f:
        json.dump(obj,f,ensure_ascii=False,sort_keys=True,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
def proc_rows():
    rows={}
    for e in Path("/proc").iterdir():
        if not e.name.isdigit(): continue
        try:
            raw=(e/"stat").read_text(); tail=raw[raw.rfind(")")+2:].split()
            ticks=int(tail[11])+int(tail[12]); name=(e/"comm").read_text().strip()
            status=(e/"status").read_text().splitlines()
            uid=int(next(x for x in status if x.startswith("Uid:")).split()[1])
            cmd=(e/"cmdline").read_bytes().replace(b"\0",b" ").decode(errors="replace").lower()
            role="process"
            if name=="unattended-upgr":
                argv=[arg.decode(errors="replace") for arg in (e/"cmdline").read_bytes().split(b"\0") if arg]
                role=("shutdown_waiter" if len(argv)>=2 and argv[-2:]==[
                    "/usr/share/unattended-upgrades/unattended-upgrade-shutdown","--wait-for-signal"]
                    else "unattended_upgrade")
            rows[int(e.name)]={"ticks":ticks,"comm":name,"uid":uid,"cmd":cmd,"role":role}
        except (OSError,ValueError,IndexError,StopIteration): continue
    return rows
def snapshot():
    mem={}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k,v=line.split(":",1)
        if k in ("MemAvailable","CmaFree","SwapTotal","SwapFree","MemTotal"): mem[k]=int(v.strip().split()[0])
    vms={}
    for line in Path("/proc/vmstat").read_text().splitlines():
        k,v=line.split()
        if k in ("oom_kill","pgmajfault","pswpin","pswpout"): vms[k]=int(v)
    services=collect_systemd_states()
    packagekit=packagekit_transaction_state(services)
    j=services["jupyter.service"]
    sv=os.statvfs(str(Path.home()))
    rows=proc_rows()
    interesting={"unattended-upgr","apt","apt-get","dpkg","dpkg-deb","packagekitd",
                 "llama-mtmd-cli","llama-server","vivado","vitis_hls","xbutil","cmake",
                 "ninja","cc1","cc1plus","gcc","g++","make","rsync"}
    procs=[{"pid":p,"uid":r["uid"],"comm":r["comm"],"role":r["role"]} for p,r in rows.items() if r["comm"] in interesting]
    return {"schema":"kv260_cpu_p2_textvqa_runtime_preflight_v3",
            "captured_at_utc":utc(),"scope":"read-only bounded CPU-only TextVQA preflight",
            "arch":__import__("platform").machine(),"cpu_count":os.cpu_count(),"memory_kib":mem,
            "vmstat_global":vms,"home_free_bytes":sv.f_bavail*sv.f_frsize,
            "loadavg":Path("/proc/loadavg").read_text().strip(),"systemd_service_states":services,
            "jupyter_active":j["active_state"],"jupyter_returncode":j["returncode"],
            "packagekit_transaction_state":packagekit,
            "timeout_executable":timeout_executable_identity(),
            "selected_processes":procs,"process_count":len(rows),
            "cpu_frequency_khz":{p.name:int((p/"cpufreq/scaling_cur_freq").read_text()) for p in sorted(Path("/sys/devices/system/cpu").glob("cpu[0-9]*")) if (p/"cpufreq/scaling_cur_freq").is_file()},
            "thermal_c":{z.name:round(int((z/"temp").read_text())/1000,3) for z in sorted(Path("/sys/class/thermal").glob("thermal_zone*")) if (z/"temp").is_file()}}
def gate(s, pre, before=None):
    reasons=[]; m=s["memory_kib"]
    if s["arch"].lower()!="aarch64" or s["cpu_count"]!=4: reasons.append("BOARD_IDENTITY")
    if m.get("MemAvailable",0)<CONFIG["min_mem_available_kib"]: reasons.append("MEMAVAILABLE")
    if m.get("CmaFree",0)<CONFIG["min_cma_free_kib"]: reasons.append("CMAFREE")
    if m.get("SwapTotal")!=0 or m.get("SwapFree")!=0: reasons.append("SWAP")
    if s.get("home_free_bytes",0)<CONFIG["min_home_free_bytes"]: reasons.append("DISK")
    reasons.extend(systemd_gate_reasons(s.get("systemd_service_states",{})))
    try: load=float(s["loadavg"].split()[0])
    except (AttributeError,KeyError,IndexError,TypeError,ValueError): load=float("nan")
    if not math.isfinite(load) or load<0: reasons.append("LOAD_STATE_UNKNOWN")
    elif load>CONFIG["max_load1"]: reasons.append("LOAD")
    timeout_identity=s.get("timeout_executable")
    if (not isinstance(timeout_identity,dict) or
            timeout_identity != CONFIG.get("timeout_executable") or
            timeout_identity.get("path") != TIMEOUT_EXECUTABLE_PATH or
            timeout_identity.get("usable") is not True or
            not isinstance(timeout_identity.get("resolved_path"),str) or
            not Path(timeout_identity["resolved_path"]).is_absolute() or
            not isinstance(timeout_identity.get("sha256"),str) or
            not re.fullmatch(r"[0-9a-f]{64}",timeout_identity["sha256"])):
        reasons.append("TIMEOUT_EXECUTABLE_MISMATCH")
    forbidden_names={"apt","apt-get","dpkg","dpkg-deb","llama-mtmd-cli","llama-server","vivado","vitis_hls","xbutil","cmake","ninja","cc1","cc1plus","gcc","g++","make","rsync"}
    forbidden=[p for p in s["selected_processes"]
               if (p["comm"] in forbidden_names or
                   (p["comm"]=="unattended-upgr" and p.get("role")!="shutdown_waiter"))]
    if forbidden: reasons.append("BUSY_PROCESS")
    pkg=s.get("packagekit_transaction_state",{})
    if (not isinstance(pkg,dict) or
            pkg.get("state") not in ("SERVICE_INACTIVE","NO_ACTIVE_TRANSACTIONS") or
            pkg.get("timed_out") is not False): reasons.append("PACKAGEKIT_STATE")
    if before is not None:
        hz=os.sysconf("SC_CLK_TCK"); elapsed=2.0
        for pid,row in s["_rows_after"].items():
            if pid==os.getpid(): continue
            old=before.get(pid)
            if old and (row["ticks"]-old["ticks"])/hz/elapsed>=CONFIG["max_busy_cores_per_process"]:
                reasons.append("BUSY_CPU"); break
    return reasons
def rich_snapshot():
    before=proc_rows(); time.sleep(2); after=proc_rows(); s=snapshot(); s["_rows_after"]=after
    reasons=gate(s,True,before)
    s.pop("_rows_after",None); s["gate_reasons"]=reasons
    return s
def stop_group(p):
    global TERMINATION_UNPROVEN
    if p is None or p.poll() is not None: return True
    try: os.killpg(p.pid,signal.SIGTERM)
    except ProcessLookupError: pass
    try: p.wait(timeout=8); return True
    except subprocess.TimeoutExpired:
        try: os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError: pass
        try: p.wait(timeout=5); return True
        except subprocess.TimeoutExpired: TERMINATION_UNPROVEN=True; return False
def on_signal(sig,_frame):
    if not stop_group(ACTIVE): raise RuntimeError("child termination unproven")
    raise InterruptedError("remote worker signal "+str(sig))
for sig in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT): signal.signal(sig,on_signal)
def argv_sha(a): return hashlib.sha256(json.dumps(a,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
def write_result(case_dir, state): save(case_dir/"result.json",state)
def owned_cli_processes():
    needle=str(BASE/"build-cpu/bin/llama-mtmd-cli").encode(); found=[]; unreadable=[]
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name)==os.getpid(): continue
        try:
            if needle in (entry/"cmdline").read_bytes(): found.append(int(entry.name))
        except PermissionError: unreadable.append(int(entry.name))
        except OSError: continue
    return sorted(found),sorted(unreadable)

def main():
    RUNS.mkdir(parents=True,exist_ok=True)
    lock=(RUNS/".cpu_p2_runner.lock").open("a+")
    try: fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        print(json.dumps({"status":"REMOTE_LOCK_BUSY","cli_started":False},sort_keys=True)); return 2
    case_id=CONFIG["run_id"]; run_dir=RUNS/case_id
    outcome={"run_id":case_id,"status":"PRECHECK_BLOCKED","captured_at_utc":utc(),"cli_started":False}
    child=None; start_wall=None; start_mono=None
    timeout_expected=CONFIG.get("timeout_executable",{})
    timeout_recheck={"path":TIMEOUT_EXECUTABLE_PATH,"resolved_path":None,"sha256":None,"usable":False}
    timeout_identity_verified=False
    timeout_rechecked_at=None
    try:
        if run_dir.exists(): raise RuntimeError("board run ID already exists")
        initial=rich_snapshot(); outcome["initial_preflight"] = initial
        if initial["gate_reasons"]:
            outcome["gate_reasons"]=initial["gate_reasons"]; print(json.dumps(outcome,sort_keys=True)); return 3
        base=BASE; cli=base/"build-cpu/bin/llama-mtmd-cli"
        model=base/"input/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf"
        mmproj=base/"input/mmproj-MiniCPM-V-4.6-f16.gguf"
        image=base/"input/textvqa-dev50"/(CONFIG["image_id"]+".jpg")
        cache=base/"build-cpu/CMakeCache.txt"
        source=base/"staging/llama_cpp_7ab4ee7_source.tar.gz"
        if sha_file(cli)!=CONFIG["cli_sha256"] or sha_file(model)!=CONFIG["model_sha256"] or sha_file(mmproj)!=CONFIG["mmproj_sha256"] or sha_file(image)!=CONFIG["image_sha256"]:
            raise RuntimeError("board CLI/model/mmproj/image SHA mismatch")
        if image.stat().st_size!=CONFIG["image_bytes"]: raise RuntimeError("board image byte-size mismatch")
        if sha_file(source)!=CONFIG["source_archive_sha256"]: raise RuntimeError("pinned source archive mismatch")
        if sha_file(cache)!=CONFIG["cmake_cache_sha256"]: raise RuntimeError("CMakeCache differs from attested build")
        cache_text=cache.read_text(errors="replace")
        required=("CMAKE_BUILD_TYPE:STRING=Release","GGML_NATIVE:BOOL=OFF","LLAMA_BUILD_TOOLS:BOOL=ON",
                  "LLAMA_BUILD_TESTS:BOOL=OFF","LLAMA_BUILD_EXAMPLES:BOOL=OFF")
        if any(item not in cache_text for item in required): raise RuntimeError("CPU-only CMake configuration mismatch")
        if any(option+":BOOL=ON" in cache_text for option in ("GGML_CUDA","GGML_VULKAN","GGML_SYCL","GGML_HIP","GGML_OPENCL")):
            raise RuntimeError("non-CPU CMake backend is enabled")
        libs=[]
        for item in CONFIG["local_shared_libraries"]:
            path=base/item["path"]
            if sha_file(path)!=item["sha256"]: raise RuntimeError("attested library mismatch: "+item["path"])
            libs.append({"path":str(path),"sha256":item["sha256"]})
        file_check=subprocess.run(["file","-b",str(cli)],capture_output=True,text=True,timeout=10)
        elf_check=subprocess.run(["readelf","-h",str(cli)],capture_output=True,text=True,timeout=10)
        ldd_check=subprocess.run(["ldd",str(cli)],capture_output=True,text=True,timeout=20)
        if file_check.returncode!=0 or "aarch64" not in file_check.stdout.lower(): raise RuntimeError("file does not identify AArch64 CLI")
        if elf_check.returncode!=0 or "aarch64" not in elf_check.stdout.lower(): raise RuntimeError("readelf does not identify AArch64 CLI")
        if ldd_check.returncode!=0 or "not found" in ldd_check.stdout.lower(): raise RuntimeError("ldd reports a missing library")
        attested_paths={str((base/item["path"]).resolve()) for item in CONFIG["local_shared_libraries"]}
        ldd_local=[]
        for line in ldd_check.stdout.splitlines():
            match=re.search(r"=>\s+(/\S+)",line) or re.match(r"\s*(/\S+)",line)
            if match:
                resolved=str(Path(match.group(1)).resolve())
                if resolved.startswith(str(base.resolve())+"/"):
                    if resolved not in attested_paths: raise RuntimeError("ldd has an unattested board-local library")
                    ldd_local.append(resolved)
        if not ldd_local: raise RuntimeError("ldd did not resolve any attested board-local library")
        help_run=subprocess.run([str(cli),"--help"],capture_output=True,timeout=30)
        if help_run.returncode!=0: raise RuntimeError("board CLI --help failed")
        pre=rich_snapshot()
        if pre["gate_reasons"]:
            outcome["status"]="PRECHECK_BLOCKED"; outcome["gate_reasons"]=pre["gate_reasons"]
            outcome["preflight_before"]=pre; print(json.dumps(outcome,sort_keys=True)); return 3
        run_dir.mkdir(mode=0o700)
        a=CONFIG["argv"]
        command={"schema":"kv260_cpu_p2_textvqa_command_v1","question_id":CONFIG["question_id"],
                 "image_id":CONFIG["image_id"],"runtime_commit":CONFIG["runtime_commit"],
                 "manifest_sha256":CONFIG["manifest_sha256"],"model_sha256":CONFIG["model_sha256"],
                 "mmproj_sha256":CONFIG["mmproj_sha256"],"cli_sha256":CONFIG["cli_sha256"],
                 "image_path":str(image),"image_sha256":CONFIG["image_sha256"],"image_bytes":CONFIG["image_bytes"],
                 "argv":a,"working_directory":str(BASE),"written_before_launch_at_utc":None}
        input_record={"schema":"kv260_cpu_p2_textvqa_input_verification_v1","question_id":CONFIG["question_id"],
                      "image_id":CONFIG["image_id"],"image_path":str(image),"image_sha256":CONFIG["image_sha256"],
                      "image_bytes":CONFIG["image_bytes"],"verification_returncode":0,"verified_before_cli":True,
                      "verification_scope":"board_filesystem_prelaunch","verified_at_utc":utc()}
        artifact={"schema":"kv260_cpu_p2_textvqa_artifact_verification_v1","question_id":CONFIG["question_id"],
                  "runtime_commit":CONFIG["runtime_commit"],"verification_returncode":0,"verified_before_cli":True,
                  "verified_at_utc":utc(),"cli_path":str(cli),"cli_sha256":CONFIG["cli_sha256"],
                  "model_path":str(model),"model_sha256":CONFIG["model_sha256"],"mmproj_path":str(mmproj),
                  "mmproj_sha256":CONFIG["mmproj_sha256"],"cpu_build_attestation_sha256":CONFIG["attestation_sha256"],
                  "verification_scope":"board_filesystem_prelaunch","source_archive_sha256":CONFIG["source_archive_sha256"],
                  "cmake_cache_sha256":CONFIG["cmake_cache_sha256"],"cmake_cpu_only_configuration_verified":True,
                  "elf_file_summary":file_check.stdout.strip(),"elf_readelf_machine":next((line.strip() for line in elf_check.stdout.splitlines() if "Machine:" in line),""),
                  "ldd_no_missing":True,"ldd_local_library_paths":sorted(set(ldd_local))}
        save(run_dir/"input_verification.json",input_record); save(run_dir/"artifact_verification.json",artifact)
        save(run_dir/"preflight_before.json",pre)
        rc=None
        env=os.environ.copy()
        marker_was_present_before_removal="MTMD_TEST_RESPONSE_MARKER" in env
        env.pop("MTMD_TEST_RESPONSE_MARKER",None)
        env["LC_ALL"]="C"
        if not isinstance(a,list) or not a or a[0]!=TIMEOUT_EXECUTABLE_PATH:
            raise RuntimeError("CLI wrapper argv does not use the fixed timeout executable path")
        timeout_recheck=timeout_executable_identity()
        timeout_identity_verified=(timeout_recheck.get("usable") is True and
                                   timeout_recheck==timeout_expected)
        if not timeout_identity_verified:
            raise RuntimeError("timeout executable identity changed before CLI launch")
        timeout_rechecked_at=utc()
        command["timeout_executable"]=timeout_expected
        command["timeout_executable_recheck"]=timeout_recheck
        command["timeout_executable_identity_verified"]=True
        command["timeout_executable_rechecked_at_utc"]=timeout_rechecked_at
        command["written_before_launch_at_utc"]=utc()
        command["environment"]={"marker_name":"MTMD_TEST_RESPONSE_MARKER",
                                "marker_present_before_removal":marker_was_present_before_removal,
                                "marker_present_in_cli_environment":False,
                                "marker_removed_before_launch":True}
        save(run_dir/"command.json",command)
        start_wall=utc(); start_mono=time.monotonic()
        with (run_dir/"stdout.log").open("xb") as out,(run_dir/"stderr.log").open("xb") as err:
            child=subprocess.Popen(a,cwd=BASE,env=env,stdout=out,stderr=err,start_new_session=True)
            globals()["ACTIVE"]=child
            rc=child.wait(timeout=330)
        globals()["ACTIVE"]=None
        elapsed=round(time.monotonic()-start_mono,6); ended=utc()
        post=rich_snapshot(); save(run_dir/"preflight_after.json",post)
        resource=run_dir/"resource.txt"
        resource_text=resource.read_text(errors="replace") if resource.is_file() else ""
        child_match=re.search(r"Exit status:\s*(\d+)",resource_text)
        image_after=sha_file(image)
        post_image={"schema":"kv260_cpu_p2_textvqa_image_post_verification_v1","question_id":CONFIG["question_id"],
                    "image_id":CONFIG["image_id"],"image_path":str(image),"image_sha256":image_after,
                    "image_bytes":image.stat().st_size,"verified_after_cli":True,"verified_at_utc":utc()}
        save(run_dir/"image_post_verification.json",post_image)
        child_status=int(child_match.group(1)) if child_match else None
        owned,unreadable=owned_cli_processes()
        cleanup_verified=not owned and not unreadable and not TERMINATION_UNPROVEN
        state={"schema":"kv260_cpu_p2_textvqa_execution_v1","question_id":CONFIG["question_id"],"cli_started":True,
               "started_at_utc":start_wall,"ended_at_utc":ended,"elapsed_monotonic_seconds":elapsed,
               "wrapper_returncode":rc,"time_child_exit_status":child_status,"execution_complete":True,
               "raw_copy_complete":True,"timeout_seconds":CONFIG["timeout_seconds"],"resource_txt_sha256":sha_file(resource) if resource.is_file() else None,
               "command_json_sha256":sha_file(run_dir/"command.json"),"input_verification_json_sha256":sha_file(run_dir/"input_verification.json"),
               "artifact_verification_json_sha256":sha_file(run_dir/"artifact_verification.json"),"stdout_log_sha256":sha_file(run_dir/"stdout.log"),
               "stderr_log_sha256":sha_file(run_dir/"stderr.log"),"preflight_before_json_sha256":sha_file(run_dir/"preflight_before.json"),
               "preflight_after_json_sha256":sha_file(run_dir/"preflight_after.json"),"image_post_verification_json_sha256":sha_file(run_dir/"image_post_verification.json"),
               "spawn_pid":child.pid,"spawn_argv_sha256":argv_sha(a),"stdout_stderr_same_child_capture":True,
               **timeout_provenance_fields(timeout_expected,timeout_recheck,timeout_identity_verified,timeout_rechecked_at),
               "marker_was_present_before_removal":marker_was_present_before_removal,
               "runner_sha256":CONFIG["runner_sha256"],"remote_run_dir":str(run_dir),
               "remote_process_cleanup_verified":cleanup_verified}
        write_result(run_dir,state)
        outcome.update({"status":"REQUEST_FINISHED","cli_started":True,"run_dir":str(run_dir),"result_sha256":sha_file(run_dir/"result.json"),
                        "wrapper_returncode":rc,"time_child_exit_status":child_status,"postflight_gate_reasons":post["gate_reasons"]})
        if rc!=0 or child_status!=0 or image_after!=CONFIG["image_sha256"] or post["gate_reasons"]:
            outcome["stop_after_this_request"]=True
        if not cleanup_verified:
            outcome["status"]="REMOTE_STATE_UNKNOWN"; outcome["owned_cli_processes"]=owned
            outcome["unreadable_processes"]=unreadable; print(json.dumps(outcome,sort_keys=True)); return 5
        manifest={}
        for p in sorted(run_dir.iterdir()):
            if p.is_symlink(): raise RuntimeError("symlink in board raw run directory")
            if p.is_file(): manifest[p.name]={"bytes":p.stat().st_size,"sha256":sha_file(p)}
        save(run_dir/"completion.json",{"schema":"kv260_cpu_p2_textvqa_board_completion_v1","run_id":case_id,
                                       "manifest":manifest,"completed_at_utc":utc(),"worker_pid":os.getpid()})
        outcome["completion_sha256"]=sha_file(run_dir/"completion.json")
        print(json.dumps(outcome,sort_keys=True)); return 0 if outcome.get("stop_after_this_request") is not True else 4
    except Exception as exc:
        if ACTIVE is not None:
            if not stop_group(ACTIVE): TERMINATION_UNPROVEN=True
            globals()["ACTIVE"]=None
        outcome["error"]=repr(exc); outcome["child_termination_unproven"]=TERMINATION_UNPROVEN
        if child is None:
            # The worker reached no successful Popen call, so this is a known non-start.
            if run_dir.exists() and not (run_dir/"result.json").exists():
                try:
                    save(run_dir/"result.json",{"schema":"kv260_cpu_p2_textvqa_execution_v1",
                         "question_id":CONFIG["question_id"],"cli_started":False,
                         "non_start_reason":"PREFLIGHT_BLOCKED","non_start_at_utc":utc(),"prior_run_id":None,
                         **timeout_provenance_fields(timeout_expected,timeout_recheck,timeout_identity_verified,timeout_rechecked_at)})
                except OSError: pass
            outcome.update({"status":"PRECHECK_BLOCKED","cli_started":False})
            print(json.dumps(outcome,sort_keys=True)); return 3

        # Popen succeeded: preserve this in the attempted denominator even if a
        # later operation failed. Complete a partial manifest only when no owned
        # CLI remains and the process state is fully observable.
        owned,unreadable=owned_cli_processes()
        cleanup_verified=not owned and not unreadable and not TERMINATION_UNPROVEN
        ended=utc()
        if cleanup_verified and run_dir.exists() and (run_dir/"result.json").is_file() and not (run_dir/"completion.json").exists():
            try:
                saved=json.loads((run_dir/"result.json").read_text(encoding="utf-8"))
                if saved.get("cli_started") is True and saved.get("remote_process_cleanup_verified") is True:
                    manifest={}
                    for p in sorted(run_dir.iterdir()):
                        if p.is_symlink(): raise RuntimeError("symlink in board raw run directory")
                        if p.is_file(): manifest[p.name]={"bytes":p.stat().st_size,"sha256":sha_file(p)}
                    save(run_dir/"completion.json",{"schema":"kv260_cpu_p2_textvqa_board_completion_v1",
                         "run_id":case_id,"manifest":manifest,"completed_at_utc":utc(),"worker_pid":os.getpid()})
                    outcome.update({"status":"REQUEST_FINISHED","cli_started":True,
                                    "run_dir":str(run_dir),"result_sha256":sha_file(run_dir/"result.json"),
                                    "remote_process_cleanup_verified":True,"stop_after_this_request":True})
                    print(json.dumps(outcome,sort_keys=True)); return 4
            except Exception as completion_exc:
                outcome["partial_completion_error"]=repr(completion_exc)
        if cleanup_verified and run_dir.exists() and not (run_dir/"result.json").exists():
            try:
                if not (run_dir/"preflight_after.json").is_file():
                    save(run_dir/"preflight_after.json",rich_snapshot())
                image=BASE/"input/textvqa-dev50"/(CONFIG["image_id"]+".jpg")
                if not (run_dir/"image_post_verification.json").is_file() and image.is_file():
                    save(run_dir/"image_post_verification.json",{
                        "schema":"kv260_cpu_p2_textvqa_image_post_verification_v1",
                        "question_id":CONFIG["question_id"],"image_id":CONFIG["image_id"],
                        "image_path":str(image),"image_sha256":sha_file(image),
                        "image_bytes":image.stat().st_size,"verified_after_cli":True,"verified_at_utc":utc()})
                resource=run_dir/"resource.txt"
                if not resource.exists(): resource.write_text("",encoding="utf-8")
                try:
                    resource_text=resource.read_text(errors="replace")
                    m=re.search(r"Exit status:\s*(\d+)",resource_text)
                    child_status=int(m.group(1)) if m else None
                except OSError: child_status=None
                def optional_sha(name):
                    p=run_dir/name
                    return sha_file(p) if p.is_file() else None
                partial={"schema":"kv260_cpu_p2_textvqa_execution_v1",
                         "question_id":CONFIG["question_id"],"cli_started":True,
                         "started_at_utc":start_wall or ended,"ended_at_utc":ended,
                         "elapsed_monotonic_seconds":round(time.monotonic()-start_mono,6) if start_mono is not None else None,
                         "wrapper_returncode":child.poll(),"time_child_exit_status":child_status,
                         "execution_complete":False,"raw_copy_complete":False,
                         "timeout_seconds":CONFIG["timeout_seconds"],
                         "resource_txt_sha256":optional_sha("resource.txt"),
                         "command_json_sha256":optional_sha("command.json"),
                         "input_verification_json_sha256":optional_sha("input_verification.json"),
                         "artifact_verification_json_sha256":optional_sha("artifact_verification.json"),
                         "preflight_before_json_sha256":optional_sha("preflight_before.json"),
                         "preflight_after_json_sha256":optional_sha("preflight_after.json"),
                         "image_post_verification_json_sha256":optional_sha("image_post_verification.json"),
                         "stdout_log_sha256":optional_sha("stdout.log"),"stderr_log_sha256":optional_sha("stderr.log"),
                         "spawn_pid":child.pid,"spawn_argv_sha256":argv_sha(CONFIG["argv"]),
                         **timeout_provenance_fields(timeout_expected,timeout_recheck,timeout_identity_verified,timeout_rechecked_at),
                         "stdout_stderr_same_child_capture":True,"runner_sha256":CONFIG["runner_sha256"],
                         "remote_run_dir":str(run_dir),"remote_process_cleanup_verified":True}
                write_result(run_dir,partial)
                manifest={}
                for p in sorted(run_dir.iterdir()):
                    if p.is_symlink(): raise RuntimeError("symlink in board raw run directory")
                    if p.is_file(): manifest[p.name]={"bytes":p.stat().st_size,"sha256":sha_file(p)}
                save(run_dir/"completion.json",{"schema":"kv260_cpu_p2_textvqa_board_completion_v1",
                     "run_id":case_id,"manifest":manifest,"completed_at_utc":utc(),"worker_pid":os.getpid()})
                outcome.update({"status":"REQUEST_FINISHED","cli_started":True,
                                "run_dir":str(run_dir),"result_sha256":sha_file(run_dir/"result.json"),
                                "remote_process_cleanup_verified":True,"stop_after_this_request":True})
                print(json.dumps(outcome,sort_keys=True)); return 4
            except Exception as partial_exc:
                outcome["partial_attempt_record_error"]=repr(partial_exc)
        outcome.update({"status":"REMOTE_RUN_FAILED_UNKNOWN","cli_started":True,
                        "remote_process_cleanup_verified":cleanup_verified,
                        "owned_cli_processes":owned,"unreadable_processes":unreadable})
        print(json.dumps(outcome,sort_keys=True)); return 5
    finally:
        fcntl.flock(lock.fileno(),fcntl.LOCK_UN); lock.close()

if __name__=="__main__": raise SystemExit(main())
'''


def ssh_python(source: str, timeout: int) -> subprocess.CompletedProcess[bytes]:
    argv = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3", "kria", "python3 -"]
    return subprocess.run(argv, input=source.encode(), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=timeout, check=False)


def remote_status_source(run_id: str) -> str:
    return "RUN_ID=" + repr(run_id) + r'''
import fcntl,hashlib,json,os
from pathlib import Path
base=Path("/home/ubuntu/kv260-vlm-p2-cpu"); run=base/"runs"/RUN_ID
out={"state":"REMOTE_STATE_UNKNOWN","run_id":RUN_ID,"run_dir_exists":run.exists()}
lock_path=base/"runs/.cpu_p2_runner.lock"
try:
    with lock_path.open("rb") as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB); out["runner_lock_free"]=True
        fcntl.flock(f.fileno(),fcntl.LOCK_UN)
except (BlockingIOError,OSError): out["runner_lock_free"]=False
needle=str(base/"build-cpu/bin/llama-mtmd-cli").encode(); found=[]; unreadable=[]
for e in Path("/proc").iterdir():
    if not e.name.isdigit() or int(e.name)==os.getpid(): continue
    try:
        if needle in (e/"cmdline").read_bytes(): found.append(int(e.name))
    except PermissionError: unreadable.append(int(e.name))
    except OSError: pass
out["board_cli_processes"]=sorted(found); out["unreadable_processes"]=sorted(unreadable)
complete=run/"completion.json"; result=run/"result.json"
if complete.is_file() and result.is_file():
    try:
        c=json.loads(complete.read_text()); r=json.loads(result.read_text()); good=True
        manifest=c.get("manifest",{})
        if not isinstance(manifest,dict) or not manifest or len(manifest)>64: good=False
        for name,meta in manifest.items() if isinstance(manifest,dict) else []:
            if not isinstance(name,str) or Path(name).name!=name or not isinstance(meta,dict): good=False; break
            p=run/name
            if p.is_symlink() or not p.is_file() or not isinstance(meta.get("bytes"),int) or p.stat().st_size!=meta["bytes"]:
                good=False; break
            h=hashlib.sha256()
            with p.open("rb") as stream:
                for block in iter(lambda:stream.read(1<<20),b""): h.update(block)
            if h.hexdigest()!=meta.get("sha256"): good=False; break
        out["completion_marker_valid"]=bool(good and c.get("schema")=="kv260_cpu_p2_textvqa_board_completion_v1"
            and c.get("run_id")==RUN_ID and r.get("remote_process_cleanup_verified") is True)
        out["result_status"]="CLI_STARTED" if r.get("cli_started") is True else r.get("status")
    except (OSError,ValueError,KeyError,TypeError): out["completion_marker_valid"]=False
else: out["completion_marker_valid"]=False
if out.get("runner_lock_free") and out.get("completion_marker_valid") and not found and not unreadable:
    out["state"]="COMPLETE"
print(json.dumps(out,sort_keys=True))
'''


def load_adapter():
    spec = importlib.util.spec_from_file_location("board_textvqa_adapter", PARSER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load reviewed host adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path.insert(0, str((ROOT / "scripts/vendor").resolve()))
    from m4c_evaluators import TextVQAAccuracyEvaluator
    return module, TextVQAAccuracyEvaluator()


def assess_previous(qid: int, samples: dict[int, dict[str, Any]], manifest: dict[str, Any],
                    adapter: Any, evaluator: Any) -> dict[str, Any]:
    raw_dir = RAW_ROOT / RUN_IDS[qid]
    if not raw_dir.is_dir():
        raise ValueError(f"previous qid {qid} lacks immutable raw result")
    return adapter.inspect_case(qid, raw_dir, samples[qid], manifest, MANIFEST_SHA256,
                                MANIFEST_PATH, evaluator, "pilot")


def make_nonstart(qid: int, reason: str, prior_run_id: str | None) -> None:
    directory = RAW_ROOT / RUN_IDS[qid]
    if directory.exists():
        if (directory / "result.json").exists():
            raise ValueError("refusing to overwrite existing append-only attempt state: " + str(directory))
        raise ValueError("cannot append non-start state to existing partial raw directory: " + str(directory))
    directory.mkdir(mode=0o775)
    state = {"schema": "kv260_cpu_p2_textvqa_execution_v1", "question_id": qid,
             "cli_started": False, "non_start_reason": reason,
             "non_start_at_utc": datetime.now(timezone.utc).isoformat(),
             "prior_run_id": prior_run_id,
             "timeout_executable_path": None, "timeout_executable_resolved_path": None,
             "timeout_executable_sha256": None, "timeout_executable_recheck_path": None,
             "timeout_executable_recheck_resolved_path": None,
             "timeout_executable_recheck_sha256": None,
             "timeout_executable_identity_verified": False,
             "timeout_executable_rechecked_at_utc": None}
    write_json(directory / "result.json", state)


def record_nonstart_in_existing(directory: Path, qid: int, reason: str,
                                prior_run_id: str | None) -> None:
    if (directory / "result.json").exists():
        raise ValueError("refusing to overwrite existing append-only attempt state: " + str(directory))
    state = {"schema": "kv260_cpu_p2_textvqa_execution_v1", "question_id": qid,
             "cli_started": False, "non_start_reason": reason,
             "non_start_at_utc": datetime.now(timezone.utc).isoformat(),
             "prior_run_id": prior_run_id,
             "timeout_executable_path": None, "timeout_executable_resolved_path": None,
             "timeout_executable_sha256": None, "timeout_executable_recheck_path": None,
             "timeout_executable_recheck_resolved_path": None,
             "timeout_executable_recheck_sha256": None,
             "timeout_executable_identity_verified": False,
             "timeout_executable_rechecked_at_utc": None}
    write_json(directory / "result.json", state)


def expected_argv(qid: int, sample: dict[str, Any], run_dir: str) -> list[str]:
    image_path = f"{BOARD_BASE}/input/textvqa-dev50/{sample['image_id']}.jpg"
    prompt = ("Answer the following question based only on the image. Give a short, direct answer.\nQuestion: "
              + sample["question"] + "\nAnswer:")
    return [TIMEOUT_EXECUTABLE_PATH, "--verbose", "--signal=TERM", "--kill-after=10s", "300s",
            "/usr/bin/time", "-v", "-o", f"{run_dir}/resource.txt",
            f"{BOARD_BASE}/build-cpu/bin/llama-mtmd-cli", "-m",
            f"{BOARD_BASE}/input/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf", "--mmproj",
            f"{BOARD_BASE}/input/mmproj-MiniCPM-V-4.6-f16.gguf", "--image", image_path,
            "-p", prompt, "-t", "2", "-tb", "2", "-c", "4096", "-n", "48",
            "--seed", "42", "--temp", "0", "--top-p", "1", "--top-k", "0",
            "--device", "none", "-ngl", "0", "--no-mmproj-offload", "--no-warmup",
            "--perf", "-lv", "4"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qid", type=int, choices=ORDER)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--owner-window-confirmed", action="store_true")
    parser.add_argument("--owner-window-ref", default=None)
    parser.add_argument("--alpha-proof", type=Path)
    parser.add_argument("--build-attestation", type=Path, default=ATTESTATION_PATH)
    args = parser.parse_args()

    manifest, samples = load_manifest()

    if args.execute and (args.qid is None or not args.owner_window_confirmed or
                         not args.owner_window_ref or not args.owner_window_ref.strip() or
                         args.alpha_proof is None):
        parser.error("--execute requires --qid, --owner-window-confirmed, a non-empty --owner-window-ref and --alpha-proof")
    qids = (args.qid,) if args.qid else ORDER
    plans = []
    for qid in qids:
        sample = samples[qid]
        image = (MANIFEST_PATH.parent / sample["image_relative_path"]).resolve()
        if not image.is_file() or image.stat().st_size != sample["image_bytes"] or sha256_file(image) != sample["image_sha256"]:
            raise ValueError(f"frozen host image is missing or changed for qid {qid}")
        raw = RAW_ROOT / RUN_IDS[qid]
        remote = f"{BOARD_BASE}/runs/{RUN_IDS[qid]}"
        plans.append({"question_id": qid, "image_id": sample["image_id"],
                      "image_sha256": sample["image_sha256"], "image_bytes": sample["image_bytes"],
                      "local_raw_dir": str(raw), "board_run_dir": remote,
                      "argv": expected_argv(qid, sample, remote)})

    if not args.execute:
        blocked=[]
        if not args.alpha_proof:
            blocked.append("SYNTHETIC_ALPHA_PROOF_NOT_SUPPLIED")
        else:
            try:
                alpha_proof(args.alpha_proof)
            except (OSError,ValueError,KeyError,TypeError) as exc:
                blocked.append("SYNTHETIC_ALPHA_PROOF_INVALID: "+str(exc))
        for review_path,subject,label,missing_reason in (
                (ADAPTER_REVIEW,sha256_file(PARSER_PATH),"TextVQA adapter","INDEPENDENT_ADAPTER_REVIEW_MISSING_OR_STALE"),
                (RUNNER_REVIEW,sha256_file(Path(__file__).resolve()),"TextVQA runner","INDEPENDENT_RUNNER_REVIEW_MISSING_OR_STALE")):
            try:
                review_gate(review_path,subject,label)
            except (OSError,ValueError) as exc:
                blocked.append(missing_reason+": "+str(exc))
        if sha256_file(PREFLIGHT_SOURCE) != PREFLIGHT_SOURCE_SHA256:
            blocked.append("PREFLIGHT_SCRIPT_SHA_MISMATCH")
        if not args.owner_window_confirmed:
            blocked.append("OWNER_WINDOW_NOT_CONFIRMED")
        if not args.owner_window_ref or not args.owner_window_ref.strip():
            blocked.append("OWNER_WINDOW_REFERENCE_NOT_SUPPLIED")
        dry = {"schema": "kv260_cpu_p2_textvqa_runner_dry_plan_v2", "mode": "dry_plan_only",
               "created_at_utc": datetime.now(timezone.utc).isoformat(), "runtime_commit": PINNED_RUNTIME_COMMIT,
               "runner_path":str(Path(__file__).resolve()),"runner_sha256":sha256_file(Path(__file__).resolve()),
               "adapter_path":str(PARSER_PATH.resolve()),"adapter_sha256":sha256_file(PARSER_PATH),
               "read_only_preflight_script_path":str(PREFLIGHT_SOURCE.resolve()),
               "read_only_preflight_script_sha256":sha256_file(PREFLIGHT_SOURCE),
               "read_only_preflight_script_sha256_expected":PREFLIGHT_SOURCE_SHA256,
               "manifest_sha256": MANIFEST_SHA256, "build_attestation_path": str(args.build_attestation.resolve()),
               "build_attestation_sha256_expected": ATTESTATION_SHA256,
               "alpha_proof_required": True, "independent_adapter_and_runner_reviews_required": True,
               "execution_ready":False,"execution_blocked_reasons":blocked,
               "live_board_resource_gate":"NOT_CHECKED_NO_BOARD_CONNECTION",
               "owner_window_confirmed": bool(args.owner_window_confirmed),
               "owner_window_ref": args.owner_window_ref,
               "gates": {"memavailable_kib_min": MIN_MEM_AVAILABLE_KIB,"cmafree_kib_min": MIN_CMA_FREE_KIB,
                         "home_free_bytes_min": MIN_HOME_FREE_BYTES,"load1_max": MAX_LOAD1,
                         "max_busy_cores_per_process": MAX_BUSY_CORES_PER_PROCESS,
                         "process_cpu_sample_wait_seconds": PROCESS_CPU_SAMPLE_WAIT_SECONDS,
                         "no_swap": True,"jupyter_active": True,"no_unattended_upgrades": True,
                         "one_fresh_cli_per_owner_window": True,"max_cli_seconds": CLI_TIMEOUT_SECONDS,
                         "max_total_cli_seconds": 900},"requests": plans}
        print(json.dumps(dry, ensure_ascii=False, sort_keys=True, indent=2))
        return 0

    # All review and ALPHA proof gates are checked before any board connection.
    proof = static_prerequisites(args.alpha_proof)
    if args.build_attestation.resolve() != ATTESTATION_PATH.resolve():
        raise ValueError("this runner version is bound to the frozen build attestation path")
    qid = args.qid
    assert qid is not None
    index = ORDER.index(qid)
    adapter, evaluator = load_adapter()
    sample = samples[qid]
    image = (MANIFEST_PATH.parent / sample["image_relative_path"]).resolve()
    board_run_dir = f"{BOARD_BASE}/runs/{RUN_IDS[qid]}"
    raw_dir_path = RAW_ROOT / RUN_IDS[qid]
    raw_dir_holder: dict[str, Path] = {}
    cfg = {"run_id":RUN_IDS[qid],"question_id":qid,"image_id":sample["image_id"],
           "image_sha256":sample["image_sha256"],"image_bytes":sample["image_bytes"],
           "manifest_sha256":MANIFEST_SHA256,"runtime_commit":PINNED_RUNTIME_COMMIT,
           "model_sha256":MODEL_SHA256,"mmproj_sha256":MMPROJ_SHA256,"cli_sha256":CLI_SHA256,
           "source_archive_sha256":"5fe5b3133f7c31f42cc9597059ddb69f31045dbbf3fbfe8bd57236ab0626efe9",
           "attestation_sha256":ATTESTATION_SHA256,"cmake_cache_sha256":json.loads(ATTESTATION_PATH.read_text())["cmake_cache_sha256"],
           "local_shared_libraries":json.loads(ATTESTATION_PATH.read_text())["local_shared_libraries"],
           "argv":expected_argv(qid,sample,board_run_dir),
           "min_mem_available_kib":MIN_MEM_AVAILABLE_KIB,"min_cma_free_kib":MIN_CMA_FREE_KIB,
           "min_home_free_bytes":MIN_HOME_FREE_BYTES,"max_load1":MAX_LOAD1,
           "max_busy_cores_per_process":MAX_BUSY_CORES_PER_PROCESS,"timeout_seconds":CLI_TIMEOUT_SECONDS,
           "runner_sha256":proof["runner_sha256"],"owner_window":{"confirmed":True,
              "operator_login":getpass.getuser(),"confirmed_at_utc":datetime.now(timezone.utc).isoformat(),
              "coordination_reference":args.owner_window_ref}}
    outcome = {"schema":"kv260_cpu_p2_textvqa_runner_local_record_v1","run_id":RUN_IDS[qid],
               "question_id":qid,"owner_window":cfg["owner_window"],"proofs":proof,
               "runner_sha256":proof["runner_sha256"],"parser_sha256":proof["parser_sha256"],
               "host_started_at_utc":datetime.now(timezone.utc).isoformat(),"status":"PRECHECK_IN_PROGRESS"}
    worker_path = raw_dir_path / "remote_worker.py"

    def current_raw_dir() -> Path:
        return raw_dir_holder.get("path", raw_dir_path)

    def record_state(phase: str, fields: dict[str, Any]) -> None:
        outcome.update(fields)
        write_record(current_raw_dir(), phase, outcome)

    def record_nonstart(qid_to_record: int, reason: str, prior_run_id: str | None) -> None:
        directory = RAW_ROOT / RUN_IDS[qid_to_record]
        try:
            if directory.exists():
                record_nonstart_in_existing(directory, qid_to_record, reason, prior_run_id)
            else:
                make_nonstart(qid_to_record, reason, prior_run_id)
        except ValueError as exc:
            if qid_to_record == qid:
                raise
            outcome.setdefault("later_nonstart_record_conflicts", []).append(
                {"question_id": qid_to_record, "error": str(exc)})

    def assess_previous_case(previous_qid: int) -> bool:
        prior = assess_previous(previous_qid, samples, manifest, adapter, evaluator)
        return (prior["attempted"] is True and prior["answer_parse_ok"] is True and
                prior["image_processing_verified"] is True)

    def begin_request() -> None:
        raw_dir_holder["path"] = checked_raw_path(raw_dir_path)
        current_raw_dir().mkdir(mode=0o775)
        write_record(current_raw_dir(), "start", outcome)
        worker_path.write_text("CONFIG=" + repr(cfg) + "\n" + REMOTE_WORKER, encoding="utf-8")

    def before_cli_failure(reason: str, phase: str, detail: str,
                          extra_fields: dict[str, Any] | None = None) -> dict[str, Any]:
        fields = {"status": phase.upper(), "board_inference_attempted": False,
                  "error": detail, "ended_at_utc": datetime.now(timezone.utc).isoformat()}
        if extra_fields:
            fields.update(extra_fields)
        return {"phase": phase, "non_start_reason": reason, "fields": fields}

    def preflight_request() -> dict[str, Any] | None:
        try:
            preflight = ssh_python(PREFLIGHT_SOURCE.read_text(encoding="utf-8"), 35)
        except (subprocess.TimeoutExpired, OSError) as exc:
            (current_raw_dir() / "preflight_before.transport.stdout").write_bytes(
                captured_output_bytes(getattr(exc, "output", None)))
            (current_raw_dir() / "preflight_before.transport.stderr").write_bytes(
                captured_output_bytes(getattr(exc, "stderr", None)))
            return before_cli_failure("PREFLIGHT_BLOCKED", "preflight_transport_failed", repr(exc))
        (current_raw_dir() / "preflight_before.transport.stdout").write_bytes(preflight.stdout)
        (current_raw_dir() / "preflight_before.transport.stderr").write_bytes(preflight.stderr)
        if preflight.returncode != 0:
            return before_cli_failure("PREFLIGHT_BLOCKED", "preflight_transport_failed",
                f"read-only SSH preflight exited {preflight.returncode}",
                {"preflight_returncode": preflight.returncode})
        try:
            snapshot = json.loads(preflight.stdout)
        except (ValueError, UnicodeDecodeError) as exc:
            return before_cli_failure("PREFLIGHT_BLOCKED", "preflight_invalid",
                "read-only SSH preflight returned invalid JSON: " + repr(exc))
        if (not isinstance(snapshot, dict) or not isinstance(snapshot.get("memory_kib"), dict) or
                not isinstance(snapshot.get("selected_process_counts"), dict) or
                not isinstance(snapshot.get("selected_processes"), list) or
                not isinstance(snapshot.get("packagekit_transaction_state"), dict) or
                not isinstance(snapshot.get("loadavg"), str) or "arch" not in snapshot or
                "cpu_count" not in snapshot or "home_free_bytes" not in snapshot or
                "jupyter_active" not in snapshot or "jupyter_returncode" not in snapshot or
                snapshot.get("schema") != "kv260_cpu_p2_textvqa_runtime_preflight_v3" or
                not isinstance(snapshot.get("systemd_service_states"), dict)):
            return before_cli_failure("PREFLIGHT_BLOCKED", "preflight_invalid",
                "read-only SSH preflight omitted required resource fields")
        process_rows = snapshot.get("selected_processes", [])
        if any(not isinstance(row, dict) or not isinstance(row.get("comm"), str)
               for row in process_rows):
            return before_cli_failure("PREFLIGHT_BLOCKED", "preflight_invalid",
                "read-only SSH preflight returned malformed process details")
        reasons = preflight_resource_gate_reasons(snapshot)
        snapshot["gate_reasons"] = reasons
        write_json(current_raw_dir() / "preflight_before.json", snapshot)
        if reasons:
            return {"phase": "preflight_blocked", "non_start_reason": "PREFLIGHT_BLOCKED",
                    "fields": {"status": "PREFLIGHT_BLOCKED", "gate_reasons": reasons,
                               "board_inference_attempted": False,
                               "ended_at_utc": datetime.now(timezone.utc).isoformat()}}
        timeout_identity = snapshot["timeout_executable"]
        cfg["timeout_executable"] = timeout_identity
        outcome["timeout_executable"] = timeout_identity
        return None

    def stage_input() -> dict[str, Any] | None:
        worker = "CONFIG=" + repr(cfg) + "\n" + REMOTE_WORKER
        worker_path.write_text(worker, encoding="utf-8")
        remote_input = f"{BOARD_BASE}/input/textvqa-dev50/"
        mkdir_source = f"from pathlib import Path; Path({(BOARD_BASE + '/input/textvqa-dev50')!r}).mkdir(parents=True,exist_ok=True); print('INPUT_DIR_READY')"
        try:
            staged = ssh_python(mkdir_source, 30)
        except (subprocess.TimeoutExpired, OSError) as exc:
            return before_cli_failure("INPUT_UNAVAILABLE", "input_directory_failed", repr(exc))
        (current_raw_dir() / "input_directory.stdout").write_bytes(staged.stdout)
        (current_raw_dir() / "input_directory.stderr").write_bytes(staged.stderr)
        if staged.returncode != 0:
            return before_cli_failure("INPUT_UNAVAILABLE", "input_directory_failed",
                f"board user input directory setup exited {staged.returncode}")
        rsync_argv = ["rsync", "-a", "--ignore-existing", "-e",
                      "ssh -T -o BatchMode=yes -o ConnectTimeout=10", "--", str(image),
                      f"kria:{remote_input}{sample['image_id']}.jpg"]
        try:
            transfer = subprocess.run(rsync_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      timeout=60, check=False)
        except (subprocess.TimeoutExpired, OSError) as exc:
            (current_raw_dir() / "image_transfer.stdout").write_bytes(
                captured_output_bytes(getattr(exc, "output", None)))
            (current_raw_dir() / "image_transfer.stderr").write_bytes(
                captured_output_bytes(getattr(exc, "stderr", None)))
            return before_cli_failure("INPUT_UNAVAILABLE", "image_transfer_failed", repr(exc))
        (current_raw_dir() / "image_transfer.stdout").write_bytes(transfer.stdout)
        (current_raw_dir() / "image_transfer.stderr").write_bytes(transfer.stderr)
        if transfer.returncode != 0:
            return before_cli_failure("INPUT_UNAVAILABLE", "image_transfer_failed",
                f"board image staging exited {transfer.returncode}")
        return None

    worker_timed_out_holder = {"value": False}

    def launch_worker() -> dict[str, Any]:
        remote_cmd = f"{TIMEOUT_EXECUTABLE_PATH} --verbose --signal=TERM --kill-after=15s {REMOTE_WATCHDOG_SECONDS}s python3 -"
        remote_argv = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                       "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3",
                       "kria", remote_cmd]
        started = datetime.now(timezone.utc).isoformat()
        try:
            result = subprocess.run(remote_argv, input=worker_path.read_bytes(),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=HOST_WAIT_SECONDS, check=False)
            transport = {"argv": remote_argv, "started_at_utc": started,
                "ended_at_utc": datetime.now(timezone.utc).isoformat(), "returncode": result.returncode,
                "timed_out": False, "timeout_executable": cfg["timeout_executable"],
                "worker_sha256": sha256_file(worker_path),
                "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()}
        except subprocess.TimeoutExpired as exc:
            result = None
            worker_timed_out_holder["value"] = True
            timeout_stdout = captured_output_bytes(getattr(exc, "output", None))
            timeout_stderr = captured_output_bytes(getattr(exc, "stderr", None))
            outcome.update(persist_transport_failure(current_raw_dir(), "worker", exc))
            transport = {"argv": remote_argv, "started_at_utc": started,
                "ended_at_utc": datetime.now(timezone.utc).isoformat(), "returncode": None,
                "timed_out": True, "worker_sha256": sha256_file(worker_path),
                "timeout_executable": cfg["timeout_executable"],
                "stdout_sha256": hashlib.sha256(timeout_stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(timeout_stderr).hexdigest(),
                "partial_output_preserved": True}
        write_json(current_raw_dir() / "worker.transport.json", transport)
        outcome["remote_transport"] = transport
        outcome["status"] = "REMOTE_COMPLETED" if result is not None else "REMOTE_STATE_UNKNOWN"
        remote_result = None
        if result is not None:
            (current_raw_dir() / "worker.stdout").write_bytes(result.stdout)
            (current_raw_dir() / "worker.stderr").write_bytes(result.stderr)
            try:
                remote_result = json.loads(result.stdout.decode().splitlines()[-1])
                outcome["remote_result"] = remote_result
            except (ValueError, IndexError, UnicodeDecodeError):
                outcome["remote_result_parse_failed"] = True
        outcome["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_record(current_raw_dir(), "remote_outcome", outcome)
        return {"timed_out": result is None, "remote_result": remote_result,
                "returncode": None if result is None else result.returncode}

    def query_remote_status() -> dict[str, Any]:
        outcome["remote_status_check_attempted_after_worker_timeout"] = worker_timed_out_holder["value"]
        try:
            reply = ssh_python(remote_status_source(RUN_IDS[qid]), 45)
        except (subprocess.TimeoutExpired, OSError) as exc:
            outcome.update(persist_transport_failure(current_raw_dir(), "remote_status", exc))
            return {"returncode": None, "remote_status": None, "transport_error": repr(exc)}
        (current_raw_dir() / "remote_status.stdout").write_bytes(reply.stdout)
        (current_raw_dir() / "remote_status.stderr").write_bytes(reply.stderr)
        if reply.returncode != 0:
            return {"returncode": reply.returncode, "remote_status": None}
        try:
            remote_status = json.loads(reply.stdout)
        except (ValueError, UnicodeDecodeError):
            remote_status = {"state": "REMOTE_STATE_UNKNOWN", "parse_failed": True}
        write_json(current_raw_dir() / "remote_status.json", remote_status)
        outcome["remote_state"] = (remote_status.get("state")
                                   if isinstance(remote_status, dict) else "REMOTE_STATE_UNKNOWN")
        if worker_timed_out_holder["value"] and isinstance(remote_status, dict) and \
                remote_status.get("state") == "COMPLETE":
            outcome["status"] = "REMOTE_COMPLETED_AFTER_HOST_TIMEOUT"
        return {"returncode": reply.returncode, "remote_status": remote_status}

    def copy_and_verify() -> dict[str, Any]:
        remote_dir = f"{BOARD_BASE}/runs/{RUN_IDS[qid]}/"
        copy_status = "REMOTE_STATE_UNKNOWN" if worker_timed_out_holder["value"] else "EVIDENCE_COPY_INCOMPLETE"
        try:
            copied = subprocess.run(["rsync", "-a", "-e",
                "ssh -T -o BatchMode=yes -o ConnectTimeout=10", "--",
                f"kria:{remote_dir}", str(current_raw_dir()) + "/"], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=90, check=False)
        except (subprocess.TimeoutExpired, OSError) as exc:
            outcome.update(persist_transport_failure(current_raw_dir(), "raw_copy", exc))
            outcome["status"] = copy_status
            if worker_timed_out_holder["value"]:
                outcome["timeout_recovery_failed_at"] = "raw_copy"
            return {"verified": False, "phase": "copy_incomplete", "failure_at": "raw_copy"}
        (current_raw_dir() / "raw_copy.stdout").write_bytes(copied.stdout)
        (current_raw_dir() / "raw_copy.stderr").write_bytes(copied.stderr)
        if copied.returncode != 0:
            outcome["status"] = copy_status
            outcome["raw_copy_returncode"] = copied.returncode
            if worker_timed_out_holder["value"]:
                outcome["timeout_recovery_failed_at"] = "raw_copy_returncode"
            return {"verified": False, "phase": "copy_incomplete", "failure_at": "raw_copy_returncode"}
        try:
            completion_sha = adapter.verify_board_completion_manifest(current_raw_dir(), qid)
            completion = json.loads((current_raw_dir() / "completion.json").read_text(encoding="utf-8"))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            outcome["status"] = copy_status
            outcome["completion_manifest_error"] = repr(exc)
            if worker_timed_out_holder["value"]:
                outcome["timeout_recovery_failed_at"] = "completion_manifest"
            return {"verified": False, "phase": "copy_manifest_invalid", "failure_at": "completion_manifest"}
        mismatches = []
        for name, row in completion["manifest"].items():
            copied_path = current_raw_dir() / name
            if (not copied_path.is_file() or copied_path.stat().st_size != row["bytes"] or
                    sha256_file(copied_path) != row["sha256"]):
                mismatches.append(name)
        if mismatches:
            outcome["status"] = copy_status
            outcome["copy_mismatches"] = mismatches
            if worker_timed_out_holder["value"]:
                outcome["timeout_recovery_failed_at"] = "copy_hash_mismatch"
            return {"verified": False, "phase": "copy_mismatch", "failure_at": "copy_hash_mismatch"}
        outcome["raw_copy_returncode"] = 0
        outcome["copied_manifest_matches_board"] = True
        receipt = {"schema": "kv260_cpu_p2_textvqa_host_copy_verification_v1",
            "question_id": qid, "run_id": RUN_IDS[qid], "completion_json_sha256": completion_sha,
            "board_files_verified": True,
            "verified_file_names": sorted(set(completion["manifest"]) | {"completion.json"}),
            "verified_at_utc": datetime.now(timezone.utc).isoformat()}
        write_json(current_raw_dir() / "host_copy_verification.json", receipt)
        outcome["host_copy_verification_sha256"] = sha256_file(
            current_raw_dir() / "host_copy_verification.json")
        outcome["completion_json_sha256"] = completion_sha
        return {"verified": True}

    def score_copied_case() -> dict[str, Any]:
        parsed = adapter.inspect_case(qid, current_raw_dir(), sample, manifest, MANIFEST_SHA256,
                                      MANIFEST_PATH, evaluator, "pilot")
        outcome["host_adapter_case_status"] = parsed["status"]
        outcome["answer_parse_ok"] = parsed["answer_parse_ok"]
        outcome["image_processing_verified"] = parsed["image_processing_verified"]
        outcome["host_adapter_completion_json_sha256"] = parsed.get("completion_json_sha256")
        outcome["host_adapter_board_completion_manifest_verified"] = parsed.get(
            "board_completion_manifest_verified")
        passed = parsed["answer_parse_ok"] is True and parsed["image_processing_verified"] is True
        outcome["stop_after_this_request"] = (False if not passed else
            outcome.get("remote_result", {}).get("stop_after_this_request", False))
        write_json(current_raw_dir() / "runner_host_assessment.json", {
            key: parsed[key] for key in ("question_id", "attempted", "status", "answer_parse_ok",
                                          "image_processing_verified", "errors")})
        return {"answer_parse_ok": parsed["answer_parse_ok"],
                "image_processing_verified": parsed["image_processing_verified"],
                "stop_after_this_request": outcome["stop_after_this_request"]}

    ops = HostOrchestrationOps(
        assess_previous=assess_previous_case,
        begin=begin_request,
        preflight=preflight_request,
        stage=stage_input,
        launch_worker=launch_worker,
        query_status=query_remote_status,
        copy_and_verify=copy_and_verify,
        score=score_copied_case,
        record_nonstart=record_nonstart,
        record_state=record_state,
    )
    decision = run_host_orchestration(qid, ORDER, RUN_IDS, ops)
    if decision.get("status") in ("PRIOR_CASE_FAILED", "PRIOR_CASE_UNRESOLVED"):
        print(json.dumps(decision, sort_keys=True))
    else:
        print(json.dumps(outcome, ensure_ascii=False, sort_keys=True))
    return int(decision["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
