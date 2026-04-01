#!/usr/bin/env python3
"""save_baseline.py — Save a run's metrics as the baseline for its target/config."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lib import PROJECT_DIR, RUN_ROOT, load_events, get_event, require_file, die

run_id = sys.argv[1] if len(sys.argv) > 1 else None
if not run_id:
    print("Usage: save_baseline.py <run_id>", file=sys.stderr); sys.exit(1)

events_file = RUN_ROOT / run_id / "events.jsonl"
require_file(events_file, f"No events for run {run_id}")
if events_file.stat().st_size == 0:
    die(f"Events file is empty for run {run_id}")

events = load_events(events_file)
data = {"run_id": run_id}

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
baselines_dir = PROJECT_DIR / "results" / "baselines"
baselines_dir.mkdir(parents=True, exist_ok=True)

outfile = baselines_dir / f"{target}_{config}.json"
outfile.write_text(json.dumps(data, indent=2))
print(f"Saved baseline: {outfile}")
print(f"  Target: {target}  Config: {config}  Result: {data.get('result', '?')}")
