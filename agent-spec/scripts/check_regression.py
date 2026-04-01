#!/usr/bin/env python3
"""check_regression.py — Compare a run against its saved baseline."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lib import (
    PROJECT_DIR, RUN_ROOT, REGRESSION_COST_THRESHOLD, REGRESSION_TOKEN_THRESHOLD,
    load_events, get_event, require_file,
)

run_id = sys.argv[1] if len(sys.argv) > 1 else None
if not run_id:
    print("Usage: check_regression.py <run_id>", file=sys.stderr); sys.exit(1)

events_file = RUN_ROOT / run_id / "events.jsonl"
require_file(events_file, f"No events for run {run_id}")

events = load_events(events_file)
started = get_event(events, "agent_started")
target = started["data"].get("target", "unknown") if started else "unknown"
config = started["data"].get("config", "unknown") if started else "unknown"
c_model = started["data"].get("model", "?") if started else "?"

baseline_path = PROJECT_DIR / "results" / "baselines" / f"{target}_{config}.json"
if not baseline_path.exists():
    print(f"NO BASELINE for {target}/{config} — run save_baseline.py first")
    sys.exit(0)

try:
    baseline = json.loads(baseline_path.read_text())
except (json.JSONDecodeError, ValueError) as e:
    print(f"CORRUPT BASELINE at {baseline_path}: {e}")
    sys.exit(1)

# Model mismatch warning
b_model = baseline.get("model", "?")
if b_model != "?" and c_model != "?" and b_model != c_model:
    print(f"  WARNING: Model mismatch — baseline used {b_model}, current used {c_model}")

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
    print("\nOK — no regression detected")
