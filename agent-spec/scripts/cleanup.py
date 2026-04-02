#!/usr/bin/env python3
"""cleanup.py — Stop all agent-spec processes, clear ports, remove sandboxes.

Usage:
  python3 scripts/cleanup.py           # Stop processes, remove sandboxes, keep logs
  python3 scripts/cleanup.py --force   # Also delete /tmp run logs
"""
import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (
    PORT_MIN, PORT_MAX, SANDBOX_ROOT, RUN_ROOT, PID_FILE,
    stop_tracked_pids, release_port, get_tracked_pids, _stop_process_tree,
)


def main(args=None):
    parser = argparse.ArgumentParser(description="Stop all agent-spec processes, clear ports, remove sandboxes")
    parser.add_argument("--force", action="store_true", help="Also delete /tmp run logs")
    args = args or parser.parse_args()

    force = args.force

    print("── agent-spec cleanup ──")
    print()

    # 1. Stop all tracked PIDs (with process tree traversal)
    tracked = get_tracked_pids()
    if tracked:
        alive = [p for p in tracked if p["alive"]]
        print(f"  Tracked PIDs: {len(tracked)} ({len(alive)} alive)")
        stop_tracked_pids()
    else:
        print("  Tracked PIDs: none")

    # 2. Clear all ports
    stopped_ports = 0
    for port in range(PORT_MIN, PORT_MAX + 1):
        result = subprocess.run(["lsof", f"-ti:{port}"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            release_port(port)
            stopped_ports += 1
    if stopped_ports:
        print(f"  Cleared {stopped_ports} ports")

    # 3. Stop orphaned processes by pattern (fallback for untracked processes)
    orphan_count = 0
    for pattern in ["system_monitor.*sidecar", "bun.*server", "node.*queries",
                     "chromium.*agent-spec", "patchright"]:
        try:
            result = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                for pid_str in result.stdout.strip().split("\n"):
                    try:
                        pid = int(pid_str.strip())
                        _stop_process_tree(pid, pattern)
                        orphan_count += 1
                    except (ValueError, ProcessLookupError):
                        pass
        except subprocess.TimeoutExpired:
            pass
    if orphan_count:
        print(f"  Stopped {orphan_count} orphaned processes")

    # 4. Remove sandboxes
    sandbox_count = 0
    for d in glob.glob(f"{SANDBOX_ROOT}-*"):
        if Path(d).is_dir():
            subprocess.run(["rm", "-rf", d], timeout=30)
            sandbox_count += 1
    for d in glob.glob("/tmp/agent-spec-inject-*"):
        subprocess.run(["rm", "-rf", d], timeout=10)
    if sandbox_count:
        print(f"  Removed {sandbox_count} sandboxes")

    # 5. Clean parallel logs
    parallel_logs = glob.glob("/tmp/agent-spec-parallel-*")
    if parallel_logs:
        for f in parallel_logs:
            try:
                os.remove(f) if Path(f).is_file() else subprocess.run(["rm", "-rf", f], timeout=10)
            except OSError:
                pass
        print(f"  Removed {len(parallel_logs)} parallel log files")

    # 6. Force: delete /tmp logs too
    if force:
        for d in glob.glob(f"{RUN_ROOT}/*/"):
            subprocess.run(["rm", "-rf", d], timeout=30)
        print("  Force: deleted /tmp run logs")

    # 7. Prune worktrees
    subprocess.run(["git", "worktree", "prune"], capture_output=True, timeout=10)

    # 8. Verify
    print()
    remaining_sandboxes = len(glob.glob(f"{SANDBOX_ROOT}-*"))
    remaining_tracked = len(PID_FILE.read_text().splitlines()) if PID_FILE.exists() else 0
    remaining_ports = 0
    for port in range(PORT_MIN, PORT_MAX + 1):
        result = subprocess.run(["lsof", f"-ti:{port}"], capture_output=True, timeout=3)
        if result.returncode == 0 and result.stdout.strip():
            remaining_ports += 1

    if remaining_sandboxes == 0 and remaining_tracked == 0 and remaining_ports == 0:
        print("  Clean.")
    else:
        if remaining_sandboxes:
            print(f"  WARNING: {remaining_sandboxes} sandboxes remain")
        if remaining_tracked:
            print(f"  WARNING: {remaining_tracked} tracked PIDs remain")
        if remaining_ports:
            print(f"  WARNING: {remaining_ports} ports still in use")


if __name__ == "__main__":
    main()
