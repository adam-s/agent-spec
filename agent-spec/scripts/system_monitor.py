#!/usr/bin/env python3
"""system_monitor.py — Resource monitoring with thresholds and pre-flight checks.

Ported from claudodidact/shared/system_monitor.py. Provides:
- Disk, memory, CPU collectors with CRITICAL/WARNING/OK status
- Pre-flight check that blocks agent launches when resources are critical
- Formatted console status table
- Sidecar mode for continuous monitoring during runs
- Plugin support for target-specific collectors

Usage:
  python3 scripts/system_monitor.py                    # one-shot status
  python3 scripts/system_monitor.py watch              # continuous (every 10s)
  python3 scripts/system_monitor.py watch --interval 5
  python3 scripts/system_monitor.py sidecar --run-id X # emit events to JSONL
"""

import argparse
import glob
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ── Thresholds ──────────────────────────────────────────────────

DISK_WARN_GB = 30
DISK_CRITICAL_GB = 15
MEM_WARN_PCT = 85
MEM_CRITICAL_PCT = 95
CPU_WARN_PCT = 80


# ── Collectors ──────────────────────────────────────────────────

def get_disk_usage() -> dict:
    """Disk usage for root partition."""
    total, used, free = shutil.disk_usage("/")
    total_gb = total / (1024 ** 3)
    used_gb = used / (1024 ** 3)
    free_gb = free / (1024 ** 3)
    pct = (used / total) * 100
    if free_gb < DISK_CRITICAL_GB:
        status = "CRITICAL"
    elif free_gb < DISK_WARN_GB:
        status = "WARNING"
    else:
        status = "OK"
    return {
        "total_gb": round(total_gb, 1),
        "used_gb": round(used_gb, 1),
        "free_gb": round(free_gb, 1),
        "pct": round(pct, 1),
        "status": status,
    }


def get_memory_usage() -> dict:
    """Memory usage via vm_stat (macOS) or /proc/meminfo (Linux)."""
    try:
        if platform.system() == "Darwin":
            result = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            stats = {}
            for line in lines[1:]:
                if ":" in line:
                    key, val = line.split(":", 1)
                    val = val.strip().rstrip(".")
                    try:
                        stats[key.strip()] = int(val)
                    except ValueError:
                        pass

            page_size = 16384
            free = stats.get("Pages free", 0) * page_size
            active = stats.get("Pages active", 0) * page_size
            inactive = stats.get("Pages inactive", 0) * page_size
            speculative = stats.get("Pages speculative", 0) * page_size
            wired = stats.get("Pages wired down", 0) * page_size
            compressed = stats.get("Pages occupied by compressor", 0) * page_size

            total_bytes = free + active + inactive + speculative + wired + compressed
            used_bytes = active + wired + compressed
        else:
            # Linux
            meminfo = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    meminfo[key.strip()] = int(val.strip().split()[0]) * 1024
            total_bytes = meminfo.get("MemTotal", 1)
            available = meminfo.get("MemAvailable", 0)
            used_bytes = total_bytes - available

        total_gb = total_bytes / (1024 ** 3)
        used_gb = used_bytes / (1024 ** 3)
        pct = (used_bytes / total_bytes * 100) if total_bytes > 0 else 0

        if pct > MEM_CRITICAL_PCT:
            status = "CRITICAL"
        elif pct > MEM_WARN_PCT:
            status = "WARNING"
        else:
            status = "OK"

        return {
            "total_gb": round(total_gb, 1),
            "used_gb": round(used_gb, 1),
            "free_gb": round(total_gb - used_gb, 1),
            "pct": round(pct, 1),
            "status": status,
        }
    except Exception as e:
        return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "pct": 0, "status": f"ERROR: {e}"}


def get_cpu_usage() -> dict:
    """CPU usage aggregated across all processes."""
    try:
        result = subprocess.run(
            ["ps", "-A", "-o", "%cpu"],
            capture_output=True, text=True, timeout=5
        )
        total = sum(float(line.strip()) for line in result.stdout.strip().split("\n")[1:] if line.strip())
        cores = os.cpu_count() or 1
        pct = total / cores
        status = "WARNING" if pct > CPU_WARN_PCT else "OK"
        return {"pct": round(pct, 1), "cores": cores, "status": status}
    except Exception as e:
        return {"pct": 0, "cores": 0, "status": f"ERROR: {e}"}


