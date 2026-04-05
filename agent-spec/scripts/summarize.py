#!/usr/bin/env python3
"""summarize.py — Generate a digestible results summary for an eval.

Prints a formatted comparison to the terminal and writes RESULTS.md
to the eval directory.

Usage:
  summarize.py <eval_name>                   Summarize all runs for an eval
  summarize.py <eval_name> --filter-eval     Only include runs tagged with this eval
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import PROJECT_DIR, RUN_ROOT, load_events, get_event


def load_eval_runs(eval_name, filter_eval=False):
    """Load all runs that belong to an eval, from both /tmp and archived results."""
    runs = []
    seen = set()

    def process_run(run_id, events_path):
        if run_id in seen:
            return
        if not events_path.exists():
            return
        events = load_events(events_path)
        run = {"run_id": run_id, "events": events}

        for e in events:
            if e["event"] == "run_started":
                run.setdefault("target", e["data"].get("target", "?"))
                run.setdefault("config", e["data"].get("config", "?"))
                run.setdefault("model", e["data"].get("model", "?"))
                run["eval"] = e["data"].get("eval", "")
            elif e["event"] == "agent_started":
                run.setdefault("target", e["data"].get("target", "?"))
                run.setdefault("config", e["data"].get("config", "?"))
                run.setdefault("model", e["data"].get("model", "?"))
            elif e["event"] == "token_update":
                run["tokens"] = e["data"]
            elif e["event"] == "score":
                run["result"] = e["data"].get("result", "N/A")
            elif e["event"] == "agent_complete":
                run["duration_ms"] = e["data"].get("duration_ms", 0)
            elif e["event"] == "agent_error":
                run["result"] = "ERROR"
                run["duration_ms"] = e["data"].get("duration_ms", 0)

        if filter_eval and run.get("eval") != eval_name:
            return

        seen.add(run_id)
        runs.append(run)

    # Archived results in eval directory
    results_dir = PROJECT_DIR / "evals" / eval_name / "results"
    if results_dir.exists():
        for d in results_dir.iterdir():
            if d.is_dir() and (d / "events.jsonl").exists():
                process_run(d.name, d / "events.jsonl")

    # Live results in /tmp
    if RUN_ROOT.exists():
        for d in RUN_ROOT.iterdir():
            if d.is_dir() and (d / "events.jsonl").exists():
                process_run(d.name, d / "events.jsonl")

    return runs


def get_metrics(run):
    """Extract metrics from a run."""
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
        "cache_read": t.get("cache_read", 0),
        "cache_create": t.get("cache_create", 0),
    }


def stddev(values):
    """Standard deviation of a list of numbers."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def build_summary(eval_name, runs):
    """Build structured summary data from runs."""
    eval_dir = PROJECT_DIR / "evals" / eval_name

    # Load eval metadata
    eval_md = eval_dir / "EVAL.md"
    description = ""
    model = "?"
    if eval_md.exists():
        text = eval_md.read_text()
        for line in text.splitlines():
            if line.startswith("description:"):
                description = line.split(":", 1)[1].strip()
            if line.startswith("model:"):
                model = line.split(":", 1)[1].strip()

    # Discover configs and challenges
    configs = sorted([d.name for d in (eval_dir / "configs").iterdir() if d.is_dir()]) if (eval_dir / "configs").exists() else []
    challenges = sorted([d.name for d in (eval_dir / "challenges").iterdir() if d.is_dir()]) if (eval_dir / "challenges").exists() else []

    # Group runs by config
    by_config = defaultdict(list)
    for r in runs:
        cfg = r.get("config", "?")
        if cfg in configs or not configs:
            by_config[cfg].append(r)

    # Filter to only runs matching this eval's configs
    if configs:
        by_config = {k: v for k, v in by_config.items() if k in configs}

    # Build per-config stats
    config_stats = []
    for cfg in configs:
        group = by_config.get(cfg, [])
        if not group:
            continue
        metrics = [get_metrics(r) for r in group]
        n = len(group)
        passes = sum(1 for m in metrics if m["result"] == "PASS")
        totals = [m["total"] for m in metrics]
        costs = [m["cost"] for m in metrics]
        durations = [m["duration_ms"] for m in metrics]
        turns_list = [m["turns"] for m in metrics]
        inputs = [m["input"] for m in metrics]
        outputs = [m["output"] for m in metrics]

        config_stats.append({
            "config": cfg,
            "runs": n,
            "passes": passes,
            "pass_rate": passes / n if n else 0,
            "avg_tokens": sum(totals) / n,
            "std_tokens": stddev(totals),
            "min_tokens": min(totals),
            "max_tokens": max(totals),
            "avg_cost": sum(costs) / n,
            "std_cost": stddev(costs),
            "avg_duration_s": sum(durations) / n / 1000,
            "avg_turns": sum(turns_list) / n,
            "avg_input": sum(inputs) / n,
            "avg_output": sum(outputs) / n,
        })

    # Compute deltas from first config (baseline)
    baseline = config_stats[0] if config_stats else None
    for s in config_stats:
        if baseline and s != baseline:
            s["delta_tokens"] = s["avg_tokens"] - baseline["avg_tokens"]
            s["delta_pct"] = ((s["avg_tokens"] - baseline["avg_tokens"]) / baseline["avg_tokens"] * 100) if baseline["avg_tokens"] else 0
            s["delta_cost"] = s["avg_cost"] - baseline["avg_cost"]
        else:
            s["delta_tokens"] = 0
            s["delta_pct"] = 0
            s["delta_cost"] = 0

    # Per-challenge breakdown
    challenge_stats = []
    for challenge in challenges:
        for cfg in configs:
            group = [r for r in by_config.get(cfg, []) if r.get("target") == challenge]
            if not group:
                continue
            metrics = [get_metrics(r) for r in group]
            n = len(group)
            passes = sum(1 for m in metrics if m["result"] == "PASS")
            totals = [m["total"] for m in metrics]
            costs = [m["cost"] for m in metrics]
            challenge_stats.append({
                "challenge": challenge,
                "config": cfg,
                "runs": n,
                "passes": passes,
                "avg_tokens": sum(totals) / n,
                "std_tokens": stddev(totals),
                "avg_cost": sum(costs) / n,
            })

    return {
        "eval_name": eval_name,
        "description": description,
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat()[:19] + "Z",
        "configs": configs,
        "challenges": challenges,
        "total_runs": len(runs),
        "config_stats": config_stats,
        "challenge_stats": challenge_stats,
    }


