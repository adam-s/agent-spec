#!/usr/bin/env python3
"""report.py — Generate comparison reports from agent-spec runs.

Usage:
  report.py --all                          Show all runs
  report.py --latest                       Show most recent run
  report.py <run_id> ...                   Show specific runs
  report.py --all --group-by config        Group by config with deltas
  report.py --all --group-by model         Group by model with deltas
  report.py --all --group-by target        Group by target with deltas
  report.py --compare <id1> <id2>          Side-by-side two-run diff
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


def get_metrics(run):
    """Extract comparable metrics from a run."""
    t = run.get("tokens", {})
    inp = t.get("input", 0)
    out = t.get("output", 0)
    return {
        "input": inp,
        "output": out,
        "total": inp + out,
        "cost": t.get("cost_usd", 0),
        "result": run.get("result", "N/A"),
        "duration_ms": run.get("duration_ms", 0),
        "turns": t.get("turns", 0),
    }


def print_table(runs):
    """Print markdown comparison table."""
    print("| Run ID | Target | Config | Model | Input | Output | Cost | Result | Duration |")
    print("|--------|--------|--------|-------|------:|-------:|-----:|--------|----------|")

    for r in runs:
        m = get_metrics(r)
        dur_s = f"{m['duration_ms'] / 1000:.0f}s" if m["duration_ms"] else "?"
        print(f"| {r['run_id']:8s} | {r.get('target', '?'):6s} | {r.get('config', '?'):6s} "
              f"| {r.get('model', '?'):5s} "
              f"| {m['input']:5d} | {m['output']:6d} | ${m['cost']:.3f} "
              f"| {m['result']:6s} | {dur_s:8s} |")


def print_group_by(runs, key):
    """Group runs by a field and show aggregated metrics with deltas."""
    groups = defaultdict(list)
    for r in runs:
        groups[r.get(key, "?")].append(r)

    print(f"\n## Grouped by {key}\n")
    print(f"| {key.title():15s} | Runs | Pass | Avg Tokens | Avg Cost | Avg Duration | Delta Cost | Delta Tokens |")
    print(f"|{'-'*17}|-----:|-----:|-----------:|---------:|-------------:|-----------:|-------------:|")

    summaries = []
    for name, group in sorted(groups.items()):
        n = len(group)
        passes = sum(1 for r in group if r.get("result") == "PASS")
        metrics = [get_metrics(r) for r in group]
        avg_tokens = sum(m["total"] for m in metrics) / n
        avg_cost = sum(m["cost"] for m in metrics) / n
        avg_dur = sum(m["duration_ms"] for m in metrics) / n
        summaries.append({
            "name": name, "n": n, "passes": passes,
            "avg_tokens": avg_tokens, "avg_cost": avg_cost, "avg_dur": avg_dur,
        })

    # First group is the baseline for deltas
    baseline = summaries[0] if summaries else None

    for s in summaries:
        dur_s = f"{s['avg_dur'] / 1000:.0f}s"
        if baseline and s != baseline:
            delta_cost = s["avg_cost"] - baseline["avg_cost"]
            delta_tokens = s["avg_tokens"] - baseline["avg_tokens"]
            dc = f"{delta_cost:+.3f}"
            dt = f"{delta_tokens:+.0f}"
        else:
            dc = "—"
            dt = "—"

        print(f"| {s['name']:15s} | {s['n']:4d} | {s['passes']:4d} "
              f"| {s['avg_tokens']:10.0f} | ${s['avg_cost']:.3f}   "
              f"| {dur_s:12s} | {dc:10s} | {dt:12s} |")


def print_compare(run_a, run_b):
    """Side-by-side comparison of two runs."""
    ma = get_metrics(run_a)
    mb = get_metrics(run_b)

    print(f"\n## Compare: {run_a['run_id']} vs {run_b['run_id']}\n")
    print(f"| Metric | {run_a['run_id']} | {run_b['run_id']} | Delta | % Change |")
    print(f"|--------|{'-'*10}|{'-'*10}|------:|---------:|")

    for label, key in [("Tokens", "total"), ("Input", "input"), ("Output", "output"),
                        ("Cost", "cost"), ("Duration (ms)", "duration_ms"), ("Turns", "turns")]:
        va = ma[key]
        vb = mb[key]
        delta = vb - va
        pct = f"{(delta / va * 100):+.1f}%" if va else "—"
        if key == "cost":
            print(f"| {label:14s} | ${va:.3f}    | ${vb:.3f}    | {delta:+.3f} | {pct:8s} |")
        else:
            print(f"| {label:14s} | {va:8} | {vb:8} | {delta:+8} | {pct:8s} |")

    print(f"| {'Result':14s} | {ma['result']:8s} | {mb['result']:8s} | {'':8s} | {'':8s} |")
    print(f"\n  {run_a['run_id']}: {run_a.get('target')}/{run_a.get('config')} ({run_a.get('model')})")
    print(f"  {run_b['run_id']}: {run_b.get('target')}/{run_b.get('config')} ({run_b.get('model')})")


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
        metrics = [get_metrics(r) for r in group]
        avg_tokens = sum(m["total"] for m in metrics) / n
        avg_cost = sum(m["cost"] for m in metrics) / n

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
        print("Usage: report.py <run_id> ... | --all | --latest | --compare <id1> <id2> | --all --group-by <field>",
              file=sys.stderr)
        sys.exit(1)

    group_by = None
    compare_ids = None
    run_ids = []
    latest = False

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--all":
            run_ids = sorted(os.listdir(BASE)) if BASE.exists() else []
        elif arg == "--latest":
            latest = True
            if BASE.exists():
                dirs = sorted(BASE.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
                run_ids = [d.name for d in dirs[:1]]
        elif arg == "--group-by":
            i += 1
            group_by = sys.argv[i] if i < len(sys.argv) else "config"
        elif arg == "--compare":
            compare_ids = (sys.argv[i + 1], sys.argv[i + 2])
            i += 2
        else:
            run_ids.append(arg)
        i += 1

    if compare_ids:
        a = load_run(compare_ids[0])
        b = load_run(compare_ids[1])
        if not a or not b:
            print("Could not load one or both runs.", file=sys.stderr)
            sys.exit(1)
        print_compare(a, b)
        return

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

    if group_by:
        print_group_by(runs, group_by)
    else:
        print_summary(runs)

    print_resource_summary(runs)


if __name__ == "__main__":
    main()
