#!/usr/bin/env python3
"""Compile the locally generated tensor-capture CLI on the KV260 staging host."""
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

ROOT = Path("/home/ubuntu/kv260-vlm-p2-cpu")
SOURCE = Path("/tmp/rm04-tensor-capture/mtmd-cli-optrace.cpp")
OUT = Path("/tmp/rm04-tensor-capture")
BUILD = ROOT / "build-cpu"
PINNED_RUNTIME_COMMIT = "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2"
PINNED_CLI_SHA256 = "92694f41553d76165428deddc11e5100da9bce79f66fd4918b4972bb9e6959bb"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    staged_cli = ROOT / "runtime-src/tools/mtmd/mtmd-cli.cpp"
    if sha(staged_cli) != PINNED_CLI_SHA256:
        raise SystemExit("staged MTMD CLI source hash differs from pinned llama.cpp source")
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
    print(json.dumps({
        "binary": str(binary),
        "binary_sha256": sha(binary),
        "source_sha256": sha(SOURCE),
        "staged_cli_sha256": sha(staged_cli),
        "runtime_commit_for_hash_pinned_source": PINNED_RUNTIME_COMMIT,
    }, indent=2))


if __name__ == "__main__":
    main()
