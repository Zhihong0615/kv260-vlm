#!/usr/bin/env python3
"""Read-only KV260 CPU-baseline resource snapshot; run through batch SSH stdin."""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SYSTEMD_UNITS = ("jupyter.service", "apt-daily.service", "apt-daily-upgrade.service",
                "packagekit.service")
PROCESS_CPU_SAMPLE_SECONDS = 2.0
TIMEOUT_EXECUTABLE_PATH = "/usr/bin/timeout"
SELECTED_PROCESS_NAMES = {"llama-mtmd-cli", "llama-server", "vivado", "vitis_hls", "xbutil", "python3",
                         "cmake", "ninja", "cc1plus", "cc1", "unattended-upgr", "apt", "apt-get",
                         "dpkg", "dpkg-deb", "packagekitd", "rsync"}


def timeout_executable_identity() -> dict:
    identity = {"path": TIMEOUT_EXECUTABLE_PATH, "resolved_path": None,
                "sha256": None, "usable": False}
    path = Path(TIMEOUT_EXECUTABLE_PATH)
    try:
        identity["resolved_path"] = str(path.resolve(strict=True))
        if not path.is_file() or not os.access(path, os.X_OK):
            return identity
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                digest.update(block)
        identity["sha256"] = digest.hexdigest()
        identity["usable"] = True
    except (OSError, RuntimeError):
        pass
    return identity


def systemd_state(unit: str, run=subprocess.run) -> dict:
    """Return an explicit bounded state; failures are represented as UNKNOWN."""
    try:
        result = run(["systemctl", "is-active", unit], capture_output=True,
                     text=True, check=False, timeout=5)
        return {"active_state": result.stdout.strip() or "UNKNOWN",
                "returncode": result.returncode, "timed_out": False}
    except subprocess.TimeoutExpired:
        return {"active_state": "UNKNOWN", "returncode": None, "timed_out": True}
    except OSError as exc:
        return {"active_state": "UNKNOWN", "returncode": None, "timed_out": False,
                "error": type(exc).__name__}


def collect_systemd_states(run=subprocess.run) -> dict:
    return {unit: systemd_state(unit, run) for unit in SYSTEMD_UNITS}


def packagekit_transaction_state(services: dict, run=subprocess.run) -> dict:
    """Query active PackageKit transactions without starting an inactive daemon."""
    service = services.get("packagekit.service", {})
    active = service.get("active_state")
    if active == "inactive" and service.get("returncode") == 3 and service.get("timed_out") is False:
        return {"state": "SERVICE_INACTIVE", "transaction_ids": [],
                "returncode": None, "timed_out": False}
    if active != "active" or service.get("returncode") != 0 or service.get("timed_out") is not False:
        return {"state": "UNKNOWN", "transaction_ids": [],
                "returncode": None, "timed_out": False}
    try:
        result = run(["busctl", "--system", "call", "org.freedesktop.PackageKit",
                      "/org/freedesktop/PackageKit", "org.freedesktop.PackageKit",
                      "GetTransactionList"], capture_output=True, text=True,
                     check=False, timeout=10)
    except subprocess.TimeoutExpired:
        return {"state": "UNKNOWN", "transaction_ids": [],
                "returncode": None, "timed_out": True}
    except OSError as exc:
        return {"state": "UNKNOWN", "transaction_ids": [],
                "returncode": None, "timed_out": False,
                "error": type(exc).__name__}
    words = result.stdout.split()
    if result.returncode != 0 or len(words) < 2 or words[0] != "ao":
        return {"state": "UNKNOWN", "transaction_ids": [],
                "returncode": result.returncode, "timed_out": False}
    try:
        count = int(words[1])
    except ValueError:
        count = -1
    if count < 0 or len(words) != count + 2:
        return {"state": "UNKNOWN", "transaction_ids": [],
                "returncode": result.returncode, "timed_out": False}
    transactions = words[2:]
    return {"state": "NO_ACTIVE_TRANSACTIONS" if not transactions else "ACTIVE_TRANSACTIONS",
            "transaction_ids": transactions, "returncode": result.returncode,
            "timed_out": False}


