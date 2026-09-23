#!/usr/bin/env python3
"""Read-only KV260 CPU-baseline resource snapshot; run through batch SSH stdin."""

import json
import os
import platform
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SYSTEMD_UNITS = ("jupyter.service", "apt-daily.service", "apt-daily-upgrade.service",
                "packagekit.service")


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


def main() -> None:
    memory = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in {"MemTotal", "MemAvailable", "CmaTotal", "CmaFree", "SwapTotal", "SwapFree"}:
            memory[key] = int(value.strip().split()[0])

    statvfs = os.statvfs(str(Path.home()))
    selected = Counter()
    selected_processes = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            name = (entry / "comm").read_text().strip()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if name in {"llama-mtmd-cli", "llama-server", "vivado", "vitis_hls", "xbutil", "python3",
                    "cmake", "ninja", "cc1plus", "cc1", "unattended-upgr", "apt", "apt-get",
                    "dpkg", "dpkg-deb", "packagekitd", "rsync"}:
            selected[name] += 1
            try:
                status = (entry / "status").read_text().splitlines()
                uid_line = next(line for line in status if line.startswith("Uid:"))
                uid = int(uid_line.split()[1])
            except (FileNotFoundError, PermissionError, ProcessLookupError, StopIteration, ValueError):
                uid = None
            selected_processes.append({"pid": int(entry.name), "uid": uid, "comm": name,
                                       "role": process_role(entry, name)})

    vmstat = {}
    for line in Path("/proc/vmstat").read_text().splitlines():
        key, value = line.split()
        if key in {"pswpin", "pswpout", "pgmajfault", "oom_kill"}:
            vmstat[key] = int(value)

    services = collect_systemd_states()
    packagekit = packagekit_transaction_state(services)
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
        "tools_present": {name: bool(shutil.which(name)) for name in
                           ("cmake", "g++", "make", "ninja", "rsync", "timeout", "sha256sum", "/usr/bin/time")},
        "selected_process_counts": dict(sorted(selected.items())),
        "selected_processes": sorted(selected_processes, key=lambda row: row["pid"]),
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
