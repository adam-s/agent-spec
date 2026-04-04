#!/usr/bin/env python3
"""behavior.py — Score agent behavior from event traces.

Analyzes events.jsonl to measure whether agents followed instructions,
made good tool choices, and were token-efficient.

Usage:
  behavior.py <run_id>                Score a single run
  behavior.py --all                   Score all runs with tool events
  behavior.py --all --group-by target Group scores by challenge
  behavior.py --compare <id1> <id2>   Side-by-side behavior comparison
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import PROJECT_DIR, load_events

RESULTS_DIRS = list(PROJECT_DIR.glob("evals/*/results"))

GIT_HISTORY_CMDS = ["git log", "git show", "git blame"]


def find_run(run_id):
    """Find events.jsonl for a run across all eval result dirs."""
    for d in RESULTS_DIRS:
        p = d / run_id / "events.jsonl"
        if p.exists():
            return p
    # Also check /tmp
    p = Path(f"/tmp/agent-spec/{run_id}/events.jsonl")
    if p.exists():
        return p
    return None


def extract_tools(events):
    """Extract tool use events from the event stream."""
    return [e for e in events if e.get("event") == "claude_tool_use"]


def score_run(run_id):
    """Score a single run's behavior. Returns dict of scores."""
    path = find_run(run_id)
    if not path:
        return None

    events = load_events(path)
    tools = extract_tools(events)

    if not tools:
        return None

    # Basic metadata
    run_start = next((e for e in events if e["event"] == "run_started"), None)
    score_evt = next((e for e in events if e["event"] == "score"), None)
    token_evt = next((e for e in events if e["event"] == "token_update"), None)

    target = run_start["data"].get("target", "?") if run_start else "?"
    result = score_evt["data"].get("result", "?") if score_evt else "?"
    tokens = token_evt["data"] if token_evt else {}

    # ── Behavior signals ─────────────────────────────────────────

    tool_counts = Counter(e["data"]["tool"] for e in tools)

    # 1. Git history exploration
    git_history = []
    for e in tools:
        if e["data"]["tool"] == "Bash":
            detail = e["data"].get("detail", "")
            if any(cmd in detail for cmd in GIT_HISTORY_CMDS):
                git_history.append(detail[:80])

    # 2. Reproduction before reading source
    #    Good: Write/Bash(python3) before Read
    #    Bad: Read source files before reproducing
    first_repro = None  # First Write or Bash(python3 repro)
    first_source_read = None  # First Read of source files
    for i, e in enumerate(tools):
        tool = e["data"]["tool"]
        detail = e["data"].get("detail", "")
        if tool == "Write" and first_repro is None:
            first_repro = i
        if tool == "Bash" and "python3" in detail and "pytest" not in detail and first_repro is None:
            first_repro = i
        if tool == "Read" and first_source_read is None:
            # Exclude reading test files or config
            first_source_read = i

    repro_first = (first_repro is not None and first_source_read is not None
                   and first_repro < first_source_read)

    # 3. Speculative exploration — grep/find/ls before reproduction
    exploration_before_repro = 0
    if first_repro is not None:
        for e in tools[:first_repro]:
            tool = e["data"]["tool"]
            detail = e["data"].get("detail", "")
            if tool in ("Grep", "Glob") or (tool == "Bash" and any(
                cmd in detail for cmd in ["find ", "ls ", "grep ", "rg "]
            )):
                exploration_before_repro += 1

    # 4. Edit cycles — how many Edit/Write attempts before passing tests
    edits = [e for e in tools if e["data"]["tool"] in ("Edit", "Write")]
    test_runs = [e for e in tools if e["data"]["tool"] == "Bash"
                 and "pytest" in e["data"].get("detail", "")]

    # 5. Total tool calls and distribution
    total_tools = len(tools)
    bash_pct = tool_counts.get("Bash", 0) / total_tools * 100 if total_tools else 0

    # 6. Files read — how many distinct Read targets
    reads = [e for e in tools if e["data"]["tool"] == "Read"]

    # ── Composite score ──────────────────────────────────────────

    violations = []
    if git_history:
        violations.append(f"git_history({len(git_history)})")
    if not repro_first and first_source_read is not None:
        violations.append("no_repro_first")
    if exploration_before_repro > 3:
        violations.append(f"speculative_exploration({exploration_before_repro})")

    return {
        "run_id": run_id,
        "target": target,
        "result": result,
        "output_tokens": tokens.get("output", 0),
        "total_tools": total_tools,
        "tool_counts": dict(tool_counts),
        "git_history_count": len(git_history),
        "git_history_cmds": git_history,
        "repro_first": repro_first,
        "exploration_before_repro": exploration_before_repro,
        "edit_count": len(edits),
        "test_runs": len(test_runs),
        "files_read": len(reads),
        "bash_pct": round(bash_pct, 1),
        "violations": violations,
    }