def process_role(entry: Path, name: str) -> str:
    """Distinguish the idle shutdown waiter from an active unattended upgrade."""
    if name != "unattended-upgr":
        return "process"
    try:
        args = (entry / "cmdline").read_bytes().split(b"\0")
        args = [arg.decode(errors="replace") for arg in args if arg]
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return "unclassified_unattended_upgrade"
    if len(args) >= 2 and args[-2:] == [
            "/usr/share/unattended-upgrades/unattended-upgrade-shutdown", "--wait-for-signal"]:
        return "shutdown_waiter"
    return "unattended_upgrade"


def process_cpu_snapshot() -> tuple[dict[int, dict], list[str]]:
    """Read every process identity and CPU counter fail-closed."""
    rows = {}
    errors = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            stat_read_started = time.monotonic()
            raw_stat = (entry / "stat").read_text()
            stat_read_ended = time.monotonic()
            close = raw_stat.rfind(")")
            if close < 0:
                raise ValueError("malformed stat command")
            fields = raw_stat[close + 2:].split()
            if len(fields) < 20:
                raise ValueError("short stat record")
            name = (entry / "comm").read_text().strip()
            if not name:
                raise ValueError("empty process name")
            uid = None
            role = "process"
            if name in SELECTED_PROCESS_NAMES:
                status = (entry / "status").read_text().splitlines()
                uid_line = next(line for line in status if line.startswith("Uid:"))
                uid = int(uid_line.split()[1])
                role = process_role(entry, name)
            rows[pid] = {"pid": pid, "uid": uid, "comm": name, "role": role,
                         "cpu_ticks": int(fields[11]) + int(fields[12]),
                         "starttime_ticks": int(fields[19]),
                         "stat_read_started": stat_read_started,
                         "stat_read_ended": stat_read_ended}
        except (OSError, StopIteration, ValueError, IndexError) as exc:
            errors.append(f"pid:{pid}:{type(exc).__name__}")
    return rows, errors


def sample_process_cpu() -> tuple[list[dict], list[dict], float, str, list[str]]:
    """Take two fixed-interval process samples and report per-process core use."""
    started = time.monotonic()
    before, before_errors = process_cpu_snapshot()
    time.sleep(PROCESS_CPU_SAMPLE_SECONDS)
    after, after_errors = process_cpu_snapshot()
    elapsed = time.monotonic() - started
    errors = before_errors + after_errors
    rows = []
    selected_rows = []
    state = "OK"
    if errors or set(before) != set(after) or elapsed <= 0:
        state = "PROCESS_STATE_UNKNOWN"
        errors.append("sample_identity_or_interval_mismatch")
    try:
        ticks_per_second = int(os.sysconf("SC_CLK_TCK"))
        if ticks_per_second <= 0:
            raise ValueError("invalid clock tick rate")
    except (OSError, ValueError, TypeError) as exc:
        ticks_per_second = 0
        state = "PROCESS_STATE_UNKNOWN"
        errors.append(f"clock_tick_rate:{type(exc).__name__}")
    for pid in sorted(set(before) & set(after)):
        old, new = before[pid], after[pid]
        if ((old["comm"], old["uid"], old["starttime_ticks"]) !=
                (new["comm"], new["uid"], new["starttime_ticks"])):
            state = "PROCESS_STATE_UNKNOWN"
            errors.append(f"pid:{pid}:identity_changed")
            continue
        delta_ticks = new["cpu_ticks"] - old["cpu_ticks"]
        # The gap from the end of the first stat read to the start of the
        # second is a lower bound on the counter-to-counter interval. Using it
        # avoids understating CPU use when /proc traversal time differs by PID.
        process_interval = new["stat_read_started"] - old["stat_read_ended"]
        if delta_ticks < 0 or ticks_per_second <= 0 or process_interval <= 0:
            state = "PROCESS_STATE_UNKNOWN"
            errors.append(f"pid:{pid}:invalid_cpu_delta")
            continue
        cpu_row = {"pid": pid, "comm": new["comm"], "cpu_ticks_delta": delta_ticks,
                   "cpu_sample_interval_seconds": process_interval,
                   "cpu_cores": delta_ticks / ticks_per_second / process_interval}
        rows.append(cpu_row)
        if new["comm"] in SELECTED_PROCESS_NAMES:
            selected_rows.append({**cpu_row, "uid": new["uid"], "role": new["role"]})
    return rows, selected_rows, elapsed, state, errors