def get_agent_spec_processes() -> dict:
    """Count active agent-spec runs, sandboxes, and ports."""
    from lib import SANDBOX_ROOT, RUN_ROOT, PORT_MIN, PORT_MAX

    sandboxes = len(glob.glob(f"{SANDBOX_ROOT}-*"))

    active_runs = 0
    if RUN_ROOT.exists():
        for d in RUN_ROOT.iterdir():
            events = d / "events.jsonl"
            if events.exists():
                # Check if run has a completion event
                text = events.read_text()
                if '"agent_started"' in text and '"agent_complete"' not in text and '"agent_error"' not in text:
                    active_runs += 1

    ports_in_use = []
    for port in range(PORT_MIN, PORT_MAX + 1):
        result = subprocess.run(["lsof", f"-ti:{port}"], capture_output=True, timeout=3)
        if result.returncode == 0 and result.stdout.strip():
            ports_in_use.append(port)

    return {
        "active_runs": active_runs,
        "sandboxes": sandboxes,
        "ports_in_use": ports_in_use,
        "port_count": len(ports_in_use),
    }


# ── Plugin Collectors ───────────────────────────────────────────

def load_collectors(target_dir: Path | None = None) -> list[dict]:
    """Load custom collectors from a target's monitor/collectors.py."""
    results = []
    if not target_dir:
        return results

    collectors_file = target_dir / "monitor" / "collectors.py"
    if not collectors_file.exists():
        return results

    try:
        spec = importlib.util.spec_from_file_location("collectors", collectors_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for fn in getattr(mod, "COLLECTORS", []):
            try:
                results.append({"name": fn.__name__, "data": fn()})
            except Exception as e:
                results.append({"name": fn.__name__, "data": {"status": f"ERROR: {e}"}})
    except Exception as e:
        results.append({"name": "collectors", "data": {"status": f"LOAD ERROR: {e}"}})

    return results


# ── Snapshot & Preflight ────────────────────────────────────────

def get_snapshot(target_dir: Path | None = None) -> dict:
    """Collect all metrics into a single snapshot."""
    disk = get_disk_usage()
    mem = get_memory_usage()
    cpu = get_cpu_usage()
    procs = get_agent_spec_processes()
    custom = load_collectors(target_dir)

    has_critical = any(
        d.get("status") == "CRITICAL"
        for d in [disk, mem, cpu]
    )
    has_warning = any(
        d.get("status") == "WARNING"
        for d in [disk, mem, cpu]
    )

    if has_critical:
        overall = "CRITICAL"
    elif has_warning:
        overall = "WARNING"
    else:
        overall = "OK"

    # Build summary string
    issues = []
    if disk["status"] != "OK":
        issues.append(f"disk {disk['free_gb']:.0f}GB free")
    if mem["status"] != "OK":
        issues.append(f"memory {mem['pct']:.0f}%")
    if cpu["status"] != "OK":
        issues.append(f"cpu {cpu['pct']:.0f}%")

    return {
        "disk": disk,
        "memory": mem,
        "cpu": cpu,
        "processes": procs,
        "custom": custom,
        "overall": overall,
        "status_summary": ", ".join(issues) if issues else "all OK",
        # Flat fields for event logging
        "cpu_pct": cpu["pct"],
        "mem_pct": mem["pct"],
        "disk_free_gb": disk["free_gb"],
    }


def check_preflight() -> tuple[bool, dict]:
    """Pre-flight resource check. Returns (ok, snapshot).

    Returns False if any resource is CRITICAL — caller should refuse to launch.
    """
    snapshot = get_snapshot()
    ok = snapshot["overall"] != "CRITICAL"
    return ok, snapshot


# ── Display ─────────────────────────────────────────────────────

def _status_icon(status: str) -> str:
    if status == "OK":
        return " OK "
    elif status == "WARNING":
        return "WARN"
    elif status == "CRITICAL":
        return "CRIT"
    else:
        return " ?? "


def print_status_table(snapshot: dict | None = None):
    """Print formatted status table to stdout."""
    if snapshot is None:
        snapshot = get_snapshot()

    disk = snapshot["disk"]
    mem = snapshot["memory"]
    cpu = snapshot["cpu"]
    procs = snapshot["processes"]
    overall = snapshot["overall"]

    W = 56
    print()
    print("\u2550" * W)
    label = "CRITICAL" if overall == "CRITICAL" else "WARNING" if overall == "WARNING" else "OK"
    print(f"  SYSTEM STATUS  {label}")
    print("\u2550" * W)
    print(f"  {'Resource':<22} {'Value':>14} {'Free':>8}  {'':>4}")
    print("\u2500" * W)

    # Disk
    print(f"  {'Disk':<22} {disk['used_gb']:>5.0f} / {disk['total_gb']:.0f} GB  {disk['free_gb']:>5.0f} GB  [{_status_icon(disk['status'])}]")

    # Memory
    print(f"  {'Memory':<22} {mem['used_gb']:>5.0f} / {mem['total_gb']:.0f} GB  {mem['free_gb']:>5.0f} GB  [{_status_icon(mem['status'])}]")

    # CPU
    cpu_label = f"CPU ({cpu['cores']} cores)"
    print(f"  {cpu_label:<22} {cpu['pct']:>13.0f}%  {'':>8}  [{_status_icon(cpu['status'])}]")

    # agent-spec processes
    print("\u2500" * W)
    print(f"  {'Active Runs':<22} {procs['active_runs']:>14}")
    print(f"  {'Sandboxes':<22} {procs['sandboxes']:>14}")
    ports_str = ",".join(str(p) for p in procs["ports_in_use"]) if procs["ports_in_use"] else "none"
    print(f"  {'Ports in use':<22} {procs['port_count']:>14}  {ports_str}")

    # Custom collectors
    for c in snapshot.get("custom", []):
        name = c["name"].replace("get_", "").replace("_", " ").title()
        data = c["data"]
        status = data.get("status", "?")
        print(f"  {name:<22} {'':>14}  {'':>8}  [{_status_icon(status)}]")
        for k, v in data.items():
            if k != "status":
                print(f"    {k:<20} {str(v):>14}")

    print("\u2550" * W)

    # Warnings
    if overall == "CRITICAL":
        print()
        print("  *** CRITICAL — do not launch agents ***")
        if disk["status"] == "CRITICAL":
            print(f"  DISK: Only {disk['free_gb']:.1f} GB free (threshold: {DISK_CRITICAL_GB} GB)")
        if mem["status"] == "CRITICAL":
            print(f"  MEMORY: {mem['pct']:.0f}% used (threshold: {MEM_CRITICAL_PCT}%)")
        print()
    elif overall == "WARNING":
        print()
        if disk["status"] == "WARNING":
            print(f"  NOTE: Disk low ({disk['free_gb']:.1f} GB free)")
        if mem["status"] == "WARNING":
            print(f"  NOTE: Memory high ({mem['pct']:.0f}% used)")
        print()

    return overall != "CRITICAL"


# ── Sidecar Mode ────────────────────────────────────────────────

def run_sidecar(run_id: str, interval: int = 30):
    """Continuous monitoring that writes events to JSONL."""
    from lib import apc_log

    while True:
        try:
            snapshot = get_snapshot()
            event_data = {
                "cpu": snapshot["cpu_pct"],
                "mem": snapshot["mem_pct"],
                "disk_free_gb": snapshot["disk_free_gb"],
            }
            apc_log("METRIC", "resource_snapshot", "System resources",
                    event_data, run_id=run_id)

            # Emit warnings for threshold breaches
            if snapshot["overall"] == "CRITICAL":
                apc_log("WARN", "resource_warning",
                        f"CRITICAL: {snapshot['status_summary']}",
                        event_data, run_id=run_id)
                print(f"WARNING: System resources critical — {snapshot['status_summary']}",
                      file=sys.stderr)
            elif snapshot["overall"] == "WARNING":
                apc_log("WARN", "resource_warning",
                        f"WARNING: {snapshot['status_summary']}",
                        event_data, run_id=run_id)
        except Exception as e:
            print(f"Monitor error (will retry): {e}", file=sys.stderr)

        time.sleep(interval)


# ── CLI ─────────────────────────────────────────────────────────

def main(args=None):
    parser = argparse.ArgumentParser(
        prog="system_monitor",
        description="System resource monitor for agent-spec",
    )
    sub = parser.add_subparsers(dest="command")

    p_watch = sub.add_parser("watch", help="Continuous monitoring")
    p_watch.add_argument("--interval", type=int, default=10)

    p_sidecar = sub.add_parser("sidecar", help="Emit events to JSONL (used by invoke.py)")
    p_sidecar.add_argument("--run-id", required=True)
    p_sidecar.add_argument("--interval", type=int, default=30)

    args = args or parser.parse_args()

    if args.command == "watch":
        try:
            while True:
                os.system("clear")
                print_status_table()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            pass
    elif args.command == "sidecar":
        run_sidecar(args.run_id, args.interval)
    else:
        print_status_table()


if __name__ == "__main__":
    main()
