#!/usr/bin/env python3
"""report.py — Unified reporting for agent-spec runs.

Usage:
  report.py --all                          Show all runs
  report.py --latest                       Show most recent run
  report.py <run_id> ...                   Show specific runs
  report.py --all --group-by config        Group by config with deltas
  report.py --all --group-by model         Group by model with deltas
  report.py --all --group-by target        Group by target with deltas
  report.py --compare <id1> <id2>          Side-by-side two-run diff
  report.py --session <session_id>         Iterate session report grouped by depth
  report.py --score <run_id>               Print PASS/FAIL result
  report.py --tokens <run_id>              Print token metrics for a run
  report.py --tokens --session <id>        Session token rollup by depth
  report.py --baseline save <run_id>       Save run metrics as baseline
  report.py --baseline check <run_id>      Compare run against saved baseline
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (
    PROJECT_DIR, RUN_ROOT, REGRESSION_COST_THRESHOLD, REGRESSION_TOKEN_THRESHOLD,
    load_events, get_event, find_session_runs, require_file, die,
)


def load_run(run_id):
    """Load events from a single run."""
    log = RUN_ROOT / run_id / "events.jsonl"
    if not log.exists():
        return None

    events = load_events(log)
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

    valid = [s for s in summaries if s["name"] != "?"]
    baseline = valid[0] if valid else (summaries[0] if summaries else None)

    for s in summaries:
        dur_s = f"{s['avg_dur'] / 1000:.0f}s"
        if baseline and s != baseline:
            delta_cost = s["avg_cost"] - baseline["avg_cost"]
            delta_tokens = s["avg_tokens"] - baseline["avg_tokens"]
            dc = f"{delta_cost:+.3f}"
            dt = f"{delta_tokens:+.0f}"
        else:
            dc = "\u2014"
            dt = "\u2014"

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
        pct = f"{(delta / va * 100):+.1f}%" if va else "\u2014"
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


# ── Score (absorbed from score.py) ─────────────────────────────

def print_score(run_id: str):
    """Print the PASS/FAIL result for a run."""
    events_file = RUN_ROOT / run_id / "events.jsonl"
    require_file(events_file, f"No events for run {run_id}")
    events = load_events(events_file)
    score = get_event(events, "score")
    print(score["data"]["result"] if score else "N/A")


# ── Tokens (absorbed from tokens.py) ──────────────────────────

def print_tokens_single(run_id: str):
    """Print token metrics for a single run."""
    events_file = RUN_ROOT / run_id / "events.jsonl"
    require_file(events_file, f"No events for run {run_id}")
    events = load_events(events_file)
    token = get_event(events, "token_update")
    if token:
        d = token["data"]
        print(f"Input: {d.get('input', 0)}  Output: {d.get('output', 0)}  Cost: ${d.get('cost_usd', 0)}")
    else:
        print("No token data")


def print_tokens_session(session_id: str):
    """Print token rollup for an iterate session, grouped by depth."""
    depth_runs = find_session_runs(session_id)
    if not depth_runs:
        print(f"No runs found for session {session_id}", file=sys.stderr)
        sys.exit(1)

    total_input = total_output = total_cost = 0

    print(f"\u2500\u2500 Session {session_id} token rollup \u2500\u2500\n")
    print(f"  {'Depth':>5}  {'Runs':>4}  {'Input':>8}  {'Output':>8}  {'Cost':>8}")
    print(f"  {'\u2500'*5}  {'\u2500'*4}  {'\u2500'*8}  {'\u2500'*8}  {'\u2500'*8}")

    for depth in sorted(depth_runs.keys()):
        run_ids = depth_runs[depth]
        d_input = d_output = d_cost = 0
        for rid in run_ids:
            events_file = RUN_ROOT / rid / "events.jsonl"
            if not events_file.exists():
                continue
            events = load_events(events_file)
            tok = get_event(events, "token_update")
            if tok:
                d = tok["data"]
                d_input += d.get("input", 0)
                d_output += d.get("output", 0)
                d_cost += d.get("cost_usd", 0)
        total_input += d_input
        total_output += d_output
        total_cost += d_cost
        print(f"  {depth:>5}  {len(run_ids):>4}  {d_input:>8}  {d_output:>8}  ${d_cost:>7.3f}")

    print(f"  {'\u2500'*5}  {'\u2500'*4}  {'\u2500'*8}  {'\u2500'*8}  {'\u2500'*8}")
    total_runs = sum(len(v) for v in depth_runs.values())
    print(f"  {'TOTAL':>5}  {total_runs:>4}  {total_input:>8}  {total_output:>8}  ${total_cost:>7.3f}")


# ── Session report ─────────────────────────────────────────────

def print_session_report(session_id: str):
    """Print iterate session report grouped by depth."""
    depth_runs = find_session_runs(session_id)
    if not depth_runs:
        print(f"No runs found for session {session_id}", file=sys.stderr)
        sys.exit(1)

    print(f"# Iterate Session: {session_id}\n")

    for depth in sorted(depth_runs.keys()):
        run_ids = depth_runs[depth]
        runs = [r for r in (load_run(rid) for rid in run_ids) if r]
        if not runs:
            continue
        print(f"\n## Depth {depth} ({len(runs)} instances)\n")
        print_table(runs)

    all_ids = [rid for ids in depth_runs.values() for rid in ids]
    all_runs = [r for r in (load_run(rid) for rid in all_ids) if r]
    if all_runs:
        total_cost = sum(get_metrics(r)["cost"] for r in all_runs)
        total_passes = sum(1 for r in all_runs if r.get("result") == "PASS")
        print(f"\n## Session Summary\n")
        print(f"  Depths: {len(depth_runs)}")
        print(f"  Total runs: {len(all_runs)}")
        print(f"  Total passes: {total_passes}/{len(all_runs)}")
        print(f"  Total cost: ${total_cost:.3f}")


# ── Baseline (absorbed from save_baseline.py / check_regression.py) ──

def baseline_save(run_id: str):
    """Save a run's metrics as the baseline for its target/config."""
    events_file = RUN_ROOT / run_id / "events.jsonl"
    require_file(events_file, f"No events for run {run_id}")
    if events_file.stat().st_size == 0:
        die(f"Events file is empty for run {run_id}")

    events = load_events(events_file)
    data = {
        "run_id": run_id,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    started = get_event(events, "agent_started")
    if started:
        data["target"] = started["data"].get("target", "?")
        data["config"] = started["data"].get("config", "?")
        data["model"] = started["data"].get("model", "?")

    token = get_event(events, "token_update")
    if token:
        data["tokens"] = token["data"]

    score = get_event(events, "score")
    if score:
        data["result"] = score["data"].get("result", "N/A")

    complete = get_event(events, "agent_complete")
    if complete:
        data["duration_ms"] = complete["data"].get("duration_ms", 0)

    target = data.get("target", "unknown")
    config = data.get("config", "unknown")
    eval_name = started["data"].get("eval", "") if started else ""
    if eval_name:
        baselines_dir = PROJECT_DIR / "evals" / eval_name / "results" / "baselines"
    else:
        baselines_dir = PROJECT_DIR / "results" / "baselines"
    baselines_dir.mkdir(parents=True, exist_ok=True)

    outfile = baselines_dir / f"{target}_{config}.json"
    outfile.write_text(json.dumps(data, indent=2))
    print(f"Saved baseline: {outfile}")
    print(f"  Target: {target}  Config: {config}  Result: {data.get('result', '?')}")


def baseline_check(run_id: str):
    """Compare a run against its saved baseline."""
    events_file = RUN_ROOT / run_id / "events.jsonl"
    require_file(events_file, f"No events for run {run_id}")

    events = load_events(events_file)
    started = get_event(events, "agent_started")
    target = started["data"].get("target", "unknown") if started else "unknown"
    config = started["data"].get("config", "unknown") if started else "unknown"
    c_model = started["data"].get("model", "?") if started else "?"

    eval_name = started["data"].get("eval", "") if started else ""
    if eval_name:
        baseline_path = PROJECT_DIR / "evals" / eval_name / "results" / "baselines" / f"{target}_{config}.json"
    else:
        baseline_path = PROJECT_DIR / "results" / "baselines" / f"{target}_{config}.json"
    if not baseline_path.exists():
        print(f"NO BASELINE for {target}/{config} \u2014 run: report.py --baseline save <run_id>")
        sys.exit(0)

    try:
        baseline = json.loads(baseline_path.read_text())
    except (json.JSONDecodeError, ValueError) as e:
        print(f"CORRUPT BASELINE at {baseline_path}: {e}")
        sys.exit(1)

    # Model mismatch warning
    b_model = baseline.get("model", "?")
    if b_model != "?" and c_model != "?" and b_model != c_model:
        print(f"  WARNING: Model mismatch \u2014 baseline used {b_model}, current used {c_model}")

    # Staleness warning
    saved_at = baseline.get("saved_at")
    if saved_at:
        print(f"  Baseline saved: {saved_at[:10]}")

    regressions = []
    cost_thresh = REGRESSION_COST_THRESHOLD / 100
    token_thresh = REGRESSION_TOKEN_THRESHOLD / 100

    # Result
    b_result = baseline.get("result", "N/A")
    score = get_event(events, "score")
    c_result = score["data"].get("result", "N/A") if score else "N/A"
    if b_result == "PASS" and c_result != "PASS":
        regressions.append(f"Result: {b_result} -> {c_result}")

    # Cost
    token = get_event(events, "token_update")
    b_cost = baseline.get("tokens", {}).get("cost_usd", 0)
    c_cost = token["data"].get("cost_usd", 0) if token else 0
    if b_cost > 0 and c_cost > b_cost * (1 + cost_thresh):
        regressions.append(f"Cost: ${b_cost:.3f} -> ${c_cost:.3f} (+{(c_cost/b_cost - 1)*100:.0f}%)")

    # Tokens
    b_tokens = baseline.get("tokens", {}).get("input", 0) + baseline.get("tokens", {}).get("output", 0)
    c_tokens = (token["data"].get("input", 0) + token["data"].get("output", 0)) if token else 0
    if b_tokens > 0 and c_tokens > b_tokens * (1 + token_thresh):
        regressions.append(f"Tokens: {b_tokens} -> {c_tokens} (+{(c_tokens/b_tokens - 1)*100:.0f}%)")

    print(f"  Baseline: {target}/{config} (run {baseline.get('run_id', '?')})")
    print(f"  Current:  {target}/{config} (run {run_id})")

    if regressions:
        print("\nREGRESSION")
        for r in regressions:
            print(f"  * {r}")
        sys.exit(1)
    else:
        print("\nOK \u2014 no regression detected")


# ── CLI ────────────────────────────────────────────────────────

def main(args=None):
    parser = argparse.ArgumentParser(
        prog="report",
        description="Unified reporting for agent-spec runs",
    )
    parser.add_argument("run_ids", nargs="*", help="Run IDs to report on")
    parser.add_argument("--all", action="store_true", dest="show_all", help="Show all runs")
    parser.add_argument("--latest", action="store_true", help="Show most recent run")
    parser.add_argument("--group-by", choices=["config", "model", "target"], help="Group results by field")
    parser.add_argument("--compare", nargs=2, metavar="RUN_ID", help="Side-by-side two-run comparison")
    parser.add_argument("--session", metavar="SESSION_ID", help="Iterate session report by depth")
    parser.add_argument("--score", metavar="RUN_ID", help="Print PASS/FAIL result for a run")
    parser.add_argument("--tokens", metavar="RUN_ID", nargs="?", const="__session__",
                        help="Print token metrics (run_id, or with --session for rollup)")
    parser.add_argument("--baseline", nargs=2, metavar=("ACTION", "RUN_ID"),
                        help="Baseline operations: save <run_id> or check <run_id>")
    args = args or parser.parse_args()

    # Dispatch to specialized modes
    if args.score:
        print_score(args.score)
        return

    if args.tokens:
        if args.tokens == "__session__" and args.session:
            print_tokens_session(args.session)
        elif args.tokens != "__session__":
            print_tokens_single(args.tokens)
        else:
            print("Usage: --tokens <run_id> or --tokens --session <session_id>", file=sys.stderr)
            sys.exit(1)
        return

    if args.baseline:
        action, run_id = args.baseline
        if action == "save":
            baseline_save(run_id)
        elif action == "check":
            baseline_check(run_id)
        else:
            print(f"Unknown baseline action: {action}. Use 'save' or 'check'.", file=sys.stderr)
            sys.exit(1)
        return

    if args.session:
        print_session_report(args.session)
        return

    if args.compare:
        a = load_run(args.compare[0])
        b = load_run(args.compare[1])
        if not a or not b:
            print("Could not load one or both runs.", file=sys.stderr)
            sys.exit(1)
        print_compare(a, b)
        return

    run_ids = list(args.run_ids)
    if args.show_all:
        run_ids = sorted(os.listdir(RUN_ROOT)) if RUN_ROOT.exists() else []
    elif args.latest:
        if RUN_ROOT.exists():
            dirs = sorted(RUN_ROOT.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            run_ids = [d.name for d in dirs[:1]]

    runs = []
    for rid in run_ids:
        r = load_run(rid)
        if r:
            runs.append(r)

    if not runs:
        if not args.run_ids and not args.show_all and not args.latest:
            parser.print_help()
        else:
            print("No runs found.", file=sys.stderr)
        sys.exit(1)

    print(f"# agent-spec Report \u2014 {len(runs)} run(s)\n")
    print_table(runs)

    if args.group_by:
        print_group_by(runs, args.group_by)
    else:
        print_summary(runs)

    print_resource_summary(runs)


if __name__ == "__main__":
    main()
