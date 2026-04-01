#!/usr/bin/env python3
"""dashboard.py — CLI dashboard for agent-spec runs.

Usage:
  python3 scripts/dashboard.py <run_id>              # Live tail
  python3 scripts/dashboard.py --latest              # Most recent run
  python3 scripts/dashboard.py <run_id> --summary    # One-shot summary
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import RUN_ROOT, load_events, get_event

# ANSI colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[90m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

LEVEL_COLORS = {"ERROR": RED, "WARN": YELLOW, "METRIC": CYAN, "INFO": GREEN, "DEBUG": DIM}


def format_event(e: dict) -> str:
    ts = e.get("ts", "")[11:19]
    level = e.get("level", "?")
    event = e.get("event", "?")
    msg = e.get("msg", "")
    color = LEVEL_COLORS.get(level, GREEN)

    line = f"{DIM}[{ts}]{RESET} {color}[{level}]{RESET} {BOLD}{event}{RESET} — {msg}"

    data = e.get("data", {})
    if event == "token_update":
        line += f" {DIM}[{data.get('input', 0)}in/{data.get('output', 0)}out ${data.get('cost_usd', 0)}]{RESET}"
    elif event == "resource_snapshot":
        line += f" {DIM}[CPU {data.get('cpu', 0)}% Mem {data.get('mem', 0)}%]{RESET}"
    elif event == "score":
        line += f" {DIM}[{data.get('result', '?')}]{RESET}"
    elif event == "agent_complete":
        dur = data.get("duration_ms", 0)
        line += f" {DIM}[{dur/1000:.1f}s]{RESET}"
    elif event == "test_passed":
        line += f" {DIM}[{data.get('test_name', '')}]{RESET}"
    elif event == "test_failed":
        line += f" {DIM}[{data.get('test_name', '')}]{RESET}"
    elif event == "verification_output":
        # Truncate for display
        out = data.get("output", "")[:200]
        line += f" {DIM}[exit={data.get('exit_code', '?')}, {len(data.get('output', ''))} chars]{RESET}"
    elif event == "instance_complete":
        line += f" {DIM}[#{data.get('instance', '?')} run={data.get('run_id', '?')} {data.get('result', '?')}]{RESET}"
    elif event == "instance_failed":
        line += f" {DIM}[#{data.get('instance', '?')} run={data.get('run_id', '?')} exit={data.get('exit_code', '?')}]{RESET}"
    elif event == "parallel_complete":
        line += f" {DIM}[{data.get('passed', 0)}/{data.get('total', 0)} passed, {data.get('duration_ms', 0)//1000}s]{RESET}"
    elif event == "parallel_started":
        line += f" {DIM}[{data.get('total', '?')} instances]{RESET}"
    elif data:
        line += f" {DIM}{json.dumps(data)}{RESET}"
    return line


def print_summary(run_id: str, events: list[dict]):
    print(f"── agent-spec ─── run: {run_id} ──")
    print()

    started = get_event(events, "agent_started")
    if started:
        d = started["data"]
        print(f"  Target: {d.get('target', '?')} / {d.get('config', '?')}")

    complete = get_event(events, "agent_complete") or get_event(events, "agent_error")
    if complete:
        dur_ms = complete["data"].get("duration_ms", 0)
        dur_s = dur_ms // 1000
        status = "COMPLETE" if complete["event"] == "agent_complete" else "ERROR"
        if dur_s >= 60:
            print(f"  Status: {status} ({dur_s}s / {dur_s // 60}m {dur_s % 60}s)")
        else:
            print(f"  Status: {status} ({dur_s}s)")

    token = get_event(events, "token_update")
    if token:
        d = token["data"]
        print(f"  Tokens: {d.get('input', 0)} in / {d.get('output', 0)} out / ${d.get('cost_usd', 0)}")

    # Tests
    passed = sum(1 for e in events if e.get("event") == "test_passed")
    failed = sum(1 for e in events if e.get("event") == "test_failed")
    total = passed + failed
    if total > 0:
        print(f"  Tests:  {passed} passed / {failed} failed ({total} total)")

    score = get_event(events, "score")
    if score:
        print(f"  Result: {score['data'].get('result', '?')}")

    # Resources
    resource = get_event(events, "resource_snapshot")
    if resource:
        d = resource["data"]
        print(f"  Resources: CPU {d.get('cpu', 0)}% | Mem {d.get('mem', 0)}% | Disk {d.get('disk_free_gb', 0)} GB free")

    print()
    print("  Events:")
    for e in events:
        print(f"    {format_event(e)}")


def live_tail(log_path: Path):
    print(f"── agent-spec ─── tailing {log_path.parent.name} ──")
    print()

    # Print existing events
    if log_path.exists():
        for e in load_events(log_path):
            print(format_event(e))

    # Tail for new events
    try:
        with open(log_path) as f:
            f.seek(0, 2)  # end of file
            while True:
                line = f.readline()
                if line:
                    try:
                        print(format_event(json.loads(line)))
                    except json.JSONDecodeError:
                        pass
                else:
                    time.sleep(0.5)
    except KeyboardInterrupt:
        pass


def main():
    run_id = None
    summary = False

    args = sys.argv[1:]
    for arg in args:
        if arg == "--latest":
            dirs = sorted(Path(RUN_ROOT).iterdir(), key=lambda d: d.stat().st_mtime, reverse=True) \
                if RUN_ROOT.exists() else []
            if not dirs:
                print("No runs found", file=sys.stderr); sys.exit(1)
            run_id = dirs[0].name
        elif arg == "--summary":
            summary = True
        else:
            run_id = arg

    if not run_id:
        print("Usage: dashboard.py <run_id> | --latest [--summary]", file=sys.stderr)
        sys.exit(1)

    log_path = RUN_ROOT / run_id / "events.jsonl"
    if not log_path.exists():
        print(f"No events found: {log_path}", file=sys.stderr)
        sys.exit(1)

    if summary:
        events = load_events(log_path)
        print_summary(run_id, events)
    else:
        live_tail(log_path)


if __name__ == "__main__":
    main()
