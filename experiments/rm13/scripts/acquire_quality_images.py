#!/usr/bin/env python3
"""Acquire only the frozen RM13 TextVQA calibration/final JPEGs.

The split manifest and annotation file are inputs; this program does not resample
or edit either one. Images are extracted from TextVQA's official train/val ZIP by
HTTP byte ranges so the full 7 GB archive need not be downloaded.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_SPLIT = ROOT / "experiments/rm13/quality_split_manifest.json"
DEFAULT_ANNOTATION = Path.home() / ".cache/kv260-vlm-literature/TextVQA_0.5.1_val.json"
DEFAULT_OUTPUT = ROOT / "experiments/rm13/data/textvqa_v0.5.1_calibration20_final200"
ANNOTATION_URL = "https://dl.fbaipublicfiles.com/textvqa/data/TextVQA_0.5.1_val.json"
ANNOTATION_SHA256 = "4ceb5aadc1a41719d0a3e4dfdf06838bcfee1db569a9a65ee67d31c99893081d"
IMAGE_ARCHIVE_URL = "https://dl.fbaipublicfiles.com/textvqa/images/train_val_images.zip"
IMAGE_ARCHIVE_SIZE = 7_072_297_970
DATASET_PAGE = "https://textvqa.org/dataset/"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class HTTPRangeFile(io.RawIOBase):
    """Seekable, bounded-block reader for a remote ZIP using HTTP Range."""

    def __init__(self, url: str, expected_size: int, block_size: int = 256 * 1024):
        super().__init__()
        self.url = url
        self.block_size = block_size
        self.position = 0
        self.blocks: dict[int, bytes] = {}
        request = Request(url, headers={"Range": "bytes=0-0", "User-Agent": "RM13 TextVQA data prep"})
        with urlopen(request, timeout=60) as response:
            match = re.fullmatch(r"bytes 0-0/(\d+)", response.headers.get("Content-Range", ""))
            if response.status != 206 or not match:
                raise RuntimeError("official image archive endpoint did not honor the initial byte-range request")
            self.size = int(match.group(1))
        if self.size != expected_size:
            raise RuntimeError(f"image archive size changed: expected {expected_size}, got {self.size}")

    def _get_block(self, number: int) -> bytes:
        if number not in self.blocks:
            start = number * self.block_size
            end = min(self.size, start + self.block_size) - 1
            last_error: Exception | None = None
            for attempt in range(5):
                request = Request(
                    self.url,
                    headers={
                        "Range": f"bytes={start}-{end}",
                        "User-Agent": "RM13 TextVQA data prep",
                    },
                )
                try:
                    with urlopen(request, timeout=90) as response:
                        expected_range = f"bytes {start}-{end}/{self.size}"
                        if response.status != 206 or response.headers.get("Content-Range") != expected_range:
                            raise RuntimeError("server returned a nonmatching Content-Range")
                        data = response.read()
                    if len(data) != end - start + 1:
                        raise RuntimeError("short read from official image archive")
                    self.blocks[number] = data
                    break
                except Exception as error:
                    last_error = error
                    if attempt == 4:
                        raise RuntimeError(f"HTTP range request failed after retries: {last_error}") from last_error
                    time.sleep(1 + attempt)
        return self.blocks[number]

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if whence == os.SEEK_SET:
            target = offset
        elif whence == os.SEEK_CUR:
            target = self.position + offset
        elif whence == os.SEEK_END:
            target = self.size + offset
        else:
            raise ValueError("invalid seek mode")
        if target < 0:
            raise ValueError("negative seek")
        self.position = target
        return target

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = self.size - self.position
        if size > 16 * 1024 * 1024:
            raise RuntimeError("refusing an unexpectedly large remote read")
        end = min(self.position + size, self.size)
        cursor = self.position
        output = bytearray()
        while cursor < end:
            block_number = cursor // self.block_size
            block = self._get_block(block_number)
            within = cursor - block_number * self.block_size
            count = min(end - cursor, len(block) - within)
            if count <= 0:
                raise RuntimeError("empty remote ZIP range block")
            output.extend(block[within : within + count])
            cursor += count
        self.position = end
        return bytes(output)


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".partial", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-manifest", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument("--annotation", type=Path, default=DEFAULT_ANNOTATION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--resume", action="store_true", help="continue an incomplete directory without a final manifest")
    args = parser.parse_args()

    split_path = args.split_manifest.resolve()
    annotation_path = args.annotation.resolve()
    output_dir = args.output_dir.resolve()
    if not split_path.is_file() or not annotation_path.is_file():
        raise SystemExit("split manifest or cached official annotation file is missing")
    split_sha = sha256_file(split_path)
    if split_sha != "5b798932b1ad08c85c6328cceab046f191e9dfbbc0a2df01f971f523eeb2e7b6":
        raise SystemExit(f"frozen split SHA-256 mismatch: {split_sha}")
    annotation_sha = sha256_file(annotation_path)
    if annotation_sha != ANNOTATION_SHA256:
        raise SystemExit(f"official annotation SHA-256 mismatch: {annotation_sha}")
    existing_manifest = output_dir / "manifest.json"
    if existing_manifest.exists():
        raise SystemExit(f"refusing to overwrite acquired dataset manifest: {existing_manifest}")
    if output_dir.exists() and any(output_dir.iterdir()) and not args.resume:
        raise SystemExit(f"refusing to overwrite non-empty dataset directory: {output_dir}; use --resume only for an incomplete acquisition")
    if args.resume and not output_dir.exists():
        raise SystemExit("--resume requires an existing incomplete dataset directory")

    frozen = json.loads(split_path.read_text(encoding="utf-8"))
    source = json.loads(annotation_path.read_text(encoding="utf-8"))
    if (source.get("dataset_name"), source.get("dataset_version"), source.get("dataset_type")) != (
        "textvqa", "0.5.1", "val"
    ):
        raise SystemExit("cached annotation file is not TextVQA v0.5.1 validation")
    annotation_by_qid: dict[int, dict] = {}
    for row in source.get("data", []):
        qid = int(row["question_id"])
        if qid in annotation_by_qid:
            raise SystemExit(f"duplicate question ID in official annotations: {qid}")
        annotation_by_qid[qid] = row

    selected: dict[str, list[dict]] = {}
    qids: set[int] = set()
    image_ids: set[str] = set()
    development_rows = frozen["splits"].get("development", [])
    if len(development_rows) != 50:
        raise SystemExit("frozen development reference must contain exactly 50 QIDs")
    development_qids = {int(row["question_id"]) for row in development_rows}
    development_images = {str(row["image_id"]) for row in development_rows}
    for split in ("calibration", "final_test"):
        rows = frozen["splits"].get(split)
        expected_count = 20 if split == "calibration" else 200
        if not isinstance(rows, list) or len(rows) != expected_count:
            raise SystemExit(f"frozen split {split} must have exactly {expected_count} rows")
        selected[split] = []
        for frozen_row in rows:
            qid = int(frozen_row["question_id"])
            image_id = str(frozen_row["image_id"])
            if qid in qids or image_id in image_ids or qid in development_qids or image_id in development_images:
                raise SystemExit("calibration/final split must be QID- and image-disjoint from itself and development")
            qids.add(qid)
            image_ids.add(image_id)
            row = annotation_by_qid.get(qid)
            if row is None or str(row["image_id"]) != image_id:
                raise SystemExit(f"frozen QID/image pair missing from official annotation: {qid}/{image_id}")
            answers = row.get("answers")
            if not isinstance(answers, list) or len(answers) != 10 or any(not isinstance(x, str) for x in answers):
                raise SystemExit(f"QID {qid} does not have exactly 10 text references")
            selected[split].append({
                "question_id": qid,
                "image_id": image_id,
                "question": row["question"],
                "answers": answers,
            })

    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    archive_stream = HTTPRangeFile(IMAGE_ARCHIVE_URL, IMAGE_ARCHIVE_SIZE)
    image_records: dict[str, dict] = {}
    with zipfile.ZipFile(archive_stream) as archive:
        names = set(archive.namelist())
        for index, image_id in enumerate(sorted(image_ids), start=1):
            member = f"train_images/{image_id}.jpg"
            if member not in names:
                raise RuntimeError(f"official archive is missing validation image {member}")
            target = image_dir / f"{image_id}.jpg"
            if target.exists():
                with archive.open(member) as source_image:
                    source_hash = hashlib.sha256()
                    while chunk := source_image.read(1 << 16):
                        source_hash.update(chunk)
                if sha256_file(target) != source_hash.hexdigest():
                    raise RuntimeError(f"existing image differs from official archive member; preserving it: {target}")
            else:
                with archive.open(member) as source_image, target.open("xb") as target_image:
                    while chunk := source_image.read(1 << 16):
                        target_image.write(chunk)
            with target.open("rb") as image:
                if image.read(3) != b"\xff\xd8\xff":
                    raise RuntimeError(f"archive member is not a JPEG: {member}")
            image_records[image_id] = {
                "path": f"images/{image_id}.jpg",
                "sha256": sha256_file(target),
                "bytes": target.stat().st_size,
                "source_archive_member": member,
            }
            if index % 20 == 0 or index == len(image_ids):
                print(f"verified {index}/{len(image_ids)} images", flush=True)

    for rows in selected.values():
        for row in rows:
            image = image_records[row["image_id"]]
            row["image"] = image["path"]
            row["image_sha256"] = image["sha256"]

    dataset_manifest = {
        "kind": "rm13_textvqa_v0.5.1_quality_dataset_v1",
        "frozen_split_manifest": "experiments/rm13/quality_split_manifest.json",
        "frozen_split_manifest_sha256": split_sha,
        "source": {
            "dataset_page": DATASET_PAGE,
            "annotation_url": ANNOTATION_URL,
            "annotation_sha256": annotation_sha,
            "image_archive_url": IMAGE_ARCHIVE_URL,
            "image_archive_size_bytes": IMAGE_ARCHIVE_SIZE,
            "official_license": "CC BY 4.0",
            "license_url": LICENSE_URL,
        },
        "source_split": "validation",
        "purpose": "RM13 frozen calibration and held-out final quality screen; not official test split",
        "image_count": len(image_records),
        "images": image_records,
        "splits": selected,
    }
    atomic_json(output_dir / "manifest.json", dataset_manifest)
    atomic_json(output_dir / "acquisition.json", {
        "split_manifest_sha256": split_sha,
        "annotation_sha256": annotation_sha,
        "image_archive_url": IMAGE_ARCHIVE_URL,
        "image_archive_size_bytes": archive_stream.size,
        "image_count": len(image_records),
        "http_range_blocks_cached": len(archive_stream.blocks),
        "http_range_bytes_cached": sum(map(len, archive_stream.blocks.values())),
    })
    print(json.dumps({
        "output_dir": str(output_dir),
        "calibration_questions": len(selected["calibration"]),
        "final_questions": len(selected["final_test"]),
        "unique_images": len(image_records),
        "split_sha256": split_sha,
        "annotation_sha256": annotation_sha,
        "image_archive_blocks_read": len(archive_stream.blocks),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
