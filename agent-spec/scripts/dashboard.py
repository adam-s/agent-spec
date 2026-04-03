#!/usr/bin/env python3
"""dashboard.py — CLI dashboard for agent-spec runs.

Usage:
  python3 scripts/dashboard.py <run_id>              # Live tail
  python3 scripts/dashboard.py --latest              # Most recent run
  python3 scripts/dashboard.py <run_id> --summary    # One-shot summary
  python3 scripts/dashboard.py <run_id> --stream     # Compact one-line-per-event (no color)
  python3 scripts/dashboard.py --diff <id1> <id2>    # Config diff between two runs
  python3 scripts/dashboard.py --parallel <id>       # Multi-instance status table
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import RUN_ROOT, load_events, get_event, RESET, BOLD, DIM, RED, GREEN, YELLOW, CYAN

LEVEL_COLORS = {"ERROR": RED, "WARN": YELLOW, "METRIC": CYAN, "INFO": GREEN, "DEBUG": DIM}


# ── Event detail formatters ──────────────────────────────────────
# Each returns a short string summarizing the event's data.
# The dispatch table keeps format_event clean and extensible.

def _fmt_token_update(d):
    return f"{d.get('input', 0)}in/{d.get('output', 0)}out ${d.get('cost_usd', 0)}"

def _fmt_resource_snapshot(d):
    return f"CPU {d.get('cpu', 0)}% Mem {d.get('mem', 0)}%"

def _fmt_score(d):
    return d.get("result", "?")

def _fmt_agent_complete(d):
    return f"{d.get('duration_ms', 0)/1000:.1f}s"

def _fmt_test_result(d):
    return d.get("test_name", "")

def _fmt_verification_output(d):
    return f"exit={d.get('exit_code', '?')}, {len(d.get('output', ''))} chars"

def _fmt_instance_complete(d):
    return f"#{d.get('instance', '?')} run={d.get('run_id', '?')} {d.get('result', '?')}"

def _fmt_instance_failed(d):
    return f"#{d.get('instance', '?')} run={d.get('run_id', '?')} exit={d.get('exit_code', '?')}"

def _fmt_parallel_complete(d):
    return f"{d.get('passed', 0)}/{d.get('total', 0)} passed, {d.get('duration_ms', 0)//1000}s"

def _fmt_parallel_started(d):
    return f"{d.get('total', '?')} instances"

def _fmt_iteration_started(d):
    return f"depth {d.get('depth', '?')}/{d.get('max_depth', '?')} session={d.get('session_id', '?')[:8]}"

def _fmt_iteration_diagnosed(d):
    return f"depth {d.get('depth', '?')} — {d.get('findings_count', 0)} findings"

def _fmt_iteration_fixed(d):
    return f"depth {d.get('depth', '?')} — {len(d.get('files_changed', []))} files changed"

def _fmt_iteration_complete(d):
    conv = "CONVERGED" if d.get("converged") else f"pass_rate={d.get('pass_rate', '?')}"
    return f"depth {d.get('depth', '?')} — {conv}"

def _fmt_iteration_session_complete(d):
    conv = "CONVERGED" if d.get("converged") else "NOT CONVERGED"
    return f"{conv} depth={d.get('final_depth', '?')} ${d.get('total_cost_usd', 0):.2f}"


EVENT_FORMATTERS = {
    "token_update":               _fmt_token_update,
    "resource_snapshot":          _fmt_resource_snapshot,
    "score":                      _fmt_score,
    "agent_complete":             _fmt_agent_complete,
    "test_passed":                _fmt_test_result,
    "test_failed":                _fmt_test_result,
    "verification_output":        _fmt_verification_output,
    "instance_complete":          _fmt_instance_complete,
    "instance_failed":            _fmt_instance_failed,
    "parallel_complete":          _fmt_parallel_complete,
    "parallel_started":           _fmt_parallel_started,
    "iteration_started":          _fmt_iteration_started,
    "iteration_diagnosed":        _fmt_iteration_diagnosed,
    "iteration_fixed":            _fmt_iteration_fixed,
    "iteration_complete":         _fmt_iteration_complete,
    "iteration_session_complete": _fmt_iteration_session_complete,
    "preflight_check":    lambda d: f"{d.get('overall', '?')} cpu={d.get('cpu', 0)}% mem={d.get('mem', 0)}% disk={d.get('disk_free_gb', 0)}GB",
    "resource_warning":   lambda d: f"cpu={d.get('cpu', 0)}% mem={d.get('mem', 0)}% disk={d.get('disk_free_gb', 0)}GB",
}


def format_event(e: dict) -> str:
    ts = e.get("ts", "")[11:19]
    level = e.get("level", "?")
    event = e.get("event", "?")
    msg = e.get("msg", "")
    data = e.get("data", {})
    color = LEVEL_COLORS.get(level, GREEN)

    line = f"{DIM}[{ts}]{RESET} {color}[{level}]{RESET} {BOLD}{event}{RESET} — {msg}"

    fmt = EVENT_FORMATTERS.get(event)
    if fmt:
        line += f" {DIM}[{fmt(data)}]{RESET}"
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

    # Resource warnings
    warnings = [e for e in events if e.get("event") == "resource_warning"]
    if warnings:
        print(f"  {YELLOW}Resource warnings: {len(warnings)}{RESET}")
        for w in warnings[-3:]:  # show last 3
            print(f"    {YELLOW}{w.get('msg', '?')}{RESET}")

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


ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def format_stream(e: dict) -> str:
    """Compact, no-color, one-line format for piping and grep."""
    ts = e.get("ts", "")[11:19]
    level = e.get("level", "?")
    event = e.get("event", "?")
    msg = e.get("msg", "")
    data = e.get("data", {})

    # Build key=val pairs from data (skip large fields)
    kvs = []
    for k, v in data.items():
        sv = str(v)
        if len(sv) > 80:
            sv = sv[:77] + "..."
        kvs.append(f"{k}={sv}")
    kv_str = f" [{', '.join(kvs)}]" if kvs else ""
    return f"{ts} {level:5s} {event} {msg}{kv_str}"


def print_diff(id1: str, id2: str):
    """Show config diff between two runs using archived config-snapshot dirs."""
    from lib import find_results_dir

    dir1 = find_results_dir(id1)
    dir2 = find_results_dir(id2)
    snap1 = dir1 / "config-snapshot" if dir1 else None
    snap2 = dir2 / "config-snapshot" if dir2 else None

    if not snap1 or not snap1.exists():
        print(f"No config snapshot for {id1}. Run with updated invoke.py to archive configs.", file=sys.stderr)
        sys.exit(1)
    if not snap2 or not snap2.exists():
        print(f"No config snapshot for {id2}. Run with updated invoke.py to archive configs.", file=sys.stderr)
        sys.exit(1)

    print(f"── Config diff: {id1} → {id2} ──\n")
    result = subprocess.run(
        ["diff", "-ruN", str(snap1), str(snap2)],
        capture_output=True, text=True,
    )
    if result.stdout:
        # Clean up paths for readability
        output = result.stdout.replace(str(snap1), f"{id1}/.claude")
        output = output.replace(str(snap2), f"{id2}/.claude")
        print(output)
    else:
        print("  No differences in config.")


def print_parallel_status(parallel_id: str):
    """Show status table for all instances in a parallel run."""
    log_path = RUN_ROOT / parallel_id / "events.jsonl"
    if not log_path.exists():
        print(f"No events for parallel run {parallel_id}", file=sys.stderr)
        sys.exit(1)

    events = load_events(log_path)

    # Collect instance info
    instances = {}
    for e in events:
        ev = e.get("event", "")
        d = e.get("data", {})
        inst = d.get("instance")
        if inst is None:
            continue

        if inst not in instances:
            instances[inst] = {"config": "?", "model": "?", "port": "?", "status": "launched", "result": "?", "run_id": "?", "cost": 0}

        if ev == "instance_launched":
            instances[inst].update({"config": d.get("config", "?"), "model": d.get("model", "?"), "port": d.get("port", "?")})
        elif ev == "instance_complete":
            instances[inst].update({"status": "done", "result": d.get("result", "?"), "run_id": d.get("run_id", "?")})
        elif ev == "instance_failed":
            instances[inst].update({"status": "failed", "result": "FAIL", "run_id": d.get("run_id", "?")})

    # Enrich with token data from child runs
    for inst, info in instances.items():
        if info["run_id"] != "?":
            child_log = RUN_ROOT / info["run_id"] / "events.jsonl"
            if child_log.exists():
                child_events = load_events(child_log)
                tok = get_event(child_events, "token_update")
                if tok:
                    info["cost"] = tok["data"].get("cost_usd", 0)

    # Check for overall completion
    par_complete = get_event(events, "parallel_complete")

    print(f"── Parallel run: {parallel_id} ──\n")

    if par_complete:
        d = par_complete["data"]
        print(f"  Status: COMPLETE — {d.get('passed', 0)}/{d.get('total', 0)} passed ({d.get('duration_ms', 0)//1000}s)\n")
    else:
        done = sum(1 for i in instances.values() if i["status"] in ("done", "failed"))
        print(f"  Status: RUNNING — {done}/{len(instances)} complete\n")

    # Shorten model names for display
    def short_model(m):
        m = str(m)
        for prefix in ("claude-", "anthropic-"):
            m = m.replace(prefix, "")
        # Trim date suffixes like -20251001
        if len(m) > 15 and m[-8:].isdigit():
            m = m[:-9]
        return m

    # Table
    print(f"  {'#':>3}  {'Config':15s}  {'Model':12s}  {'Port':>5}  {'Status':8s}  {'Result':6s}  {'Cost':>7}  {'Run ID':8s}")
    print(f"  {'─'*3}  {'─'*15}  {'─'*12}  {'─'*5}  {'─'*8}  {'─'*6}  {'─'*7}  {'─'*8}")

    for idx in sorted(instances.keys()):
        i = instances[idx]
        cost_str = f"${i['cost']:.3f}" if i['cost'] else "—"
        print(f"  {idx:>3}  {i['config']:15s}  {short_model(i['model']):12s}  {i['port']:>5}  {i['status']:8s}  {i['result']:6s}  {cost_str:>7}  {i['run_id']:8s}")

    print()


def main(args=None):
    parser = argparse.ArgumentParser(
        prog="dashboard",
        description="CLI dashboard for agent-spec runs",
    )
    parser.add_argument("run_id", nargs="?", help="Run ID to display")
    parser.add_argument("--latest", action="store_true", help="Show most recent run")
    parser.add_argument("--summary", action="store_true", help="One-shot summary (no live tail)")
    parser.add_argument("--stream", action="store_true", help="Compact one-line-per-event, no color")
    parser.add_argument("--diff", nargs=2, metavar="RUN_ID", help="Config diff between two runs")
    parser.add_argument("--parallel", metavar="PARALLEL_ID", help="Multi-instance status table")
    args = args or parser.parse_args()

    # Dispatch to special modes
    if args.diff:
        print_diff(args.diff[0], args.diff[1])
        return

    if args.parallel:
        print_parallel_status(args.parallel)
        return

    run_id = args.run_id
    if args.latest:
        dirs = sorted(Path(RUN_ROOT).iterdir(), key=lambda d: d.stat().st_mtime, reverse=True) \
            if RUN_ROOT.exists() else []
        if not dirs:
            print("No runs found", file=sys.stderr); sys.exit(1)
        run_id = dirs[0].name

    if not run_id:
        parser.print_help()
        sys.exit(1)

    log_path = RUN_ROOT / run_id / "events.jsonl"
    if not log_path.exists():
        print(f"No events found: {log_path}", file=sys.stderr)
        sys.exit(1)

    if args.stream:
        events = load_events(log_path)
        for e in events:
            print(format_stream(e))
    elif args.summary:
        events = load_events(log_path)
        print_summary(run_id, events)
    else:
        live_tail(log_path)


if __name__ == "__main__":
    main()