def format_terminal(summary):
    """Format summary for terminal display."""
    lines = []
    lines.append("")
    lines.append(f"  {summary['eval_name']} — {summary['description']}")
    lines.append(f"  Model: {summary['model']}  |  Runs: {summary['total_runs']}  |  Generated: {summary['generated_at']}")
    lines.append("")

    # Main comparison table
    lines.append("  Config Comparison")
    lines.append(f"  {'Config':<16} {'Runs':>4} {'Pass':>6} {'Avg Tok':>9} {'Std':>7} {'Avg Cost':>9} {'Avg Time':>9} {'Delta':>9}")
    lines.append(f"  {'─'*16} {'─'*4} {'─'*6} {'─'*9} {'─'*7} {'─'*9} {'─'*9} {'─'*9}")

    for s in summary["config_stats"]:
        pass_str = f"{s['passes']}/{s['runs']}"
        delta_str = "baseline" if s["delta_tokens"] == 0 and s == summary["config_stats"][0] else f"{s['delta_pct']:+.0f}%"
        dur_str = f"{s['avg_duration_s']:.0f}s"
        lines.append(
            f"  {s['config']:<16} {s['runs']:>4} {pass_str:>6} {s['avg_tokens']:>9.0f} "
            f"{s['std_tokens']:>7.0f} ${s['avg_cost']:>8.3f} {dur_str:>9} {delta_str:>9}"
        )

    lines.append("")

    # Per-challenge breakdown
    lines.append("  Per-Challenge Breakdown")
    lines.append(f"  {'Challenge':<26} {'Config':<16} {'Runs':>4} {'Pass':>4} {'Avg Tok':>9} {'Avg Cost':>9}")
    lines.append(f"  {'─'*26} {'─'*16} {'─'*4} {'─'*4} {'─'*9} {'─'*9}")

    for cs in summary["challenge_stats"]:
        lines.append(
            f"  {cs['challenge']:<26} {cs['config']:<16} {cs['runs']:>4} {cs['passes']:>4} "
            f"{cs['avg_tokens']:>9.0f} ${cs['avg_cost']:>8.3f}"
        )

    lines.append("")

    return "\n".join(lines)


