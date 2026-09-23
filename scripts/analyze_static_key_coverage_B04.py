#!/usr/bin/env python3
"""Summarize full and coarse static keys in the four frozen B03 vision traces."""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRACE_ROOT = ROOT / "experiments/raw/textvqa_selected_optrace_B03"
GROUP_SUMMARY = ROOT / "experiments/derived/selected_qid_optrace_B03_group_shapes.json"
OUTPUT_JSON = ROOT / "experiments/derived/static_key_coverage_B04.json"
OUTPUT_MD = ROOT / "experiments/derived/static_key_coverage_B04.md"
QIDS = (34609, 35005, 35419, 35950)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_key(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def tensor_signature(tensor: dict[str, Any]) -> dict[str, Any]:
    # Intentionally excludes IDs, names, byte addresses, flags and storage metadata.
    return {
        "dtype": tensor["dtype"],
        "ne": list(tensor["ne"]),
        "nb": list(tensor["nb"]),
    }


def full_key(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "op": record["op"],
        "inputs": [tensor_signature(t) for t in record["inputs"]],
        "output": tensor_signature(record["output"]),
    }


def keyset_digest(keys: set[str]) -> str:
    return sha256_bytes("\n".join(sorted(keys)).encode("ascii"))


def load_group_summary() -> tuple[dict[int, dict[str, Any]], dict[str, str]]:
    obj = json.loads(GROUP_SUMMARY.read_text(encoding="utf-8"))
    expected = {int(row["question_id"]): row for row in obj["requests"]}
    trace_hashes = {str(k): v for k, v in obj["source_trace_sha256_compressed"].items()}
    if set(expected) != set(QIDS) or set(map(int, trace_hashes)) != set(QIDS):
        raise ValueError("B03 group summary does not contain exactly the four frozen qids")
    return expected, trace_hashes


def read_trace(qid: int, expected_sha: str, expected_groups: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = TRACE_ROOT / f"qid_{qid}_op_trace.jsonl.gz"
    compressed_sha = sha256_file(path)
    if compressed_sha != expected_sha:
        raise ValueError(f"compressed trace SHA mismatch for qid {qid}")

    uncompressed = hashlib.sha256()
    media_batches: dict[int, dict[str, Any]] = {}
    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    records = 0
    vision_nodes = 0
    keyed_records = 0
    request_ids: set[str] = set()

    with gzip.open(path, "rb") as stream:
        for raw in stream:
            uncompressed.update(raw)
            if not raw.strip():
                continue
            row = json.loads(raw)
            records += 1
            if "request_id" in row:
                request_ids.add(str(row["request_id"]))
            if row.get("record") == "media_batch":
                group = int(row["group"])
                media_batches[group] = {
                    "group": group,
                    "chunk_index": int(row["chunk_index"]),
                    "chunks_added": int(row["chunks_added"]),
                    "chunks_total": int(row["chunks_total"]),
                }
            elif row.get("record") == "node" and row.get("phase") == "vision_encoder":
                group = int(row["group"])
                key = full_key(row)
                digest = digest_key(key)
                output_ne = list(row["output"]["ne"])
                shape_key = {"op": row["op"], "output_ne": output_ne}
                gemm_key = None
                if row["op"] == "MUL_MAT":
                    src0 = row["inputs"][0]
                    # GGML MUL_MAT: output [M,N,...], K is src0.ne[0].
                    gemm_key = {
                        "op": "MUL_MAT",
                        "M": int(output_ne[0]),
                        "N": int(output_ne[1]),
                        "K": int(src0["ne"][0]),
                    }
                groups[group].append({
                    "full_digest": digest,
                    "full_key": key,
                    "shape_digest": digest_key(shape_key),
                    "shape_key": shape_key,
                    "gemm_digest": digest_key(gemm_key) if gemm_key is not None else None,
                    "gemm_key": gemm_key,
                })
                vision_nodes += 1
                keyed_records += 1

    if request_ids != {str(qid)}:
        raise ValueError(f"request_id mismatch in qid {qid} trace")
    if len(media_batches) != expected_groups or len(groups) != expected_groups:
        raise ValueError(f"media-group count mismatch in qid {qid} trace")
    if sorted(media_batches) != list(range(expected_groups)):
        raise ValueError(f"unexpected media-group ordinals in qid {qid} trace")

    trace_info = {
        "path": str(path.relative_to(ROOT)),
        "compressed_sha256": compressed_sha,
        "uncompressed_sha256": uncompressed.hexdigest(),
        "record_count_including_media_batch_markers": records,
        "vision_node_records": vision_nodes,
        "vision_records_with_complete_full_key": keyed_records,
        "media_batches": [media_batches[i] for i in sorted(media_batches)],
    }
    parsed_groups = [{"group": i, "nodes": groups[i]} for i in sorted(groups)]
    return trace_info, parsed_groups


def analyze() -> dict[str, Any]:
    expected, trace_hashes = load_group_summary()
    summary_sha = sha256_file(GROUP_SUMMARY)
    all_groups: list[dict[str, Any]] = []
    per_request: list[dict[str, Any]] = []
    catalog: dict[str, dict[str, Any]] = {}
    gemm_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"key": None, "full": set(), "records": 0})
    shape_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"key": None, "full": set(), "records": 0})

    for qid in QIDS:
        expected_groups = int(expected[qid]["encoded_media_batch_count"])
        trace_info, groups = read_trace(qid, trace_hashes[str(qid)], expected_groups)
        request_full: set[str] = set()
        request_gemm: set[str] = set()
        request_shape: set[str] = set()
        group_rows = []
        for group in groups:
            group_id = int(group["group"])
            nodes = group["nodes"]
            full_set: set[str] = set()
            gemm_set: set[str] = set()
            shape_set: set[str] = set()
            op_counts: dict[str, int] = defaultdict(int)
            for node in nodes:
                fd = node["full_digest"]
                full_set.add(fd)
                request_full.add(fd)
                shape_set.add(node["shape_digest"])
                request_shape.add(node["shape_digest"])
                op_counts[node["full_key"]["op"]] += 1
                item = catalog.setdefault(fd, {"key": node["full_key"], "node_records": 0, "qids": set(), "groups": set()})
                item["node_records"] += 1
                item["qids"].add(qid)
                item["groups"].add(f"{qid}:{group_id}")
                sd = node["shape_digest"]
                shape_map[sd]["key"] = node["shape_key"]
                shape_map[sd]["full"].add(fd)
                shape_map[sd]["records"] += 1
                if node["gemm_digest"] is not None:
                    gd = node["gemm_digest"]
                    gemm_set.add(gd)
                    request_gemm.add(gd)
                    gemm_map[gd]["key"] = node["gemm_key"]
                    gemm_map[gd]["full"].add(fd)
                    gemm_map[gd]["records"] += 1
            group_fingerprint = keyset_digest(full_set)
            group_row = {
                "qid": qid,
                "group": group_id,
                "vision_node_records": len(nodes),
                "unique_full_keys": len(full_set),
                "unique_gemm_mnk_keys": len(gemm_set),
                "unique_op_output_shape_keys": len(shape_set),
                "full_key_set_sha256": group_fingerprint,
                "op_node_counts": dict(sorted(op_counts.items())),
            }
            group_rows.append(group_row)
            all_groups.append(group_row)

        if trace_info["vision_node_records"] != trace_info["vision_records_with_complete_full_key"]:
            raise ValueError(f"incomplete full-key coverage in qid {qid}")
        if trace_info["vision_node_records"] != sum(row["vision_node_records"] for row in group_rows):
            raise ValueError(f"group node counts do not reconcile for qid {qid}")
        per_request.append({
            "qid": qid,
            "trace": trace_info,
            "vision_node_full_key_field_completeness_fraction": 1.0,
            "vision_node_records": trace_info["vision_node_records"],
            "unique_full_keys": len(request_full),
            "unique_gemm_mnk_keys": len(request_gemm),
            "unique_op_output_shape_keys": len(request_shape),
            "groups": group_rows,
        })

    equivalence: dict[str, list[str]] = defaultdict(list)
    for row in all_groups:
        equivalence[row["full_key_set_sha256"]].append(f"{row['qid']}:{row['group']}")

    cross_request_reuse: dict[str, int] = defaultdict(int)
    catalog_rows = []
    for fd, item in sorted(catalog.items()):
        qids = sorted(item["qids"])
        if len(qids) > 1:
            cross_request_reuse["shared_full_key_count"] += 1
            cross_request_reuse["shared_full_key_node_records"] += item["node_records"]
            for i, left in enumerate(qids):
                for right in qids[i + 1:]:
                    cross_request_reuse[f"shared_keys_q{left}_q{right}"] += 1
        catalog_rows.append({
            "full_key_sha256": fd,
            "key": item["key"],
            "node_records": item["node_records"],
            "qids": qids,
            "group_count": len(item["groups"]),
        })

    def collision_rows(index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for key_digest, item in index.items():
            if len(item["full"]) > 1:
                rows.append({
                    "coarse_key": item["key"],
                    "coarse_key_sha256": key_digest,
                    "node_records": item["records"],
                    "distinct_full_key_count": len(item["full"]),
                    "full_key_sha256s": sorted(item["full"]),
                })
        return sorted(rows, key=lambda row: (-row["distinct_full_key_count"], -row["node_records"], row["coarse_key_sha256"]))

    return {
        "evidence_level": "OFFLINE_GRAPH_METADATA_KEY_COVERAGE",
        "scope": "vision_encoder nodes in four frozen B03 traces; no inference or model/answer files read",
        "group_summary": {
            "path": str(GROUP_SUMMARY.relative_to(ROOT)),
            "sha256": summary_sha,
        },
        "signature_field_completeness_definition": "Fraction of vision node records with op and ordered input/output dtype, ne, nb fields needed to construct the canonical key; metadata extractability only, not backend eligibility, dispatch, or scheduling coverage.",
        "key_definitions": {
            "full": "op plus ordered input/output dtype, ne, nb; excludes ids, names, request/group identity, addresses and storage metadata",
            "gemm_mnk": "MUL_MAT only: op, M=output.ne[0], N=output.ne[1], K=input[0].ne[0]",
            "op_output_shape": "all vision ops: op plus output.ne; intentionally drops dtype, strides and inputs",
        },
        "requests": per_request,
        "cross_group_full_key_set_equivalence_classes": [
            {"full_key_set_sha256": fp, "groups": sorted(members)}
            for fp, members in sorted(equivalence.items(), key=lambda item: (item[0], item[1]))
        ],
        "cross_request_full_key_reuse": dict(sorted(cross_request_reuse.items())),
        "unique_full_key_catalog": catalog_rows,
        "coarse_key_collision_summary": {
            "gemm_mnk": {
                "scope": "MUL_MAT nodes only",
                "coarse_key_count": len(gemm_map),
                "colliding_coarse_key_count": sum(1 for v in gemm_map.values() if len(v["full"]) > 1),
                "collisions": collision_rows(gemm_map),
            },
            "op_output_shape": {
                "scope": "all vision nodes",
                "coarse_key_count": len(shape_map),
                "colliding_coarse_key_count": sum(1 for v in shape_map.values() if len(v["full"]) > 1),
                "collisions": collision_rows(shape_map),
            },
        },
        "limitations": [
            "Media-group ordinals identify encoded media-batch calls, not crop identities.",
            "The graph callback runs after backend splitting; these traces cannot validate supports_op eligibility or final K26 placement.",
            "Key collisions describe metadata coalescing only, not accelerator cost, placement, bandwidth, resource pressure, or performance.",
        ],
    }


def render_markdown(result: dict[str, Any], script_sha: str) -> str:
    lines = [
        "# B04 static per-op key coverage",
        "",
        "This offline analysis covers vision-encoder graph-node metadata in four frozen B03 traces. It does not read prompt, image, model, answer, or annotation artifacts.",
        "",
        "| Qid | Vision node records | Distinct full keys | Signature fields complete | Groups: full-key uniques | GEMM M/N/K keys | Op/output-shape keys |",
        "|---:|---:|---:|---:|---|---:|---:|",
    ]
    for req in result["requests"]:
        group_counts = ", ".join(f"{g['group']}:{g['unique_full_keys']}" for g in req["groups"])
        lines.append(
            f"| {req['qid']} | {req['vision_node_records']} | {req['unique_full_keys']} | 100% | {group_counts} | {req['unique_gemm_mnk_keys']} | {req['unique_op_output_shape_keys']} |"
        )
    eq_classes = result["cross_group_full_key_set_equivalence_classes"]
    gemm = result["coarse_key_collision_summary"]["gemm_mnk"]
    shape = result["coarse_key_collision_summary"]["op_output_shape"]
    reuse = result["cross_request_full_key_reuse"]
    eq_members = [", ".join(row["groups"]) for row in eq_classes]
    sample = next((row for row in shape["collisions"] if row["coarse_key"].get("op") == "MUL_MAT" and row["coarse_key"].get("output_ne") == [1152, 252, 1, 1]), None)
    sample_k = []
    if sample:
        digests = set(sample["full_key_sha256s"])
        sample_k = sorted({
            entry["key"]["inputs"][0]["ne"][0]
            for entry in result["unique_full_key_catalog"]
            if entry["full_key_sha256"] in digests
        })
    lines += [
        "",
        f"All {sum(req['vision_node_records'] for req in result['requests']):,} vision records contain metadata needed to construct a full key; there are {len(result['unique_full_key_catalog'])} distinct full keys. Full-key-set equivalence classes: {len(eq_classes)}. {reuse.get('shared_full_key_count', 0)} full keys recur across requests.",
        "",
        f"Group-set classes: {'; '.join(eq_members)}.",
        "",
        f"Coarser GEMM M/N/K keys: {gemm['coarse_key_count']} keys, {gemm['colliding_coarse_key_count']} merge multiple full keys. Op/output-shape keys: {shape['coarse_key_count']} keys, {shape['colliding_coarse_key_count']} merge multiple full keys. The JSON lists each collision and the full-key digests it merges.",
        "",
        f"Example: `MUL_MAT` output `[1152,252,1,1]` has three full keys with input-0 K values {sample_k}; output-shape-only merges them, while M/N/K separates them.",
        "",
        "The full static key represents all observed per-node shape/type/stride variation in these traces. Group ordinal is not needed to distinguish a node signature; different group key sets are distinguished by their node metadata. Treat media groups as encoded media-batch calls, not crop identities.",
        "",
        "## Evidence boundary",
        "",
        "The recorded graph callback runs after backend splitting. This analysis cannot validate `supports_op` eligibility, backend placement, or final K26 behavior. Coarse-key collisions are metadata collisions only; they do not imply cost, placement failure, bandwidth, pressure, or performance. No latency or hardware claim follows.",
        "",
        f"Source group-summary SHA-256: `{result['group_summary']['sha256']}`. Analyzer SHA-256: `{script_sha}`.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    result = analyze()
    script_sha = sha256_file(Path(__file__))
    result["tool"] = {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": script_sha}
    OUTPUT_JSON.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result, script_sha), encoding="utf-8")


if __name__ == "__main__":
    main()
