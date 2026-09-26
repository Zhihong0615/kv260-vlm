#!/usr/bin/env python3
"""Compile the generated FFN-up capture CLI against the pinned board runtime."""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from pathlib import Path

BOARD_ROOT = Path(os.environ.get("RM11_BOARD_ROOT", "/home/ubuntu/kv260-vlm-p2-cpu"))
OUT = Path(os.environ.get("RM11_CAPTURE_ROOT", "/tmp/rm11-ffn-up-capture"))
SOURCE = OUT / "mtmd-cli-optrace.cpp"
BUILD = BOARD_ROOT / "build-cpu"
PINNED_RUNTIME_COMMIT = "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2"
PINNED_CLI_SHA256 = "92694f41553d76165428deddc11e5100da9bce79f66fd4918b4972bb9e6959bb"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    staged_cli = BOARD_ROOT / "runtime-src/tools/mtmd/mtmd-cli.cpp"
    if sha(staged_cli) != PINNED_CLI_SHA256:
        raise SystemExit("staged MTMD CLI source hash differs from pinned llama.cpp source")
    if not SOURCE.is_file():
        raise SystemExit(f"missing generated source: {SOURCE}")
    db = json.loads((BUILD / "compile_commands.json").read_text())
    entry = next(e for e in db if e["file"].endswith("/tools/mtmd/mtmd-cli.cpp"))
    cmd = shlex.split(entry["command"])
    obj = OUT / "mtmd-cli-optrace.o"
    for i, arg in enumerate(cmd):
        if arg == entry["file"]:
            cmd[i] = str(SOURCE)
        if arg == "-o":
            cmd[i + 1] = str(obj)
    subprocess.run(cmd, cwd=entry["directory"], check=True)

    libs = [
        BUILD / "bin/libllama-common.so.0.4.1",
        BUILD / "bin/libmtmd.so.0.4.1",
        BUILD / "common/libllama-common-base.a",
        BUILD / "bin/libllama.so.0.4.1",
        BUILD / "bin/libggml.so.0.24.0",
        BUILD / "bin/libggml-cpu.so.0.24.0",
        BUILD / "bin/libggml-base.so.0.24.0",
    ]
    missing = [str(p) for p in libs if not p.is_file()]
    if missing:
        raise SystemExit("missing staged runtime libraries: " + ", ".join(missing))
    binary = OUT / "llama-mtmd-optrace"
    subprocess.run(
        ["/usr/bin/c++", "-O3", "-DNDEBUG", "-o", str(binary), str(obj),
         f"-Wl,-rpath,{BUILD / 'bin'}", *map(str, libs)],
        cwd=BUILD,
        check=True,
    )
    report = {
        "binary": str(binary),
        "binary_sha256": sha(binary),
        "generated_source_sha256": sha(SOURCE),
        "staged_upstream_source_sha256": sha(staged_cli),
        "runtime_commit_for_hash_pinned_source": PINNED_RUNTIME_COMMIT,
        "capture_names": ["ffn_up-0", "ffn_up-13", "ffn_up-26"],
        "linked_libraries": [{"name": p.name, "sha256": sha(p)} for p in libs],
    }
    report_path = OUT / "build.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
