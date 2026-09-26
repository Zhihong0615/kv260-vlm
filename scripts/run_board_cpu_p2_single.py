#!/usr/bin/env python3
"""Plan or run one bounded KV260 CPU-only synthetic image-QA request.

Dry plan is the default and performs no SSH or board operation.  --execute is
for an already authorized P2 CPU-only window after the human owner check.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_MANIFEST = ROOT / "models/manifests/model_manifest.json"
SMOKE_MANIFEST = ROOT / "datasets/smoke/manifest.json"
PREFLIGHT_SOURCE = ROOT / "scripts/board_cpu_preflight_remote.py"
SOURCE_VERIFIER = ROOT / "scripts/verify_board_source_archive_remote.py"
RAW_PARENT = ROOT / "experiments/raw"
BUILD_ATTESTATION = RAW_PARENT / "kv260_cpu_p2_baseline_round01/cpu_build_attestation_v1.json"
PINNED_RUNTIME_COMMIT = "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2"
PINNED_SOURCE_ARCHIVE_SHA256 = "5fe5b3133f7c31f42cc9597059ddb69f31045dbbf3fbfe8bd57236ab0626efe9"
MODEL_NAME = "MiniCPM-V-4.6-Q4_K_M-no-nextn.gguf"
MMPROJ_NAME = "mmproj-MiniCPM-V-4.6-f16.gguf"
IMAGE_NAME = "text_alpha.png"
MODEL_SHA256 = "8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773"
MMPROJ_SHA256 = "ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293"
IMAGE_SHA256 = "cd825c6781189b63af6ed30b75a3d7edb047776c6adec6d6c9a231c72e240ee4"
QUESTION = "Read the single uppercase word in the image. Answer with that word only."
BOARD_BASE = "kv260-vlm-p2-cpu"
MIN_MEM_AVAILABLE_KIB = 2_750_000
# CPU-only inference records CmaFree but does not allocate CMA-backed buffers.
MIN_CMA_FREE_KIB = 0
MIN_HOME_FREE_BYTES = 1 << 30
# Keep below half of four cores; per-process CPU and forbidden-process gates remain.
MAX_LOAD1 = 2.0
MAX_BUSY_CORES_PER_PROCESS = 0.25
TIMEOUT_SECONDS = 300
REMOTE_WATCHDOG_SECONDS = 540
HOST_REMOTE_WAIT_SECONDS = 600
RUN_ID_RE = re.compile(r"[a-z][a-z0-9_-]{7,79}\Z")


# Submitted over noninteractive ssh stdin.  It writes only under the board
# user's ~/kv260-vlm-p2-cpu/runs/RUN_ID and never changes system or PL state.
REMOTE_ONCE = r'''
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ACTIVE_CHILD = None
CHILD_TERMINATION_UNPROVEN = False


def stop_child_group(child):
    if child is None or child.poll() is not None:
        return True
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=8)
        return True
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=5)
            return True
        except subprocess.TimeoutExpired:
            return False


def interrupted(signum, _frame):
    global CHILD_TERMINATION_UNPROVEN
    if not stop_child_group(ACTIVE_CHILD):
        CHILD_TERMINATION_UNPROVEN = True
        raise RuntimeError("remote watchdog signal; child group termination unproven")
    raise InterruptedError("remote watchdog or SSH signal " + str(signum))


for trapped in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
    signal.signal(trapped, interrupted)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fail(message):
    raise RuntimeError(message)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked_artifact(path, expected):
    if not path.is_file():
        fail("missing required file: " + str(path))
    actual = {"path": str(path), "bytes": path.stat().st_size,
              "sha256": sha256_file(path)}
    if expected.get("bytes") is not None and actual["bytes"] != expected["bytes"]:
        fail("byte size mismatch: " + str(path))
    if actual["sha256"] != expected["sha256"]:
        fail("SHA-256 mismatch: " + str(path))
    return actual


def command_record(argv, timeout_seconds=90, cwd=None):
    global ACTIVE_CHILD, CHILD_TERMINATION_UNPROVEN
    started = utc_now()
    process = None
    try:
        process = subprocess.Popen(argv, cwd=cwd, text=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        ACTIVE_CHILD = process
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        return {"argv": [str(x) for x in argv], "started_at_utc": started,
                "returncode": process.returncode, "stdout": stdout,
                "stderr": stderr}
    except subprocess.TimeoutExpired as exc:
        if not stop_child_group(process):
            CHILD_TERMINATION_UNPROVEN = True
            fail("prerequisite child termination unproven")
        stdout, stderr = process.communicate()
        return {"argv": [str(x) for x in argv], "started_at_utc": started,
                "returncode": None, "timed_out": True,
                "stdout": stdout, "stderr": stderr}
    finally:
        ACTIVE_CHILD = None


def require_command(record, label):
    if record["returncode"] != 0:
        fail(label + " failed; see prerequisites.json")


def proc_snapshot():
    seen = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "stat").read_text()
            tail = raw[raw.rfind(")") + 2:].split()
            ticks = int(tail[11]) + int(tail[12])
            name = (entry / "comm").read_text().strip()
            uid_line = next(line for line in (entry / "status").read_text().splitlines()
                            if line.startswith("Uid:"))
            uid = int(uid_line.split()[1])
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").lower()
        except PermissionError:
            fail("cannot inspect process ownership/cmdline for PID " + entry.name)
        except (OSError, ValueError, IndexError, StopIteration):
            continue
        seen[int(entry.name)] = {"ticks": ticks, "comm": name, "uid": uid, "command": command,
                                 "vlm_command_match": any(term in command for term in
                                     ("llama-mtmd", "llama-server", "minicpm", "vllm", "sglang", "ollama"))}
    return seen


def active_load_gate():
    before = proc_snapshot()
    start = time.monotonic()
    time.sleep(2)
    after = proc_snapshot()
    elapsed = time.monotonic() - start
    ticks_per_second = os.sysconf("SC_CLK_TCK")
    busy = []
    owners = []
    forbidden_names = {"llama-mtmd-cli", "llama-server", "llama-cli", "ollama",
                       "vivado", "vitis_hls", "xbutil", "cmake", "ninja",
                       "cc1plus", "cc1", "gcc", "g++", "ld", "lto1",
                       "unattended-upgr"}
    for pid, row in after.items():
        if pid == os.getpid():
            continue
        is_shutdown_waiter = (row["comm"] == "unattended-upgr" and
                              row["command"].split()[-2:] == [
                                  "/usr/share/unattended-upgrades/unattended-upgrade-shutdown",
                                  "--wait-for-signal"])
        if (row["comm"] in forbidden_names and not is_shutdown_waiter) or row["vlm_command_match"]:
            owners.append({"pid": pid, "uid": row["uid"], "comm": row["comm"],
                           "vlm_command_match": row["vlm_command_match"]})
        old = before.get(pid)
        if old is not None:
            cores = (row["ticks"] - old["ticks"]) / ticks_per_second / elapsed
            if cores >= CONFIG["max_busy_cores_per_process"]:
                busy.append({"pid": pid, "uid": row["uid"], "comm": row["comm"],
                             "cores_over_sample": round(cores, 3)})
    load1 = float(Path("/proc/loadavg").read_text().split()[0])
    return {"captured_at_utc": utc_now(), "sample_seconds": round(elapsed, 3),
            "loadavg_1min": load1, "forbidden_processes": owners,
            "busy_processes": busy,
            "thresholds": {"max_loadavg_1min": CONFIG["max_load1"],
                           "max_busy_cores_per_process": CONFIG["max_busy_cores_per_process"]}}


def fresh_memory_gate():
    memory = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        name, value = line.split(":", 1)
        if name in ("MemAvailable", "CmaFree", "SwapTotal", "SwapFree"):
            memory[name] = int(value.strip().split()[0])
    return memory


def owned_cli_processes(base):
    needle = str(base / "build-cpu/bin/llama-mtmd-cli").encode()
    found = []
    unreadable = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes()
            if needle in cmdline:
                found.append(int(entry.name))
        except PermissionError:
            unreadable.append(int(entry.name))
        except OSError:
            continue
    return sorted(found), sorted(unreadable)


base = Path.home() / "kv260-vlm-p2-cpu"
run_root = base / "runs"
run_root.mkdir(parents=True, exist_ok=True)
lock_handle = (run_root / ".cpu_p2_runner.lock").open("a+")
try:
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print(json.dumps({"run_id": CONFIG["run_id"], "status": "REMOTE_LOCK_BUSY",
                      "wrapper_returncode": None}, sort_keys=True))
    sys.exit(2)
run_dir = base / "runs" / CONFIG["run_id"]
run_dir.mkdir(parents=True, exist_ok=False)
result = {"run_id": CONFIG["run_id"], "started_at_utc": utc_now(),
          "scope": "one synthetic original-image CPU-only wiring request; no PL",
          "status": "PREREQUISITE_FAILED", "wrapper_returncode": None,
          "board_run_dir": str(run_dir), "worker_pid": os.getpid(),
          "owner_window": CONFIG["owner_window"]}
prereq = {"expected": CONFIG["expected"],
          "build_attestation_sha256": CONFIG["build_attestation_sha256"],
          "build_attestation": CONFIG["build_attestation"]}
try:
    required_tools = ("sha256sum", "file", "readelf", "ldd", "timeout", "/usr/bin/time")
    missing = [tool for tool in required_tools if not shutil.which(tool)]
    prereq["required_tools_missing"] = missing
    if missing:
        fail("missing prerequisite tools: " + ", ".join(missing))

    source_archive = base / "staging" / CONFIG["source_archive_name"]
    model = base / "input" / CONFIG["model_name"]
    mmproj = base / "input" / CONFIG["mmproj_name"]
    image = base / "input" / CONFIG["image_name"]
    cli = base / "build-cpu/bin/llama-mtmd-cli"
    cache = base / "build-cpu/CMakeCache.txt"
    prereq["source_archive"] = checked_artifact(source_archive, CONFIG["expected"]["source_archive"])
    prereq["model"] = checked_artifact(model, CONFIG["expected"]["model"])
    prereq["mmproj"] = checked_artifact(mmproj, CONFIG["expected"]["mmproj"])
    prereq["image"] = checked_artifact(image, CONFIG["expected"]["image"])

    prereq["source_compare"] = command_record(
        [sys.executable, "-c", CONFIG["source_verifier_source"]], timeout_seconds=120)
    require_command(prereq["source_compare"], "content/type/mode board source verifier")
    source_compare = json.loads(prereq["source_compare"]["stdout"])
    if (source_compare.get("pass") is not True or source_compare.get("uid_gid_ignored") is not True
            or source_compare.get("archive_sha256") != CONFIG["expected"]["source_archive"]["sha256"]
            or source_compare.get("regular_files_checked") != 3617
            or source_compare.get("directories_checked") != 374
            or source_compare.get("symlinks_checked") != 0
            or source_compare.get("differences") or source_compare.get("extra_paths")):
        fail("extracted source differs from pinned archive content/type/mode")
    prereq["source_verifier_sha256"] = CONFIG["source_verifier_sha256"]
    if not cache.is_file():
        fail("missing CMakeCache.txt")
    prereq["cmake_cache_sha256"] = sha256_file(cache)
    if prereq["cmake_cache_sha256"] != CONFIG["build_attestation"]["cmake_cache_sha256"]:
        fail("board CMakeCache SHA differs from successful build attestation")
    cache_text = cache.read_text(errors="replace")
    prereq["cmake_cache_selected"] = [line for line in cache_text.splitlines()
                                      if line.startswith(("CMAKE_BUILD_TYPE:", "GGML_NATIVE:",
                                                          "LLAMA_BUILD_TOOLS:", "LLAMA_BUILD_TESTS:",
                                                          "LLAMA_BUILD_EXAMPLES:"))]
    required_cache = ("CMAKE_BUILD_TYPE:STRING=Release", "GGML_NATIVE:BOOL=OFF",
                      "LLAMA_BUILD_TOOLS:BOOL=ON", "LLAMA_BUILD_TESTS:BOOL=OFF",
                      "LLAMA_BUILD_EXAMPLES:BOOL=OFF")
    if any(line not in cache_text for line in required_cache):
        fail("board build configuration differs from the frozen CPU setup")
    for option in ("GGML_CUDA", "GGML_VULKAN", "GGML_SYCL", "GGML_HIP", "GGML_OPENCL"):
        if option + ":BOOL=ON" in cache_text:
            fail("non-CPU backend enabled in CMakeCache: " + option)
    if not cli.is_file() or not os.access(cli, os.X_OK):
        fail("missing executable board llama-mtmd-cli")
    prereq["cli_sha256"] = sha256_file(cli)
    if prereq["cli_sha256"] != CONFIG["build_attestation"]["cli_sha256"]:
        fail("board CLI SHA differs from successful build attestation")
    attested_libraries = set()
    prereq["local_shared_libraries"] = []
    for item in CONFIG["build_attestation"]["local_shared_libraries"]:
        lib = base / item["path"]
        if not lib.is_file() or not lib.resolve().is_relative_to((base / "build-cpu").resolve()):
            fail("attested local shared library missing or outside board build tree")
        actual = {"path": str(lib), "sha256": sha256_file(lib)}
        if actual["sha256"] != item["sha256"]:
            fail("local shared-library SHA differs from build attestation: " + str(lib))
        prereq["local_shared_libraries"].append(actual)
        attested_libraries.add(str(lib.resolve()))
    prereq["file"] = command_record(["file", "-b", str(cli)], timeout_seconds=10)
    prereq["readelf"] = command_record(["readelf", "-h", str(cli)], timeout_seconds=10)
    prereq["ldd"] = command_record(["ldd", str(cli)], timeout_seconds=20)
    prereq["help"] = command_record([str(cli), "--help"], timeout_seconds=30)
    for label in ("file", "readelf", "ldd", "help"):
        require_command(prereq[label], label)
    if "aarch64" not in prereq["file"]["stdout"].lower() or "aarch64" not in prereq["readelf"]["stdout"].lower():
        fail("binary is not identified as AArch64 by file and readelf")
    if "not found" in prereq["ldd"]["stdout"].lower():
        fail("ldd reports unresolved shared libraries")
    loaded_local = set()
    for line in prereq["ldd"]["stdout"].splitlines():
        match = re.search(r"=>\s+(/\S+)", line) or re.match(r"\s*(/\S+)", line)
        if match:
            resolved = Path(match.group(1)).resolve()
            if resolved.is_relative_to(base.resolve()):
                loaded_local.add(str(resolved))
    prereq["ldd_local_shared_libraries"] = sorted(loaded_local)
    if not loaded_local or not loaded_local.issubset(attested_libraries):
        fail("ldd uses an unattested local shared library or no local library")
    result["memory_just_before"] = fresh_memory_gate()
    result["active_load_just_before"] = active_load_gate()
    result["jupyter_just_before"] = command_record(
        ["systemctl", "is-active", "jupyter.service"], timeout_seconds=10)
    save_json(run_dir / "just_before.json", {"memory_kib": result["memory_just_before"],
                                               "active_load": result["active_load_just_before"]})
    if result["memory_just_before"].get("MemAvailable", 0) < CONFIG["min_mem_available_kib"]:
        fail("MemAvailable below fixed single-request floor")
    if result["memory_just_before"].get("CmaFree", 0) < CONFIG["min_cma_free_kib"]:
        fail("CmaFree below fixed no-disruption floor")
    if result["memory_just_before"].get("SwapTotal") != 0:
        fail("swap configuration changed from the frozen no-swap baseline")
    if result["jupyter_just_before"]["returncode"] != 0 or result["jupyter_just_before"]["stdout"].strip() != "active":
        fail("existing Jupyter service state changed")
    load = result["active_load_just_before"]
    if load["forbidden_processes"] or load["busy_processes"] or load["loadavg_1min"] > CONFIG["max_load1"]:
        fail("board is not in an exclusive low-load CPU window")

    argv = ["timeout", "--verbose", "--signal=TERM", "--kill-after=10s",
            str(CONFIG["timeout_seconds"]) + "s", "/usr/bin/time", "-v", "-o",
            str(run_dir / "resource.txt"), str(cli), "-m", str(model),
            "--mmproj", str(mmproj), "--image", str(image), "-p", CONFIG["question"],
            "-t", "2", "-tb", "2", "-c", "4096", "-n", "8", "--seed", "42",
            "--temp", "0", "--top-p", "1", "--top-k", "0", "--device", "none",
            "-ngl", "0", "--no-mmproj-offload", "--no-warmup", "--perf"]
    save_json(run_dir / "command.json", {"argv": argv, "cwd": str(base),
                                          "mtmd_test_response_marker_unset": True,
                                          "measurement_boundary": "whole CLI process including model load; timeout wraps /usr/bin/time which directly wraps CLI"})
    result["inference_started_at_utc"] = utc_now()
    start = time.monotonic()
    wrapper = None
    with (run_dir / "stdout.log").open("wb") as stdout, (run_dir / "stderr.log").open("wb") as stderr:
        try:
            wrapper_env = os.environ.copy()
            wrapper_env["LC_ALL"] = "C"
            wrapper_env.pop("MTMD_TEST_RESPONSE_MARKER", None)
            wrapper = subprocess.Popen(argv, cwd=base, stdout=stdout, stderr=stderr,
                                       env=wrapper_env, start_new_session=True)
            ACTIVE_CHILD = wrapper
            result["wrapper_returncode"] = wrapper.wait(timeout=330)
        except subprocess.TimeoutExpired:
            if not stop_child_group(wrapper):
                CHILD_TERMINATION_UNPROVEN = True
                fail("CLI wrapper termination after 330 seconds unproven")
            fail("CLI wrapper exceeded its 300-second limit and cleanup interval")
        finally:
            ACTIVE_CHILD = None
    result["process_wall_seconds_including_model_load"] = round(time.monotonic() - start, 3)
    result["inference_ended_at_utc"] = utc_now()
    resource = run_dir / "resource.txt"
    if resource.is_file():
        resource_text = resource.read_text(errors="replace")
        rss_match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", resource_text)
        exit_match = re.search(r"Exit status:\s*(\d+)", resource_text)
        result["resource_observed_rss_kib"] = int(rss_match.group(1)) if rss_match else None
        result["time_child_exit_status"] = int(exit_match.group(1)) if exit_match else None
    else:
        result["resource_observed_rss_kib"] = None
        result["time_child_exit_status"] = None
    result["process_peak_rss_kib"] = (result["resource_observed_rss_kib"]
                                      if result["wrapper_returncode"] == 0 and result["time_child_exit_status"] == 0
                                      else None)
    result["resource_scope"] = ("complete_success" if result["process_peak_rss_kib"] is not None
                                else "failed_or_interrupted_partial_observation_only")
    timeout_stderr = (run_dir / "stderr.log").read_text(errors="replace")
    result["timeout_signal_logged"] = "timeout: sending signal" in timeout_stderr
    result["wrapper_status_interpretation"] = (
        "success" if result["wrapper_returncode"] == 0 else
        "timeout_signal_logged" if result["wrapper_returncode"] == 124 and result["timeout_signal_logged"] else
        "exit_124_ambiguous_cli_or_timeout" if result["wrapper_returncode"] == 124 else
        "nonzero_wrapper_or_cli")
    lines = [line.strip() for line in (run_dir / "stdout.log").read_text(errors="replace").splitlines()
             if line.strip()]
    result["observed_last_nonempty_stdout_line"] = lines[-1] if lines else ""
    result["expected_word_match"] = result["observed_last_nonempty_stdout_line"] == CONFIG["expected_word"]
    result["status"] = ("SYNTHETIC_WIRING_PASS" if result["wrapper_returncode"] == 0 and
                        result["time_child_exit_status"] == 0 and
                        result["expected_word_match"] else "SYNTHETIC_WIRING_FAIL")
except Exception as exc:
    result["failure"] = repr(exc)
finally:
    try:
        if not stop_child_group(ACTIVE_CHILD):
            CHILD_TERMINATION_UNPROVEN = True
        (result["owned_cli_processes_at_finish"],
         result["unreadable_processes_at_finish"]) = owned_cli_processes(base)
        result["remote_process_cleanup_verified"] = (
            not CHILD_TERMINATION_UNPROVEN and not result["owned_cli_processes_at_finish"]
            and not result["unreadable_processes_at_finish"])
        if not result["remote_process_cleanup_verified"]:
            result["status"] = "REMOTE_CHILD_STATE_UNKNOWN"
        save_json(run_dir / "prerequisites.json", prereq)
        result["ended_at_utc"] = utc_now()
        save_json(run_dir / "result.json", result)
        if result["remote_process_cleanup_verified"]:
            save_json(run_dir / "completion.json", {
                "kind": "kv260_cpu_p2_single_completion_v1", "run_id": CONFIG["run_id"],
                "worker_pid": os.getpid(), "completed_at_utc": utc_now(),
                "result_sha256": sha256_file(run_dir / "result.json")})
        print(json.dumps(result, sort_keys=True))
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()
sys.exit(0 if result["status"] == "SYNTHETIC_WIRING_PASS" else 1)
'''


REMOTE_STATUS = r'''
import fcntl
import hashlib
import json
import os
from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


base = Path.home() / "kv260-vlm-p2-cpu"
run_dir = base / "runs" / RUN_ID
status = {"run_id": RUN_ID, "state": "REMOTE_STATE_UNKNOWN", "run_dir_exists": run_dir.exists()}
lock_path = base / "runs/.cpu_p2_runner.lock"
if lock_path.is_file():
    with lock_path.open("rb") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            status["runner_lock_free"] = True
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        except BlockingIOError:
            status["runner_lock_free"] = False
else:
    status["runner_lock_free"] = False

needle = str(base / "build-cpu/bin/llama-mtmd-cli").encode()
owned = []
unreadable = []
for entry in Path("/proc").iterdir():
    if not entry.name.isdigit() or int(entry.name) == os.getpid():
        continue
    try:
        if needle in (entry / "cmdline").read_bytes():
            owned.append(int(entry.name))
    except PermissionError:
        unreadable.append(int(entry.name))
    except OSError:
        continue
status["board_cli_processes"] = sorted(owned)
status["unreadable_processes"] = sorted(unreadable)

result_path = run_dir / "result.json"
completion_path = run_dir / "completion.json"
if result_path.is_file() and completion_path.is_file():
    try:
        completion = json.loads(completion_path.read_text())
        result = json.loads(result_path.read_text())
        status["completion_marker_valid"] = (
            completion.get("kind") == "kv260_cpu_p2_single_completion_v1" and
            completion.get("run_id") == RUN_ID and result.get("run_id") == RUN_ID and
            completion.get("result_sha256") == sha256_file(result_path) and
            result.get("remote_process_cleanup_verified") is True)
        status["result_status"] = result.get("status")
    except (OSError, ValueError):
        status["completion_marker_valid"] = False
else:
    status["completion_marker_valid"] = False

if (status["completion_marker_valid"] and status["runner_lock_free"] and
        not status["board_cli_processes"] and not status["unreadable_processes"]):
    manifest = {}
    for path in sorted(run_dir.rglob("*")):
        if path.is_symlink():
            status["state"] = "REMOTE_STATE_UNKNOWN_SYMLINK"
            break
        if path.is_file():
            manifest[str(path.relative_to(run_dir))] = {
                "bytes": path.stat().st_size, "sha256": sha256_file(path)}
    else:
        status["state"] = "COMPLETE"
        status["raw_manifest"] = manifest
print(json.dumps(status, sort_keys=True))
'''


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def raw_path(value: str) -> Path:
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(RAW_PARENT.resolve())
    except ValueError as exc:
        raise ValueError("build evidence path is outside experiments/raw") from exc
    return candidate


def load_build_attestation(path: Path) -> tuple[dict, dict]:
    if not path.is_file():
        raise ValueError(f"completed build attestation missing: {path}")
    attestation = json.loads(path.read_text(encoding="utf-8"))
    if attestation.get("schema") != "kv260_cpu_p2_build_attestation_v1":
        raise ValueError("unsupported board build attestation schema")
    if attestation.get("runtime_commit") != PINNED_RUNTIME_COMMIT:
        raise ValueError("build attestation runtime commit changed")
    if attestation.get("source_archive_sha256") != PINNED_SOURCE_ARCHIVE_SHA256:
        raise ValueError("build attestation source archive changed")
    attempt_path = raw_path(attestation["build_attempt_record_path"])
    if sha256_file(attempt_path) != attestation["build_attempt_record_sha256"]:
        raise ValueError("build attempt record SHA mismatch")
    attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    if (attempt.get("record") != "build_attempt" or attempt.get("board") != "KV260"
            or attempt.get("target") != "llama-mtmd-cli"
            or attempt.get("exit_code") != 0
            or attempt.get("status") != "BUILD_TARGET_COMPLETED"
            or attempt.get("source_archive_sha256") != PINNED_SOURCE_ARCHIVE_SHA256):
        raise ValueError("no recorded successful pinned llama-mtmd-cli build")
    if "cmake --build build-cpu --target llama-mtmd-cli" not in attempt.get("command", ""):
        raise ValueError("build command did not target the staged CLI")
    for label, record_key in (("build_log", "build_log_sha256"),
                              ("configure_log", "configure_log_sha256")):
        artifact = raw_path(attestation[label + "_path"])
        if sha256_file(artifact) != attempt[record_key]:
            raise ValueError(label + " SHA mismatch against successful build record")
    if "Linking CXX executable bin/llama-mtmd-cli" not in raw_path(
            attestation["build_log_path"]).read_text(encoding="utf-8"):
        raise ValueError("successful build log lacks CLI link line")
    if attestation.get("build_exit_code") != 0:
        raise ValueError("build attestation does not record exit 0")
    captured_at = datetime.fromisoformat(attestation["captured_at_utc"].replace("Z", "+00:00"))
    recorded_at = datetime.fromisoformat(attempt["recorded_at_utc"].replace("Z", "+00:00"))
    if captured_at.tzinfo is None or recorded_at.tzinfo is None or captured_at < recorded_at:
        raise ValueError("build artifact capture predates completed build record")
    expected_cache = attestation.get("cmake_cache_sha256", "")
    expected_cli = attestation.get("cli_sha256", "")
    libraries = attestation.get("local_shared_libraries")
    for value in (expected_cache, expected_cli):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("build attestation has invalid artifact SHA")
    if not isinstance(libraries, list) or not libraries:
        raise ValueError("build attestation lacks local shared-library hashes")
    paths = set()
    for item in libraries:
        relative = Path(item["path"])
        if (relative.is_absolute() or ".." in relative.parts or
                relative.parts[:1] != ("build-cpu",) or
                not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])):
            raise ValueError("invalid local shared-library entry")
        paths.add(str(relative))
    if len(paths) != len(libraries):
        raise ValueError("duplicate local shared-library path")
    evidence_hashes = attestation.get("raw_evidence_sha256")
    if not isinstance(evidence_hashes, dict) or not evidence_hashes:
        raise ValueError("build attestation lacks board raw-evidence hashes")
    for relative, expected_sha in evidence_hashes.items():
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            raise ValueError("invalid build raw-evidence SHA")
        if sha256_file(raw_path(relative)) != expected_sha:
            raise ValueError("build raw-evidence SHA mismatch: " + relative)
    return attestation, attempt


def load_frozen_config(run_id: str) -> dict:
    model_manifest = json.loads(MODEL_MANIFEST.read_text(encoding="utf-8"))
    smoke_manifest = json.loads(SMOKE_MANIFEST.read_text(encoding="utf-8"))
    if model_manifest["llama_cpp_commit"] != PINNED_RUNTIME_COMMIT:
        raise ValueError("model manifest runtime commit changed")
    if smoke_manifest["kind"] != "synthetic_wiring_fixtures_not_quality_data":
        raise ValueError("smoke manifest kind changed")
    if model_manifest["quantization_format"] != "Q4_K_M" or smoke_manifest["question"] != QUESTION:
        raise ValueError("frozen quantization or smoke question changed")
    artifacts = {Path(item["path"]).name: item for item in model_manifest["artifacts"]}
    fixtures = {item["path"]: item for item in smoke_manifest["fixtures"]}
    model = artifacts[MODEL_NAME]
    mmproj = artifacts[MMPROJ_NAME]
    image = fixtures[IMAGE_NAME]
    if image["expected_visible_word"] != "ALPHA":
        raise ValueError("alpha smoke fixture changed")
    if (model["sha256"], model["bytes"]) != (MODEL_SHA256, 529_101_632):
        raise ValueError("frozen Q4 model identity changed")
    if (mmproj["sha256"], mmproj["bytes"]) != (MMPROJ_SHA256, 1_108_747_008):
        raise ValueError("frozen mmproj identity changed")
    if image["sha256"] != IMAGE_SHA256:
        raise ValueError("frozen alpha image identity changed")
    return {
        "run_id": run_id,
        "model_name": MODEL_NAME, "mmproj_name": MMPROJ_NAME, "image_name": IMAGE_NAME,
        "source_archive_name": "llama_cpp_7ab4ee7_source.tar.gz",
        "question": smoke_manifest["question"], "expected_word": "ALPHA",
        "expected": {
            "source_archive": {"sha256": PINNED_SOURCE_ARCHIVE_SHA256},
            "model": {"bytes": model["bytes"], "sha256": model["sha256"]},
            "mmproj": {"bytes": mmproj["bytes"], "sha256": mmproj["sha256"]},
            "image": {"sha256": image["sha256"]},
        },
        "min_mem_available_kib": MIN_MEM_AVAILABLE_KIB,
        "min_cma_free_kib": MIN_CMA_FREE_KIB,
        "max_load1": MAX_LOAD1,
        "max_busy_cores_per_process": MAX_BUSY_CORES_PER_PROCESS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "manifest_sha256": {"model": sha256_file(MODEL_MANIFEST),
                            "smoke": sha256_file(SMOKE_MANIFEST)},
    }


def ssh_python(source: str, out: Path, timeout_seconds: int,
               remote_command: str = "python3 -") -> subprocess.CompletedProcess[str]:
    command = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
               "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3",
               "kria", remote_command]
    started = datetime.now(timezone.utc).isoformat()
    try:
        completed = subprocess.run(command, input=source, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   check=False, timeout=timeout_seconds)
        record = {"argv": command, "started_at_utc": started,
                  "returncode": completed.returncode, "timed_out": False}
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        completed = subprocess.CompletedProcess(command, 124, stdout, stderr)
        record = {"argv": command, "started_at_utc": started,
                  "returncode": 124, "timed_out": True}
    out.with_suffix(".stdout").write_text(completed.stdout, encoding="utf-8")
    out.with_suffix(".stderr").write_text(completed.stderr, encoding="utf-8")
    out.with_suffix(".transport.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return completed


def preflight_gate(snapshot: dict) -> None:
    if snapshot.get("arch", "").lower() != "aarch64" or snapshot.get("cpu_count") != 4:
        raise ValueError("board identity is not the expected 4-core AArch64")
    memory = snapshot.get("memory_kib", {})
    if memory.get("MemAvailable", 0) < MIN_MEM_AVAILABLE_KIB:
        raise ValueError("MemAvailable below fixed floor")
    if memory.get("CmaFree", 0) < MIN_CMA_FREE_KIB:
        raise ValueError("CmaFree below fixed floor")
    if memory.get("SwapTotal") != 0 or memory.get("SwapFree") != 0:
        raise ValueError("swap configuration changed")
    if snapshot.get("home_free_bytes", 0) < MIN_HOME_FREE_BYTES:
        raise ValueError("board user home free disk below 1 GiB")
    if snapshot.get("jupyter_active") != "active":
        raise ValueError("existing Jupyter service state changed")
    processes = snapshot.get("selected_processes")
    if not isinstance(processes, list):
        raise ValueError("read-only preflight omitted selected process details")
    forbidden = {"llama-mtmd-cli", "llama-server", "vivado", "vitis_hls", "xbutil",
                 "cmake", "ninja", "cc1plus", "cc1", "apt", "apt-get", "dpkg", "dpkg-deb"}
    active = []
    for row in processes:
        if not isinstance(row, dict) or not isinstance(row.get("comm"), str):
            raise ValueError("read-only preflight returned malformed process details")
        comm = row["comm"]
        if comm == "unattended-upgr" and row.get("role") == "shutdown_waiter":
            continue
        if comm in forbidden or comm == "unattended-upgr":
            active.append({"pid": row.get("pid"), "comm": comm,
                           "role": row.get("role", "unknown")})
    if active:
        raise ValueError("board has active VLM/build/package-transaction processes: " + repr(active))
    packagekit = snapshot.get("packagekit_transaction_state")
    if (not isinstance(packagekit, dict) or
            packagekit.get("state") not in ("SERVICE_INACTIVE", "NO_ACTIVE_TRANSACTIONS") or
            packagekit.get("timed_out") is not False):
        raise ValueError("PackageKit transaction state is active or unknown")
    load1 = float(snapshot["loadavg"].split()[0])
    if load1 > MAX_LOAD1:
        raise ValueError(f"board 1-minute load {load1} exceeds {MAX_LOAD1}")
    if not snapshot.get("tools_present", {}).get("timeout") or not snapshot.get("tools_present", {}).get("/usr/bin/time"):
        raise ValueError("timeout or /usr/bin/time unavailable")


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="unique lowercase append-only run ID")
    parser.add_argument("--execute", action="store_true", help="perform one board CPU request after all gates")
    parser.add_argument("--owner-window-confirmed", action="store_true",
                        help="affirm the board owner has a short exclusive CPU-only P2 window")
    parser.add_argument("--owner-window-ref", default=None,
                        help="optional owner reservation or coordination reference saved in raw record")
    parser.add_argument("--build-attestation", type=Path, default=BUILD_ATTESTATION,
                        help="versioned successful-build attestation under experiments/raw")
    args = parser.parse_args()
    attestation_path = args.build_attestation.resolve()
    try:
        attestation_path.relative_to(RAW_PARENT.resolve())
    except ValueError:
        parser.error("build attestation must be under experiments/raw")
    run_id = args.run_id or ("kv260_cpu_p2_alpha_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                              + "_" + uuid.uuid4().hex[:8])
    if not RUN_ID_RE.fullmatch(run_id):
        parser.error("run ID must be 8-80 lowercase letters, digits, underscores or hyphens, starting with a letter")
    if args.execute and not args.owner_window_confirmed:
        parser.error("--execute requires --owner-window-confirmed")
    config = load_frozen_config(run_id)
    config["owner_window"] = {
        "confirmed": bool(args.owner_window_confirmed),
        "operator_login": getpass.getuser(),
        "confirmed_at_utc": datetime.now(timezone.utc).isoformat() if args.owner_window_confirmed else None,
        "coordination_reference": args.owner_window_ref,
    }
    local_dir = RAW_PARENT / run_id
    board_dir = f"~/kv260-vlm-p2-cpu/runs/{run_id}"
    plan = {
        "run_id": run_id, "mode": "execute" if args.execute else "dry_plan_only",
        "local_raw_dir": str(local_dir), "board_raw_dir": board_dir,
        "board_ssh": "ssh -T -o BatchMode=yes kria",
        "build_attestation_path": str(attestation_path),
        "build_attestation_present": attestation_path.is_file(),
        "runtime_commit": PINNED_RUNTIME_COMMIT,
        "source_archive_sha256": PINNED_SOURCE_ARCHIVE_SHA256,
        "source_verifier_sha256": sha256_file(SOURCE_VERIFIER),
        "model_manifest_sha256": config["manifest_sha256"]["model"],
        "smoke_manifest_sha256": config["manifest_sha256"]["smoke"],
        "input_sha256": config["expected"],
        "cli_flags": ["-t 2", "-tb 2", "-c 4096", "-n 8", "--seed 42",
                      "--temp 0", "--top-p 1", "--top-k 0", "--device none",
                      "-ngl 0", "--no-mmproj-offload", "--no-warmup", "--perf"],
        "gates": {"min_mem_available_kib": MIN_MEM_AVAILABLE_KIB,
                  "min_cma_free_kib": MIN_CMA_FREE_KIB,
                  "min_home_free_bytes": MIN_HOME_FREE_BYTES,
                  "max_loadavg_1min": MAX_LOAD1,
                  "max_busy_cores_per_process": MAX_BUSY_CORES_PER_PROCESS,
                  "no_swap": True, "jupyter_must_remain_active": True,
                  "no_other_vlm_build_or_system_update": True,
                  "owner_window_confirmed": bool(args.owner_window_confirmed)},
        "owner_window": config["owner_window"],
        "remote_watchdog_seconds": REMOTE_WATCHDOG_SECONDS,
        "measurement": "one whole CLI process; 300 s timeout outside /usr/bin/time directly around CLI",
        "result_scope": "synthetic functional wiring only, no quality or PL claim",
    }
    if not args.execute:
        print(json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    # Atomic local creation and atomic remote creation prevent accidental reruns.
    local_dir.mkdir(parents=True, exist_ok=False)
    write_json(local_dir / "plan.json", plan)
    write_json(local_dir / "runner_provenance.json", {
        "runner_sha256": sha256_file(Path(__file__)),
        "preflight_source_sha256": sha256_file(PREFLIGHT_SOURCE),
        "source_verifier_sha256": sha256_file(SOURCE_VERIFIER),
        "model_manifest_sha256": config["manifest_sha256"]["model"],
        "smoke_manifest_sha256": config["manifest_sha256"]["smoke"],
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    outcome = {"run_id": run_id, "status": "PRECHECK_FAILED", "board_inference_attempted": False,
               "board_raw_dir": board_dir, "local_raw_dir": str(local_dir)}
    remote_attempted = False
    try:
        attestation, successful_attempt = load_build_attestation(attestation_path)
        config["build_attestation"] = attestation
        config["build_attestation_sha256"] = sha256_file(attestation_path)
        verifier_bytes = SOURCE_VERIFIER.read_bytes()
        config["source_verifier_source"] = verifier_bytes.decode("utf-8")
        config["source_verifier_sha256"] = hashlib.sha256(verifier_bytes).hexdigest()
        write_json(local_dir / "build_attestation_snapshot.json", attestation)
        write_json(local_dir / "successful_build_attempt_snapshot.json", successful_attempt)
        (local_dir / "source_verifier_snapshot.py").write_text(
            config["source_verifier_source"], encoding="utf-8")
        before = ssh_python(PREFLIGHT_SOURCE.read_text(encoding="utf-8"),
                            local_dir / "preflight_before", 30)
        if before.returncode != 0:
            raise RuntimeError("read-only board preflight before failed")
        snapshot = json.loads(before.stdout)
        write_json(local_dir / "preflight_before.json", snapshot)
        preflight_gate(snapshot)
        source = "CONFIG = " + repr(config) + "\n" + REMOTE_ONCE
        remote_attempted = True
        completed = ssh_python(
            source, local_dir / "remote_once", HOST_REMOTE_WAIT_SECONDS,
            remote_command=("timeout --verbose --signal=TERM --kill-after=15s "
                            + str(REMOTE_WATCHDOG_SECONDS) + "s python3 -"))
        outcome["board_inference_attempted"] = None  # unresolved until remote result is parsed
        outcome["remote_transport_returncode"] = completed.returncode
        outcome["remote_transport_timed_out"] = json.loads(
            (local_dir / "remote_once.transport.json").read_text(encoding="utf-8"))["timed_out"]
        try:
            outcome["remote_result"] = json.loads(completed.stdout.splitlines()[-1])
            outcome["board_inference_attempted"] = "inference_started_at_utc" in outcome["remote_result"]
        except (ValueError, IndexError):
            outcome["remote_result_parse_failed"] = True
        outcome["status"] = ("SYNTHETIC_WIRING_PASS" if completed.returncode == 0 and
                             outcome.get("remote_result", {}).get("status") == "SYNTHETIC_WIRING_PASS"
                             else "REMOTE_RUN_FAILED")
    except Exception as exc:
        outcome["failure"] = repr(exc)
    finally:
        if remote_attempted:
            remote_state = None
            try:
                status_source = "RUN_ID = " + repr(run_id) + "\n" + REMOTE_STATUS
                status_result = ssh_python(status_source, local_dir / "remote_status", 45)
                if status_result.returncode == 0:
                    remote_state = json.loads(status_result.stdout)
                    write_json(local_dir / "remote_status.json", remote_state)
                    outcome["remote_state"] = remote_state["state"]
                else:
                    outcome["remote_status_probe_failed"] = True
            except Exception as exc:
                outcome["remote_status_probe_error"] = repr(exc)
            try:
                after = ssh_python(PREFLIGHT_SOURCE.read_text(encoding="utf-8"),
                                   local_dir / "preflight_after", 30)
                if after.returncode == 0:
                    after_snapshot = json.loads(after.stdout)
                    write_json(local_dir / "preflight_after.json", after_snapshot)
                    if (after_snapshot.get("jupyter_active") != "active" or
                            after_snapshot.get("memory_kib", {}).get("SwapTotal") != 0 or
                            after_snapshot.get("memory_kib", {}).get("SwapFree") != 0):
                        outcome["post_board_service_or_swap_changed"] = True
                        outcome["status"] = "EVIDENCE_INCOMPLETE"
                else:
                    outcome["post_preflight_failed"] = True
                    outcome["status"] = "EVIDENCE_INCOMPLETE"
            except Exception as exc:
                outcome["post_preflight_error"] = repr(exc)
                outcome["status"] = "EVIDENCE_INCOMPLETE"
            if remote_state is None or remote_state.get("state") != "COMPLETE":
                outcome["status"] = "REMOTE_STATE_UNKNOWN_NO_COMPLETE_COPY"
                outcome["raw_copy_skipped"] = "remote completion marker, free runner lock, and no CLI process were not jointly proven"
            else:
                board_copy = local_dir / "board_complete_snapshot"
                board_copy.mkdir()
                rsync_cmd = ["rsync", "-a", "-e", "ssh -T -o BatchMode=yes -o ConnectTimeout=10", "--",
                             f"kria:{BOARD_BASE}/runs/{run_id}/", str(board_copy) + "/"]
                try:
                    copied = subprocess.run(rsync_cmd, text=True, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, check=False, timeout=90)
                    outcome["raw_copy_returncode"] = copied.returncode
                    (local_dir / "raw_copy.stdout").write_text(copied.stdout, encoding="utf-8")
                    (local_dir / "raw_copy.stderr").write_text(copied.stderr, encoding="utf-8")
                    if copied.returncode != 0:
                        outcome["status"] = "EVIDENCE_COPY_INCOMPLETE"
                    else:
                        copied_manifest = {}
                        for path in sorted(board_copy.rglob("*")):
                            if path.is_symlink():
                                raise RuntimeError("copied raw evidence contains a symlink")
                            if path.is_file():
                                copied_manifest[str(path.relative_to(board_copy))] = {
                                    "bytes": path.stat().st_size, "sha256": sha256_file(path)}
                        write_json(local_dir / "raw_copy_manifest.json", copied_manifest)
                        if copied_manifest != remote_state["raw_manifest"]:
                            outcome["status"] = "EVIDENCE_COPY_INCOMPLETE"
                            outcome["raw_copy_manifest_mismatch"] = True
                except (subprocess.TimeoutExpired, RuntimeError, OSError) as exc:
                    outcome["raw_copy_error"] = repr(exc)
                    outcome["status"] = "EVIDENCE_COPY_INCOMPLETE"
        outcome["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(local_dir / "run.json", outcome)
    print(json.dumps(outcome, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if outcome["status"] == "SYNTHETIC_WIRING_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