def print_scorecard(s):
    """Print a human-readable scorecard for one run."""
    if not s:
        print("No behavior data available")
        return

    v_str = ", ".join(s["violations"]) if s["violations"] else "none"
    marker = "✓" if s["result"] == "PASS" else "✗"

    print(f"\n{marker} {s['run_id']} — {s['target']} — {s['result']}")
    print(f"  Tokens: {s['output_tokens']:,}  |  Tools: {s['total_tools']}  |  Edits: {s['edit_count']}  |  Test runs: {s['test_runs']}")
    print(f"  Files read: {s['files_read']}  |  Bash: {s['bash_pct']}%")
    print(f"  Repro first: {'yes' if s['repro_first'] else 'NO'}  |  Exploration before repro: {s['exploration_before_repro']}")
    print(f"  Git history commands: {s['git_history_count']}")
    if s["git_history_cmds"]:
        for cmd in s["git_history_cmds"]:
            print(f"    - {cmd}")
    print(f"  Violations: {v_str}")


def print_summary_table(scores):
    """Print a summary table across runs."""
    print("\n| Run ID | Target | Result | Tokens | Tools | Git Hist | Repro 1st | Violations |")
    print("|--------|--------|--------|-------:|------:|---------:|-----------|------------|")
    for s in scores:
        repro = "yes" if s["repro_first"] else "NO"
        v_str = ", ".join(s["violations"]) if s["violations"] else "—"
        print(f"| {s['run_id']:8s} | {s['target'][:25]:25s} | {s['result']:4s} "
              f"| {s['output_tokens']:6d} | {s['total_tools']:5d} "
              f"| {s['git_history_count']:8d} | {repro:9s} | {v_str} |")


def print_group_summary(scores, key):
    """Group scores by a field and show aggregated behavior metrics."""
    groups = defaultdict(list)
    for s in scores:
        groups[s.get(key, "?")].append(s)

    print(f"\n## Behavior by {key}\n")
    print(f"| {key.title():30s} | Runs | Pass | Avg Tools | Avg Git | Repro 1st % | Avg Violations |")
    print(f"|{'-'*32}|-----:|-----:|----------:|--------:|------------:|---------------:|")

    for name in sorted(groups):
        g = groups[name]
        n = len(g)
        passes = sum(1 for s in g if s["result"] == "PASS")
        avg_tools = sum(s["total_tools"] for s in g) / n
        avg_git = sum(s["git_history_count"] for s in g) / n
        repro_pct = sum(1 for s in g if s["repro_first"]) / n * 100
        avg_violations = sum(len(s["violations"]) for s in g) / n
        print(f"| {name:30s} | {n:4d} | {passes:4d} | {avg_tools:9.1f} | {avg_git:7.1f} "
              f"| {repro_pct:10.0f}% | {avg_violations:14.1f} |")


def main():
    parser = argparse.ArgumentParser(description="Score agent behavior from event traces")
    parser.add_argument("run_ids", nargs="*", help="Run IDs to score")
    parser.add_argument("--all", action="store_true", help="Score all runs with tool events")
    parser.add_argument("--group-by", choices=["target", "result"], help="Group summary by field")
    parser.add_argument("--compare", nargs=2, metavar="ID", help="Compare two runs")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.compare:
        for rid in args.compare:
            s = score_run(rid)
            print_scorecard(s)
        return

    if args.all:
        scores = []
        for results_dir in RESULTS_DIRS:
            for run_dir in sorted(results_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                s = score_run(run_dir.name)
                if s:
                    scores.append(s)

        if not scores:
            print("No runs with behavior data found", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(scores, indent=2))
        elif args.group_by:
            print_group_summary(scores, args.group_by)
        else:
            print_summary_table(scores)
        return

    if args.run_ids:
        for rid in args.run_ids:
            s = score_run(rid)
            if args.json:
                print(json.dumps(s, indent=2))
            else:
                print_scorecard(s)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
