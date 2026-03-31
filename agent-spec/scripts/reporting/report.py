#!/usr/bin/env python3
"""report.py — Generate a full comparison report from agent-spec runs.

Usage: python3 scripts/reporting/report.py [run_id ...]
       python3 scripts/reporting/report.py --all
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path("/tmp/agent-spec")


def load_run(run_id):
    """Load events from a single run."""
    log = BASE / run_id / "events.jsonl"
    if not log.exists():
        return None

    events = []
    for line in log.read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    run = {"run_id": run_id, "events": events}

    for e in events:
        if e["event"] == "agent_started":
            run["target"] = e["data"].get("target", "?")
            run["config"] = e["data"].get("config", "?")
            run["model"] = e["data"].get("model", "?")
        elif e["event"] == "token_update":
            run["tokens"] = e["data"]
        elif e["event"] == "score":
            run["result"] = e["data"].get("result", "N/A")
        elif e["event"] == "agent_complete":
            run["duration_ms"] = e["data"].get("duration_ms", 0)
        elif e["event"] == "agent_error":
            run["result"] = "ERROR"
            run["duration_ms"] = e["data"].get("duration_ms", 0)

    return run


def print_table(runs):
    """Print markdown comparison table."""
    print("| Run ID | Target | Config | Input | Output | Total | Cost | Result | Duration |")
    print("|--------|--------|--------|------:|-------:|------:|-----:|--------|----------|")

    for r in runs:
        t = r.get("tokens", {})
        inp = t.get("input", 0)
        out = t.get("output", 0)
        total = inp + out
        cost = t.get("cost_usd", 0)
        result = r.get("result", "N/A")
        dur = r.get("duration_ms", 0)
        dur_s = f"{dur / 1000:.1f}s" if dur else "?"

        print(f"| {r['run_id']:8s} | {r.get('target', '?'):6s} | {r.get('config', '?'):6s} "
              f"| {inp:5d} | {out:6d} | {total:5d} | ${cost:.3f} | {result:6s} | {dur_s:8s} |")


def print_summary(runs):
    """Print per-config summary statistics."""
    by_config = defaultdict(list)
    for r in runs:
        key = f"{r.get('target', '?')}/{r.get('config', '?')}"
        by_config[key].append(r)

    print("\n## Summary by Config\n")
    print("| Target/Config | Runs | Pass Rate | Avg Tokens | Avg Cost |")
    print("|---------------|-----:|----------:|-----------:|---------:|")

    for key, group in sorted(by_config.items()):
        n = len(group)
        passes = sum(1 for r in group if r.get("result") == "PASS")
        pass_rate = f"{passes}/{n}"
        tokens = [r.get("tokens", {}).get("input", 0) + r.get("tokens", {}).get("output", 0)
                  for r in group]
        avg_tokens = sum(tokens) / n if n else 0
        costs = [r.get("tokens", {}).get("cost_usd", 0) for r in group]
        avg_cost = sum(costs) / n if n else 0

        print(f"| {key:13s} | {n:4d} | {pass_rate:9s} | {avg_tokens:10.0f} | ${avg_cost:.3f}   |")


def print_resource_summary(runs):
    """Print resource usage summary across runs."""
    all_snapshots = []
    for r in runs:
        for e in r.get("events", []):
            if e["event"] == "resource_snapshot":
                all_snapshots.append(e["data"])

    if not all_snapshots:
        return

    print("\n## Resource Usage\n")
    cpus = [s.get("cpu", 0) for s in all_snapshots]
    mems = [s.get("mem", 0) for s in all_snapshots]
    disks = [s.get("disk_free_gb", 0) for s in all_snapshots]

    print(f"  Snapshots: {len(all_snapshots)}")
    print(f"  Peak CPU:  {max(cpus):.1f}%")
    print(f"  Peak Mem:  {max(mems):.1f}%")
    print(f"  Min Disk:  {min(disks)} GB free")


def main():
    if len(sys.argv) < 2:
        print("Usage: report.py <run_id> ... | --all", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--all":
        run_ids = sorted(os.listdir(BASE)) if BASE.exists() else []
    else:
        run_ids = sys.argv[1:]

    runs = []
    for rid in run_ids:
        r = load_run(rid)
        if r:
            runs.append(r)

    if not runs:
        print("No runs found.", file=sys.stderr)
        sys.exit(1)

    print(f"# agent-spec Report — {len(runs)} run(s)\n")
    print_table(runs)
    print_summary(runs)
    print_resource_summary(runs)


if __name__ == "__main__":
    main()