def format_markdown(summary):
    """Format summary as a shareable markdown document."""
    lines = []
    lines.append(f"# {summary['eval_name']} Results\n")
    lines.append(f"> {summary['description']}\n")
    lines.append(f"Model: `{summary['model']}` | Runs: {summary['total_runs']} | Generated: {summary['generated_at']}\n")

    # Config comparison
    lines.append("## Config Comparison\n")
    lines.append("| Config | Runs | Pass Rate | Avg Tokens | Std Dev | Min | Max | Avg Cost | Avg Time | vs Baseline |")
    lines.append("|--------|-----:|----------:|-----------:|--------:|----:|----:|---------:|---------:|------------:|")

    for s in summary["config_stats"]:
        pass_rate = f"{s['pass_rate']*100:.0f}%"
        delta_str = "baseline" if s["delta_tokens"] == 0 and s == summary["config_stats"][0] else f"{s['delta_pct']:+.0f}%"
        dur_str = f"{s['avg_duration_s']:.0f}s"
        lines.append(
            f"| {s['config']} | {s['runs']} | {pass_rate} | "
            f"{s['avg_tokens']:.0f} | {s['std_tokens']:.0f} | "
            f"{s['min_tokens']} | {s['max_tokens']} | "
            f"${s['avg_cost']:.3f} | {dur_str} | {delta_str} |"
        )

    # Token breakdown
    lines.append("\n## Token Breakdown\n")
    lines.append("| Config | Avg Input | Avg Output | Avg Turns | Cost/Turn |")
    lines.append("|--------|----------:|-----------:|----------:|----------:|")

    for s in summary["config_stats"]:
        cost_per_turn = s["avg_cost"] / s["avg_turns"] if s["avg_turns"] else 0
        lines.append(
            f"| {s['config']} | {s['avg_input']:.0f} | {s['avg_output']:.0f} | "
            f"{s['avg_turns']:.1f} | ${cost_per_turn:.4f} |"
        )

    # Per-challenge breakdown
    lines.append("\n## Per-Challenge Breakdown\n")
    lines.append("| Challenge | Config | Runs | Pass | Avg Tokens | Std Dev | Avg Cost |")
    lines.append("|-----------|--------|-----:|-----:|-----------:|--------:|---------:|")

    for cs in summary["challenge_stats"]:
        lines.append(
            f"| {cs['challenge']} | {cs['config']} | {cs['runs']} | "
            f"{cs['passes']}/{cs['runs']} | {cs['avg_tokens']:.0f} | "
            f"{cs['std_tokens']:.0f} | ${cs['avg_cost']:.3f} |"
        )

    # Interpretation guide
    lines.append("\n## How to Read This\n")
    lines.append("- **Avg Tokens**: Mean input + output tokens across all runs (lower = more efficient)")
    lines.append("- **Std Dev**: Run-to-run variance. High std dev means the config's efficiency is inconsistent")
    lines.append("- **vs Baseline**: Percentage change from the first config. Negative = fewer tokens")
    lines.append("- **Pass Rate**: Configs that cause failures waste tokens. 100% pass rate is expected for these challenges")
    lines.append("- **Cost/Turn**: Helps distinguish \"fewer turns\" from \"less output per turn\" as the efficiency mechanism")
    lines.append("")

    # Methodology note
    lines.append("## Methodology\n")
    lines.append("Each config is a `.claude/` directory containing a CLAUDE.md with different instruction strategies. ")
    lines.append("The same challenges run against each config in isolated sandboxes. ")
    lines.append("Only the CLAUDE.md differs between runs -- same model, same prompts, same test files. ")
    lines.append("Results are deterministic: `verify.sh` runs the test suite and outputs PASS or FAIL.\n")
    lines.append(f"Generated by agent-spec summarize.py")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a results summary for an eval"
    )
    parser.add_argument("eval_name", help="Name of the eval to summarize")
    parser.add_argument("--filter-eval", action="store_true",
                        help="Only include runs tagged with this eval name")
    parser.add_argument("--no-write", action="store_true",
                        help="Print to terminal only, don't write RESULTS.md")
    args = parser.parse_args()

    eval_dir = PROJECT_DIR / "evals" / args.eval_name
    if not eval_dir.exists():
        print(f"Eval not found: {args.eval_name}", file=sys.stderr)
        sys.exit(1)

    runs = load_eval_runs(args.eval_name, filter_eval=args.filter_eval)
    if not runs:
        print(f"No runs found for eval: {args.eval_name}", file=sys.stderr)
        sys.exit(1)

    summary = build_summary(args.eval_name, runs)

    # Terminal output
    print(format_terminal(summary))

    # Write markdown
    if not args.no_write:
        md_path = eval_dir / "RESULTS.md"
        md_path.write_text(format_markdown(summary))
        print(f"  Written to: {md_path}")


if __name__ == "__main__":
    main()
