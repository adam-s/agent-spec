#!/usr/bin/env python3
"""score.py — Print the PASS/FAIL result for a run."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lib import RUN_ROOT, load_events, get_event, require_file

run_id = sys.argv[1] if len(sys.argv) > 1 else None
if not run_id:
    print("Usage: score.py <run_id>", file=sys.stderr); sys.exit(1)

events_file = RUN_ROOT / run_id / "events.jsonl"
require_file(events_file, f"No events for run {run_id}")

events = load_events(events_file)
score = get_event(events, "score")
print(score["data"]["result"] if score else "N/A")
