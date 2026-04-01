#!/usr/bin/env python3
"""score.py — Print the PASS/FAIL result for a run."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import RUN_ROOT, load_events, get_event, require_file


def main(args=None):
    parser = argparse.ArgumentParser(description="Print the PASS/FAIL result for a run")
    parser.add_argument("run_id", help="Run ID to check")
    args = args or parser.parse_args()

    events_file = RUN_ROOT / args.run_id / "events.jsonl"
    require_file(events_file, f"No events for run {args.run_id}")

    events = load_events(events_file)
    score = get_event(events, "score")
    print(score["data"]["result"] if score else "N/A")


if __name__ == "__main__":
    main()
