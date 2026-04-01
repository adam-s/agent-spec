#!/usr/bin/env python3
"""tokens.py — Print token metrics for a run or iterate session.

Usage:
  tokens.py <run_id>                   Single run tokens
  tokens.py --session <session_id>     Rollup across all runs in an iterate session
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lib import RUN_ROOT, load_events, get_event, require_file


def print_single(run_id: str):
    events_file = RUN_ROOT / run_id / "events.jsonl"
    require_file(events_file, f"No events for run {run_id}")
    events = load_events(events_file)
    token = get_event(events, "token_update")
    if token:
        d = token["data"]
        print(f"Input: {d.get('input', 0)}  Output: {d.get('output', 0)}  Cost: ${d.get('cost_usd', 0)}")
    else:
        print("No token data")


def find_session_runs(session_id: str) -> dict[int, list[str]]:
    """Find all run_ids belonging to a session, grouped by iteration depth."""
    depth_runs: dict[int, list[str]] = {}
    if not RUN_ROOT.exists():
        return depth_runs

    for run_dir in RUN_ROOT.iterdir():
        events_file = run_dir / "events.jsonl"
        if not events_file.exists():
            continue
        events = load_events(events_file)
        for e in events:
            if e.get("event") == "iteration_started" and e.get("data", {}).get("session_id", "").startswith(session_id):
                depth = e["data"].get("depth", 0)
                # This is the parallel orchestrator run — find child run_ids
                for e2 in events:
                    if e2.get("event") == "instance_complete":
                        child_id = e2["data"].get("run_id")
                        if child_id:
                            depth_runs.setdefault(depth, []).append(child_id)
                break
    return depth_runs


def print_session(session_id: str):
    depth_runs = find_session_runs(session_id)
    if not depth_runs:
        print(f"No runs found for session {session_id}", file=sys.stderr)
        sys.exit(1)

    total_input = total_output = total_cost = 0

    print(f"── Session {session_id} token rollup ──\n")
    print(f"  {'Depth':>5}  {'Runs':>4}  {'Input':>8}  {'Output':>8}  {'Cost':>8}")
    print(f"  {'─'*5}  {'─'*4}  {'─'*8}  {'─'*8}  {'─'*8}")

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

    print(f"  {'─'*5}  {'─'*4}  {'─'*8}  {'─'*8}  {'─'*8}")
    total_runs = sum(len(v) for v in depth_runs.values())
    print(f"  {'TOTAL':>5}  {total_runs:>4}  {total_input:>8}  {total_output:>8}  ${total_cost:>7.3f}")


def main():
    if len(sys.argv) < 2:
        print("Usage: tokens.py <run_id> | --session <session_id>", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--session":
        if len(sys.argv) < 3:
            print("Usage: tokens.py --session <session_id>", file=sys.stderr)
            sys.exit(1)
        print_session(sys.argv[2])
    else:
        print_single(sys.argv[1])


if __name__ == "__main__":
    main()
