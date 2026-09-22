#!/usr/bin/env python3
"""Write a reproducibility manifest only when all requested model artifacts exist."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--hf-repo", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--processor-revision", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--mmproj", type=Path, required=True)
    parser.add_argument("--quantized", type=Path, required=True)
    parser.add_argument("--quantization", required=True)
    parser.add_argument("--conversion-command", required=True)
    args = parser.parse_args()

    artifacts = [args.checkpoint, args.gguf, args.mmproj, args.quantized]
    missing = [str(path) for path in artifacts if not path.is_file()]
    if missing:
        parser.error("missing artifact(s): " + ", ".join(missing))

    root = args.project_root.resolve()
    llama_dir = root / "runtime" / "llama.cpp"
    llama_commit = subprocess.check_output(["git", "-C", str(llama_dir), "rev-parse", "HEAD"], text=True).strip()
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_repo": args.hf_repo,
        "model_revision": args.revision,
        "processor_revision": args.processor_revision,
        "llama_cpp_commit": llama_commit,
        "transformers_version": version("transformers"),
        "huggingface_hub_version": version("huggingface-hub"),
        "torch_version": version("torch"),
        "conversion_command": args.conversion_command,
        "quantization_format": args.quantization,
        "artifacts": [
            {"path": str(path.resolve().relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in artifacts
        ],
    }
    manifest_path = root / "models" / "manifests" / "model_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    sums_path = root / "models" / "SHA256SUMS"
    sums_path.write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in manifest["artifacts"]),
        encoding="utf-8",
    )
    print(manifest_path)
    print(sums_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