def main() -> None:
    memory = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in {"MemTotal", "MemAvailable", "CmaTotal", "CmaFree", "SwapTotal", "SwapFree"}:
            memory[key] = int(value.strip().split()[0])

    statvfs = os.statvfs(str(Path.home()))
    process_cpu_rows, selected_processes, cpu_sample_interval, cpu_sample_state, cpu_sample_errors = sample_process_cpu()
    selected = Counter(row["comm"] for row in selected_processes)

    vmstat = {}
    for line in Path("/proc/vmstat").read_text().splitlines():
        key, value = line.split()
        if key in {"pswpin", "pswpout", "pgmajfault", "oom_kill"}:
            vmstat[key] = int(value)

    services = collect_systemd_states()
    packagekit = packagekit_transaction_state(services)
    timeout_identity = timeout_executable_identity()
    thermal = {}
    for zone in sorted(Path("/sys/class/thermal").glob("thermal_zone*")):
        try:
            thermal[(zone / "type").read_text().strip()] = round(int((zone / "temp").read_text().strip()) / 1000, 3)
        except (FileNotFoundError, PermissionError, ValueError):
            continue
    cpu_frequency_khz = {}
    for cpu in sorted(Path("/sys/devices/system/cpu").glob("cpu[0-9]*")):
        try:
            cpu_frequency_khz[cpu.name] = int((cpu / "cpufreq/scaling_cur_freq").read_text().strip())
        except (FileNotFoundError, PermissionError, ValueError):
            continue
    print(json.dumps({
        "schema": "kv260_cpu_p2_textvqa_runtime_preflight_v3",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "read-only P2 CPU-baseline preflight, no VLM inference or board configuration change",
        "arch": platform.machine(),
        "cpu_count": os.cpu_count(),
        "memory_kib": memory,
        "home_free_bytes": statvfs.f_bavail * statvfs.f_frsize,
        "timeout_executable": timeout_identity,
        "tools_present": {**{name: bool(shutil.which(name)) for name in
                              ("cmake", "g++", "make", "ninja", "rsync", "sha256sum", "/usr/bin/time")},
                          "timeout": timeout_identity["usable"]},
        "selected_process_counts": dict(sorted(selected.items())),
        "selected_processes": sorted(selected_processes, key=lambda row: row["pid"]),
        "preflight_pid": os.getpid(),
        "process_cpu_rows": sorted(process_cpu_rows, key=lambda row: row["pid"]),
        "process_cpu_sample_wait_seconds": PROCESS_CPU_SAMPLE_SECONDS,
        "process_cpu_sample_interval_seconds": cpu_sample_interval,
        "process_cpu_sample_state": cpu_sample_state,
        "process_cpu_sample_errors": cpu_sample_errors,
        "packagekit_transaction_state": packagekit,
        "vmstat_global": vmstat,
        "loadavg": Path("/proc/loadavg").read_text().strip(),
        "systemd_service_states": services,
        "jupyter_active": services["jupyter.service"]["active_state"],
        "jupyter_returncode": services["jupyter.service"]["returncode"],
        "thermal_c": thermal,
        "cpu_frequency_khz": cpu_frequency_khz,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
