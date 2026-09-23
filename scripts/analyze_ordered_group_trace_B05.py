#!/usr/bin/env python3
"""Compare ordered vision-node key sequences across frozen B03 media groups."""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRACE_ROOT = ROOT / "experiments/raw/textvqa_selected_optrace_B03"
B04_JSON = ROOT / "experiments/derived/static_key_coverage_B04.json"
SOURCE_MANIFEST = ROOT / "orchestration/evidence_snapshots/B05_ordered_group_trace_audit/SOURCE.sha256"
OUTPUT_JSON = ROOT / "experiments/derived/ordered_group_trace_audit_B05.json"
OUTPUT_MD = ROOT / "experiments/derived/ordered_group_trace_audit_B05.md"
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


def digest(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def tensor_signature(tensor: dict[str, Any]) -> dict[str, Any]:
    # Keep exactly B04's ordered tensor fields; all names, ids and storage data are omitted.
    return {
        "dtype": tensor["dtype"],
        "ne": list(tensor["ne"]),
        "nb": list(tensor["nb"]),
    }


def full_key(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "op": record["op"],
        "inputs": [tensor_signature(tensor) for tensor in record["inputs"]],
        "output": tensor_signature(record["output"]),
    }


def key_set_digest(keys: set[str]) -> str:
    # Match B04's exact group-set fingerprint.
    return sha256_bytes("\n".join(sorted(keys)).encode("ascii"))


def read_manifest() -> list[dict[str, str]]:
    rows = []
    for line in SOURCE_MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, path = line.split(maxsplit=1)
        rows.append({"path": path.strip(), "sha256": expected})
    return rows


def load_b04() -> tuple[dict[int, dict[int, str]], dict[int, dict[str, Any]]]:
    obj = json.loads(B04_JSON.read_text(encoding="utf-8"))
    expected_sets: dict[int, dict[int, str]] = {}
    expected_requests: dict[int, dict[str, Any]] = {}
    for request in obj["requests"]:
        qid = int(request["qid"])
        expected_requests[qid] = request
        expected_sets[qid] = {
            int(group["group"]): str(group["full_key_set_sha256"])
            for group in request["groups"]
        }
    if tuple(sorted(expected_sets)) != QIDS:
        raise ValueError("B04 summary does not contain exactly the four frozen requests")
    return expected_sets, expected_requests


def read_trace(qid: int, expected_request: dict[str, Any]) -> dict[str, Any]:
    path = TRACE_ROOT / f"qid_{qid}_op_trace.jsonl.gz"
    compressed_sha = sha256_file(path)
    expected_sha = str(expected_request["trace"]["compressed_sha256"])
    if compressed_sha != expected_sha:
        raise ValueError(f"compressed trace SHA mismatch for qid {qid}")

    uncompressed_hash = hashlib.sha256()
    groups: dict[int, list[str]] = defaultdict(list)
    boundaries: list[dict[str, int]] = []
    with gzip.open(path, "rb") as stream:
        for raw in stream:
            uncompressed_hash.update(raw)
            if not raw.strip():
                continue
            row = json.loads(raw)
            record_type = row.get("record")
            if record_type == "media_batch":
                boundaries.append({
                    "group": int(row["group"]),
                    "chunk_index": int(row["chunk_index"]),
                    "chunks_added": int(row["chunks_added"]),
                    "chunks_total": int(row["chunks_total"]),
                })
            elif record_type == "node" and row.get("phase") == "vision_encoder":
                group = int(row["group"])
                groups[group].append(digest(full_key(row)))

    boundary_groups = [row["group"] for row in boundaries]
    if len(boundary_groups) != len(set(boundary_groups)):
        raise ValueError(f"duplicate media_batch boundary in qid {qid}")
    if boundary_groups != [int(row["group"]) for row in expected_request["trace"]["media_batches"]]:
        raise ValueError(f"media_batch boundary order mismatch against B04 for qid {qid}")
    if set(groups) != set(boundary_groups):
        raise ValueError(f"vision groups do not match media_batch boundaries for qid {qid}")

    group_rows = []
    for boundary in boundaries:
        group_id = boundary["group"]
        sequence = groups[group_id]
        counts = Counter(sequence)
        transitions = Counter(zip(sequence, sequence[1:]))
        sorted_counts = [[key, counts[key]] for key in sorted(counts)]
        transition_rows = [
            {"from_full_key_sha256": left, "to_full_key_sha256": right, "count": count}
            for (left, right), count in sorted(transitions.items())
        ]
        group_rows.append({
            **boundary,
            "qid": qid,
            "vision_node_records": len(sequence),
            "unique_full_keys": len(counts),
            "full_key_set_sha256": key_set_digest(set(sequence)),
            "full_key_multiset_sha256": digest(sorted_counts),
            "ordered_full_key_sequence_sha256": digest(sequence),
            "adjacent_transition_count": max(0, len(sequence) - 1),
            "distinct_adjacent_transitions": len(transitions),
            "adjacent_transition_profile_sha256": digest(transition_rows),
            "full_key_counts": {key: counts[key] for key in sorted(counts)},
            "adjacent_transition_counts": transition_rows,
            "_sequence": sequence,
        })

    return {
        "qid": qid,
        "trace_path": str(path.relative_to(ROOT)),
        "compressed_sha256": compressed_sha,
        "uncompressed_sha256": uncompressed_hash.hexdigest(),
        "media_batch_boundaries": boundaries,
        "groups": group_rows,
    }


def group_name(row: dict[str, Any]) -> str:
    return f"{row['qid']}:{row['group']}"


def equivalence_classes(rows: list[dict[str, Any]], field: str) -> list[list[str]]:
    classes: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        classes[str(row[field])].append(group_name(row))
    return sorted((sorted(items) for items in classes.values()), key=lambda items: (len(items), items))


def analyze() -> dict[str, Any]:
    b04_sets, b04_requests = load_b04()
    requests = [read_trace(qid, b04_requests[qid]) for qid in QIDS]
    groups = [group for request in requests for group in request["groups"]]

    b04_match_rows = []
    for group in groups:
        expected = b04_sets[int(group["qid"])][int(group["group"])]
        matches = group["full_key_set_sha256"] == expected
        b04_match_rows.append({"group": group_name(group), "matches_b04_full_key_set": matches})
        if not matches:
            raise ValueError(f"reconstructed key set differs from B04 for {group_name(group)}")

    same_set_different_sequence = []
    same_multiset_different_sequence = []
    same_set_different_multiset = []
    for left, right in combinations(groups, 2):
        pair = [group_name(left), group_name(right)]
        same_set = left["full_key_set_sha256"] == right["full_key_set_sha256"]
        same_multiset = left["full_key_multiset_sha256"] == right["full_key_multiset_sha256"]
        same_sequence = left["ordered_full_key_sequence_sha256"] == right["ordered_full_key_sequence_sha256"]
        if same_set and not same_sequence:
            same_set_different_sequence.append({
                "groups": pair,
                "same_full_key_multiset": same_multiset,
                "canonicalized_multiset_collapses_order_difference": same_multiset,
            })
        if same_multiset and not same_sequence:
            same_multiset_different_sequence.append({"groups": pair})
        if same_set and not same_multiset:
            same_set_different_multiset.append({"groups": pair})

    set_classes = equivalence_classes(groups, "full_key_set_sha256")
    multiset_classes = equivalence_classes(groups, "full_key_multiset_sha256")
    sequence_classes = equivalence_classes(groups, "ordered_full_key_sequence_sha256")
    transition_classes = equivalence_classes(groups, "adjacent_transition_profile_sha256")
    same_partition = (
        set_classes == multiset_classes == sequence_classes == transition_classes
    )

    for request in requests:
        for group in request["groups"]:
            del group["_sequence"]

    return {
        "evidence_level": "OFFLINE_ORDERED_GRAPH_METADATA_TRACE_AUDIT",
        "scope": "vision_encoder node records and media_batch boundaries in the four frozen B03 compressed traces only",
        "key_definition": "B04 full key: op plus ordered input/output dtype, ne, nb; excludes names, ids, addresses, group/request identity, and storage metadata",
        "canonicalization_definitions": {
            "set": "unique full-key digests sorted before hashing, exactly matching B04",
            "multiset": "full-key digests with occurrence counts sorted by digest; removes order but retains multiplicity",
            "sequence": "full-key digests in trace order inside each media group",
            "adjacent_transitions": "ordered pairs of adjacent full-key digests with occurrence counts",
        },
        "source_manifest": {
            "path": str(SOURCE_MANIFEST.relative_to(ROOT)),
            "sha256": sha256_file(SOURCE_MANIFEST),
            "entries": read_manifest(),
        },
        "b04_comparison": {
            "path": str(B04_JSON.relative_to(ROOT)),
            "sha256": sha256_file(B04_JSON),
            "all_reconstructed_group_key_sets_match_b04": all(row["matches_b04_full_key_set"] for row in b04_match_rows),
            "groups_checked": b04_match_rows,
        },
        "requests": requests,
        "comparison_summary": {
            "media_group_count": len(groups),
            "group_full_key_set_class_count": len(set_classes),
            "group_full_key_multiset_class_count": len(multiset_classes),
            "group_ordered_sequence_class_count": len(sequence_classes),
            "group_adjacent_transition_profile_class_count": len(transition_classes),
            "set_multiset_sequence_transition_partitions_identical": same_partition,
            "full_key_set_equivalence_classes": set_classes,
            "full_key_multiset_equivalence_classes": multiset_classes,
            "ordered_sequence_equivalence_classes": sequence_classes,
            "adjacent_transition_profile_equivalence_classes": transition_classes,
            "same_full_key_set_but_different_ordered_sequence_pairs": same_set_different_sequence,
            "same_multiset_but_different_ordered_sequence_pairs": same_multiset_different_sequence,
            "same_set_but_different_multiplicity_pairs": same_set_different_multiset,
        },
        "limits": [
            "The four requests are selected development examples, not a population estimate.",
            "Media-batch ordinals are encoded-call boundaries, not crop identities.",
            "The graph records do not establish backend placement, measured cost, resource use, traffic, or performance.",
            "Sequence fingerprints describe these recorded traces and do not prove a runtime selector can observe or needs to use them.",
        ],
    }


def render_markdown(result: dict[str, Any], analyzer_sha: str) -> str:
    rows = [
        "# B05 ordered media-group trace audit",
        "",
        "Evidence level: **offline graph metadata only**. Scope is the vision-encoder node records and `media_batch` boundaries in the four frozen B03 traces. No prompt, image, model, answer, annotation, or run-manifest case contents were inspected.",
        "",
        "The full key exactly matches B04: op plus ordered input/output `(dtype, ne, nb)`. Names, IDs, addresses, request/group identity, and storage metadata are excluded. Node order is preserved within each media group.",
        "",
        "| Qid | Groups | Vision node records | B04 set fingerprints matched |",
        "|---:|---:|---:|---|",
    ]
    for request in result["requests"]:
        count = sum(group["vision_node_records"] for group in request["groups"])
        rows.append(f"| {request['qid']} | {len(request['groups'])} | {count} | yes |")

    summary = result["comparison_summary"]
    rows += [
        "",
        f"Across {summary['media_group_count']} groups, there are {summary['group_full_key_set_class_count']} key-set classes, {summary['group_full_key_multiset_class_count']} multiplicity-preserving unordered classes, {summary['group_ordered_sequence_class_count']} ordered-sequence classes, and {summary['group_adjacent_transition_profile_class_count']} adjacent-transition-profile classes.",
        "",
        "Full-key-set, multiplicity-preserving multiset, ordered-sequence, and adjacent-transition partitions are identical: "
        + ("yes" if summary["set_multiset_sequence_transition_partitions_identical"] else "no")
        + ". Classes: "
        + "; ".join(", ".join(group_class) for group_class in summary["full_key_set_equivalence_classes"])
        + ".",
        "",
        "## Per-group fingerprints and boundaries",
        "",
        "| Group | Boundary (chunk index; added/total) | Nodes | Unique keys | Set SHA-256 (prefix) | Multiset SHA-256 (prefix) | Ordered sequence SHA-256 (prefix) | Adjacent transitions (distinct/total) |",
        "|---|---:|---:|---:|---|---|---|---:|",
    ]
    for request in result["requests"]:
        for group in request["groups"]:
            rows.append(
                f"| {request['qid']}:{group['group']} | {group['chunk_index']}; {group['chunks_added']}/{group['chunks_total']} | {group['vision_node_records']} | {group['unique_full_keys']} | `{group['full_key_set_sha256'][:12]}` | `{group['full_key_multiset_sha256'][:12]}` | `{group['ordered_full_key_sequence_sha256'][:12]}` | {group['distinct_adjacent_transitions']}/{group['adjacent_transition_count']} |"
            )

    pairs = summary["same_full_key_set_but_different_ordered_sequence_pairs"]
    rows += ["", "## Same-set, different-sequence pairs", ""]
    if pairs:
        rows += ["| Groups | Same multiplicities after sorting? | Sequence difference disappears after multiset canonicalization? |", "|---|---|---|"]
        for item in pairs:
            rows.append(
                f"| {', '.join(item['groups'])} | {'yes' if item['same_full_key_multiset'] else 'no'} | {'yes' if item['canonicalized_multiset_collapses_order_difference'] else 'no'} |"
            )
    else:
        rows.append("None. No pair of groups has the same full-key set and a different ordered sequence in these four traces.")

    order_only = summary["same_multiset_but_different_ordered_sequence_pairs"]
    rows += ["", "## Sequence distinctions removed by canonicalization", ""]
    if order_only:
        rows.append("Sorting the full-key multiset removes these order-only distinctions:")
        for item in order_only:
            rows.append(f"- {item['groups'][0]} vs {item['groups'][1]}")
    else:
        rows.append("None: no distinct ordered sequences share an identical multiplicity-preserving full-key multiset.")

    rows += [
        "",
        "## Static null and recommendation",
        "",
        "Every reconstructed full-key set matches its B04 group fingerprint. Any group distinction visible in the set is already encoded by node metadata. The ordered-sequence and adjacent-transition fingerprints further summarize order; these finite traces do not show that a dynamic group-ordinal selector is necessary. A per-op full-key dispatch plus a static ordered-sequence/replay table is the strongest static null supported here. Media-group ordinals remain encoded-call boundaries, not crop identities.",
        "",
        "**Recommendation: stop** pursuing a group-aware dynamic selector from these traces. If measured submission/wait cost becomes a separate question, it needs a separately gated timing experiment against the static sequence/replay table; this audit makes no cost or performance claim.",
        "",
        "## Integrity and limits",
        "",
        f"All {len(result['source_manifest']['entries'])} frozen manifest entries passed the pre-analysis SHA-256 check; the handoff records the required post-analysis verification. B04 group-set comparison: {summary['media_group_count']}/{summary['media_group_count']} exact matches. The source traces are immutable inputs.",
        "",
        "This is a finite audit of four selected development requests. It does not establish crop identity, dynamic selector visibility, backend placement, cost, resource pressure, allocation/liveness, traffic, novelty, or performance. P3 `NO_GO_NOW` remains unchanged.",
        "",
        f"Source manifest SHA-256: `{result['source_manifest']['sha256']}`. B04 result SHA-256: `{result['b04_comparison']['sha256']}`. Analyzer SHA-256: `{analyzer_sha}`.",
        "",
    ]
    return "\n".join(rows)


def main() -> None:
    result = analyze()
    analyzer_sha = sha256_file(Path(__file__))
    result["analyzer"] = {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": analyzer_sha}
    OUTPUT_JSON.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result, analyzer_sha), encoding="utf-8")


if __name__ == "__main__":
    main()
