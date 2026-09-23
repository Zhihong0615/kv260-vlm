#!/usr/bin/env python3
"""Capture one redacted CPU graph-metadata trace for four frozen requests."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

WORKER_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path("/home/zhiro/research/kv260-vlm")
INPUT_MANIFEST = WORKER_ROOT / "orchestration/evidence_snapshots/B03_selected_qid_optraces/SOURCE.sha256"
RUN_ID = "textvqa_selected_optrace_B03"
RAW_OUT = WORKER_ROOT / "experiments/raw" / RUN_ID
DERIVED_OUT = WORKER_ROOT / "experiments/derived/selected_qid_optrace_B03_summary.json"
BUILD_DIR = Path("/tmp/phasemap-vlm-optrace-B03")
SOURCE_RUN = SOURCE_ROOT / "experiments/raw/textvqa_val_dev50_host_q4_cpu_round01"
MODEL = SOURCE_ROOT / "models/gguf/MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf"
MMPROJ = SOURCE_ROOT / "models/gguf/mmproj-MiniCPM-V-4.6-f16.gguf"

REQUESTS = {
    34609: {
        "record": SOURCE_RUN / "040_q34609/command.json",
        "image_id": "181f00d3ee2b2076",
        "image_sha256": "26401f0395f38a5c780f9d05d0eeba956876ba762159585e8ece52eafb8d1bfd",
        "image_size": [1024, 729],
        "n_tokens_batch": [63, 63, 63, 63, 63],
    },
    35005: {
        "record": SOURCE_RUN / "045_q35005/command.json",
        "image_id": "97c8c2c2c6f572f1",
        "image_sha256": "2512aeae080117e96813702fc68733be80a4051fc1e871d926306c37a91abdb6",
        "image_size": [1024, 1024],
        "n_tokens_batch": [64, 70, 70, 70, 70, 70, 70],
    },
    35419: {
        "record": SOURCE_RUN / "028_q35419/command.json",
        "image_id": "004b75d1299e653c",
        "image_sha256": "f703a5ce6bbf7c1aa1dd11fda26a7a30323913d404d771d51deba387c840c5f6",
        "image_size": [1024, 819],
        "n_tokens_batch": [63, 63, 63, 63, 63, 63, 63],
    },
    35950: {
        "record": SOURCE_RUN / "035_q35950/command.json",
        "image_id": "9d85d260f22be0c8",
        "image_sha256": "225ff76c542d9f49474f60dfeb316e3ca31828b44b3ebaee52dcb3eeec984c30",
        "image_size": [1024, 633],
        "n_tokens_batch": [60, 60, 60, 60, 60],
    },
}

EXPECTED_MODEL_SHA256 = "8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773"
EXPECTED_MMPROJ_SHA256 = "ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293"
EXPECTED_SOURCE_COMMIT = "094edc130489dc59dd9333e4ae6b0aa4c8013149"
EXPECTED_RUNTIME_COMMIT = "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_manifest() -> None:
    failures = []
    for raw in INPUT_MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        expected, path_text = line.split("  ", 1)
        path = Path(path_text)
        if not path.is_file():
            failures.append(f"missing: {path}")
        elif sha256(path) != expected:
            failures.append(f"hash mismatch: {path}")
    if failures:
        raise SystemExit("frozen source manifest failed:\n" + "\n".join(failures))


def get_value(argv: list[str], option: str) -> str:
    index = argv.index(option)
    if index + 1 >= len(argv):
        raise ValueError(f"missing value for {option}")
    return argv[index + 1]


def parse_trace(path: Path, qid: int, image_sha: str) -> dict:
    phase_counts: Counter[str] = Counter()
    op_counts: dict[str, Counter[str]] = defaultdict(Counter)
    signatures: dict[str, set[str]] = defaultdict(set)
    matmuls: dict[str, Counter[str]] = defaultdict(Counter)
    media_batches = []
    node_count = 0
    records = 0
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            records += 1
            if row.get("request_id") != str(qid) or row.get("image_sha256") != image_sha:
                raise ValueError(f"request/image identity mismatch at trace line {line_number}")
            kind = row.get("record")
            if kind == "media_batch":
                media_batches.append({k: row[k] for k in ("group", "chunk_index", "chunks_added", "chunks_total")})
                continue
            if kind != "node":
                raise ValueError(f"unexpected trace record {kind!r} at line {line_number}")
            node_count += 1
            phase, op = row["phase"], row["op"]
            output = row["output"]
            inputs = row["inputs"]
            phase_counts[phase] += 1
            op_counts[phase][op] += 1
            sig = {
                "op": op,
                "output": {k: output.get(k) for k in ("dtype", "ne", "nb", "bytes")},
                "inputs": [{k: tensor.get(k) for k in ("dtype", "ne", "nb", "bytes")} for tensor in inputs],
            }
            signatures[phase].add(json.dumps(sig, sort_keys=True, separators=(",", ":")))
            if op == "MUL_MAT":
                matmuls[phase][json.dumps({
                    "output_dtype": output["dtype"],
                    "output_ne": output["ne"],
                    "input_ne": [tensor["ne"] for tensor in inputs],
                    "input_dtype": [tensor["dtype"] for tensor in inputs],
                }, sort_keys=True, separators=(",", ":"))] += 1
    if not node_count:
        raise ValueError(f"no graph nodes in trace for qid {qid}")
    return {
        "trace_record_count": records,
        "graph_node_count": node_count,
        "node_count_by_phase": dict(sorted(phase_counts.items())),
        "unique_op_shape_signatures_by_phase": {phase: len(items) for phase, items in sorted(signatures.items())},
        "op_count_by_phase": {phase: dict(sorted(counter.items())) for phase, counter in sorted(op_counts.items())},
        "matmul_shape_counts_by_phase": {
            phase: [{**json.loads(shape), "count": count} for shape, count in sorted(counter.items())]
            for phase, counter in sorted(matmuls.items())
        },
        "encoded_media_batch_records": media_batches,
        "crop_identity_available": False,
        "backend_eligibility_or_placement_available": False,
    }


def main() -> int:
    if RAW_OUT.exists() or DERIVED_OUT.exists():
        raise SystemExit(f"refusing to overwrite existing B03 output: {RAW_OUT if RAW_OUT.exists() else DERIVED_OUT}")
    if BUILD_DIR.exists():
        raise SystemExit(f"refusing to reuse temporary build directory: {BUILD_DIR}")
    if not INPUT_MANIFEST.is_file():
        raise SystemExit(f"missing source manifest: {INPUT_MANIFEST}")
    if os.statvfs(WORKER_ROOT).f_bavail * os.statvfs(WORKER_ROOT).f_frsize < (1 << 30):
        raise SystemExit("less than 1 GiB free; refusing to start host traces")
    verify_manifest()
    if sha256(MODEL) != EXPECTED_MODEL_SHA256 or sha256(MMPROJ) != EXPECTED_MMPROJ_SHA256:
        raise SystemExit("model or mmproj hash changed")
    os.environ["PHASEMAP_OPTRACE_SOURCE_ROOT"] = str(SOURCE_ROOT)
    os.environ["PHASEMAP_OPTRACE_BUILD_DIR"] = str(BUILD_DIR)
    sys.path.insert(0, str(WORKER_ROOT / "scripts"))
    import build_optrace_cli_B03

    if build_optrace_cli_B03.main() != 0:
        return 1
    build_record = json.loads((BUILD_DIR / "build.json").read_text(encoding="utf-8"))
    traced_cli = Path(build_record["binary"])
    RAW_OUT.mkdir(parents=True)
    cases = []
    for qid, meta in sorted(REQUESTS.items()):
        source_record_path = meta["record"]
        source_record = json.loads(source_record_path.read_text(encoding="utf-8"))
        if source_record.get("returncode") != 0:
            raise SystemExit(f"source host command did not pass for qid {qid}")
        argv = source_record["command"]
        cli_index = next((i for i, arg in enumerate(argv) if arg.endswith("/llama-mtmd-cli")), None)
        if cli_index is None:
            raise SystemExit(f"cannot find pinned CLI in qid {qid} command record")
        args = argv[cli_index + 1:]
        if Path(get_value(args, "-m")) != MODEL or Path(get_value(args, "--mmproj")) != MMPROJ:
            raise SystemExit(f"model identity mismatch in qid {qid} command record")
        image = Path(get_value(args, "--image"))
        image_id = image.stem
        image_hash = sha256(image)
        if image_id != meta["image_id"] or image_hash != meta["image_sha256"]:
            raise SystemExit(f"image identity/hash mismatch for qid {qid}")
        prompt = get_value(args, "-p")
        trace_path = RAW_OUT / f"qid_{qid}_op_trace.jsonl"
        trace_gz_path = RAW_OUT / f"qid_{qid}_op_trace.jsonl.gz"
        if trace_path.exists() or trace_gz_path.exists():
            raise SystemExit(f"refusing to overwrite qid {qid} trace")

        env = dict(os.environ)
        for name in ("PHASEMAP_LAYER_TIMING", "PHASEMAP_TARGET_OP_TIMING", "PHASEMAP_ALLOCATOR_METADATA", "MTMD_DEBUG_GRAPH"):
            env.pop(name, None)
        env["PHASEMAP_OPTRACE_PATH"] = str(trace_path)
        env["PHASEMAP_REQUEST_ID"] = str(qid)
        env["PHASEMAP_IMAGE_SHA256"] = image_hash
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(
            [str(traced_cli), *args], cwd=SOURCE_ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False, timeout=300,
        )
        if result.returncode != 0 or not trace_path.is_file() or trace_path.stat().st_size == 0:
            partial = {
                "run_id": RUN_ID,
                "status": "FAIL",
                "failed_qid": qid,
                "returncode": result.returncode,
                "trace_exists": trace_path.is_file(),
                "generated_answer_text_saved": False,
                "source_manifest_sha256": sha256(INPUT_MANIFEST),
                "trace_cli_build": build_record,
            }
            (RAW_OUT / "run.json").write_text(json.dumps(partial, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"qid": qid, "status": "FAIL", "returncode": result.returncode}))
            return 1

        profile = parse_trace(trace_path, qid, image_hash)
        raw_bytes = trace_path.read_bytes()
        raw_sha = hashlib.sha256(raw_bytes).hexdigest()
        compressed = gzip.compress(raw_bytes, compresslevel=9, mtime=0)
        trace_gz_path.write_bytes(compressed)
        if gzip.decompress(trace_gz_path.read_bytes()) != raw_bytes:
            raise SystemExit(f"gzip round-trip mismatch for qid {qid}")
        compressed_sha = sha256(trace_gz_path)
        trace_path.unlink()
        cases.append({
            "question_id": qid,
            "image_id": image_id,
            "image_size": meta["image_size"],
            "image_sha256": image_hash,
            "source_command_record_sha256": sha256(source_record_path),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "argv_sha256": hashlib.sha256(json.dumps(args, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
            "n_tokens_batch_from_B02": meta["n_tokens_batch"],
            "source_host_returncode": source_record["returncode"],
            "trace_returncode": result.returncode,
            "trace_started_at_utc": started,
            "trace_file": str(trace_gz_path.relative_to(WORKER_ROOT)),
            "trace_sha256_uncompressed": raw_sha,
            "trace_sha256_compressed": compressed_sha,
            "trace_uncompressed_bytes": len(raw_bytes),
            "trace_compressed_bytes": len(compressed),
            **profile,
        })
        print(json.dumps({"qid": qid, "status": "PASS", "graph_nodes": profile["graph_node_count"], "trace_records": profile["trace_record_count"]}))

    report = {
        "run_id": RUN_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if len(cases) == len(REQUESTS) else "FAIL",
        "evidence_level": "HOST_CPU_SELECTED_REQUEST_GRAPH_METADATA_ONLY",
        "source_project_commit": EXPECTED_SOURCE_COMMIT,
        "source_project_tree_status": "dirty research overlay present; all consumed external files hash-frozen; source tree left unmodified",
        "source_manifest_sha256": sha256(INPUT_MANIFEST),
        "source_run_sha256_for_baseline_provenance_only": "d92fa666e25ad8fb2b9e06d03c806cda890319664bed4fc503f1837bcf066050",
        "source_run_json_values_parsed_by_experiment": False,
        "source_run_sha_verified_as_opaque_bytes": True,
        "runtime_commit": EXPECTED_RUNTIME_COMMIT,
        "model_sha256": sha256(MODEL),
        "mmproj_sha256": sha256(MMPROJ),
        "trace_cli_build": build_record,
        "measurement": "One fresh CPU-only graph metadata trace process for each of four selected host requests, in ascending qid order, using each frozen source command's exact model/image/prompt and inference flags.",
        "output_handling": "CLI stdout and stderr were discarded. No generated answers or dataset answer/annotation fields were stored or inspected. Prompt text is represented only by SHA-256.",
        "trace_semantics": "Node records are logical graph/tensor metadata from the ggml scheduler eval callback during scheduled graph compute after backend splitting. Media batch records identify mtmd_batch_encode calls. Neither is a supports_op eligibility/final backend-placement trace; media batch ids do not identify internal crops.",
        "phase_semantics": "vision_encoder, image_embedding_prefill, text_prefill, and token_decode labels come from the local tracer instrumentation and are not target-board stages or latency measurements.",
        "cases": cases,
        "answer_labels_read": False,
        "generated_answer_text_saved": False,
        "board_or_PL_evidence": False,
        "limitations": [
            "four development examples, not a representative workload distribution",
            "CPU-only metadata traces do not record backend eligibility or prove a K26 dispatch choice",
            "media batch identity is not crop identity",
            "logical tensor sizes are not measured DDR traffic or physical buffer occupancy",
            "this capture does not report latency, accuracy, or method advantage",
            "shape-keyed static dispatch remains the strongest selector control",
        ],
    }
    raw_run = RAW_OUT / "run.json"
    raw_run.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    DERIVED_OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "status": report["status"], "cases": len(cases), "summary": str(DERIVED_OUT)}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
