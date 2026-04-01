#!/usr/bin/env python3
"""cleanup.py — Stop all agent-spec processes, clear ports, remove sandboxes.

Usage:
  python3 scripts/cleanup.py           # Stop processes, remove sandboxes, keep logs
  python3 scripts/cleanup.py --force   # Also delete /tmp run logs
"""
import argparse
import glob
import os
import signal
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import PORT_MIN, PORT_MAX, SANDBOX_ROOT, RUN_ROOT, PID_FILE, stop_tracked_pids, release_port


def main(args=None):
    parser = argparse.ArgumentParser(description="Stop all agent-spec processes, clear ports, remove sandboxes")
    parser.add_argument("--force", action="store_true", help="Also delete /tmp run logs")
    args = args or parser.parse_args()

    force = args.force

    print("=== agent-spec cleanup ===")

    # 1. Stop tracked PIDs
    stop_tracked_pids()

    # 2. Clear all ports
    for port in range(PORT_MIN, PORT_MAX + 1):
        release_port(port)

    # 3. Stop orphaned processes
    for pattern in ["bun.*server", "node.*queries", "chromium.*agent-spec", "patchright", "sidecar"]:
        result = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            for pid in result.stdout.strip().split("\n"):
                try:
                    os.kill(int(pid), 9)
                    print(f"  Stopped: {pattern} (PID {pid})")
                except (ProcessLookupError, ValueError):
                    pass

    # 4. Remove sandboxes
    for d in glob.glob(f"{SANDBOX_ROOT}-*"):
        if Path(d).is_dir():
            subprocess.run(["rm", "-rf", d])

    # Remove inject dirs
    for d in glob.glob("/tmp/agent-spec-inject-*"):
        subprocess.run(["rm", "-rf", d])

    # 5. Force: delete /tmp logs too
    if force:
        for d in glob.glob(f"{RUN_ROOT}/*/"):
            subprocess.run(["rm", "-rf", d])
        for f in glob.glob("/tmp/agent-spec-parallel-*"):
            os.remove(f) if Path(f).is_file() else subprocess.run(["rm", "-rf", f])
        print("  Force: deleted /tmp run logs and parallel logs")

    # 6. Prune worktrees
    subprocess.run(["git", "worktree", "prune"], capture_output=True)

    # 7. Verify
    sandboxes = len(glob.glob(f"{SANDBOX_ROOT}-*"))
    run_dirs = len(glob.glob(f"{RUN_ROOT}/*/"))
    tracked = len(PID_FILE.read_text().splitlines()) if PID_FILE.exists() else 0
    port_check = subprocess.run(["lsof", f"-ti:{PORT_MIN}"], capture_output=True)
    port_count = len(port_check.stdout.decode().strip().split("\n")) if port_check.returncode == 0 else 0

    print()
    print("=== Verification ===")
    print(f"  Sandboxes:       {sandboxes}")
    print(f"  Run dirs (/tmp): {run_dirs}")
    print(f"  Tracked PIDs:    {tracked}")
    print(f"  Port {PORT_MIN}:        {port_count}")
    print()
    print("Clean.")


if __name__ == "__main__":
    main()
