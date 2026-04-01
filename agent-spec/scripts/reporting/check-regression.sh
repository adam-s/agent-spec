#!/usr/bin/env bash
# check-regression.sh — Compare a run against its saved baseline.
#
# Usage: scripts/reporting/check-regression.sh <run_id>
#
# Looks up results/baselines/{target}_{config}.json and compares.
# Prints REGRESSION or OK.
#
# Regression criteria:
#   - Result changed from PASS to FAIL
#   - Cost increased by more than 50%
#   - Token count increased by more than 50%
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

RUN_ID="${1:?Usage: check-regression.sh <run_id>}"
RUN_DIR="/tmp/agent-spec/$RUN_ID"
EVENTS="$RUN_DIR/events.jsonl"

if [[ ! -f "$EVENTS" ]]; then
  echo "No events found for run $RUN_ID" >&2
  exit 1
fi

EVENTS_PATH="$EVENTS" RUN_ID="$RUN_ID" BASELINES_DIR="$PROJECT_DIR/results/baselines" python3 << 'PYEOF'
import json, os, sys

def load_events(path):
    data = {}
    for line in open(path):
        try:
            e = json.loads(line)
        except:
            continue
        ev = e.get("event", "")
        if ev == "agent_started":
            data["target"] = e["data"].get("target", "?")
            data["config"] = e["data"].get("config", "?")
            data["model"] = e["data"].get("model", "?")
        elif ev == "token_update":
            data["tokens"] = e["data"]
        elif ev == "score":
            data["result"] = e["data"].get("result", "N/A")
    return data

current = load_events(os.environ["EVENTS_PATH"])
target = current.get("target", "unknown")
config = current.get("config", "unknown")

baseline_path = os.path.join(os.environ["BASELINES_DIR"], f"{target}_{config}.json")
if not os.path.exists(baseline_path):
    print(f"NO BASELINE for {target}/{config} — run save-baseline.sh first")
    sys.exit(0)

try:
    baseline = json.load(open(baseline_path))
except (json.JSONDecodeError, ValueError) as e:
    print(f"CORRUPT BASELINE at {baseline_path}: {e}")
    sys.exit(1)

# Warn on model mismatch
b_model = baseline.get("model", "?")
c_model = current.get("model", "?")  # not currently stored in events, future-proofing
if b_model != "?" and c_model != "?" and b_model != c_model:
    print(f"  WARNING: Model mismatch — baseline used {b_model}, current used {c_model}")

regressions = []

# Check result
b_result = baseline.get("result", "N/A")
c_result = current.get("result", "N/A")
if b_result == "PASS" and c_result != "PASS":
    regressions.append(f"Result: {b_result} → {c_result}")

# Check cost
b_cost = baseline.get("tokens", {}).get("cost_usd", 0)
c_cost = current.get("tokens", {}).get("cost_usd", 0)
if b_cost > 0 and c_cost > b_cost * 1.5:
    regressions.append(f"Cost: ${b_cost:.3f} → ${c_cost:.3f} (+{(c_cost/b_cost - 1)*100:.0f}%)")

# Check tokens
b_tokens = baseline.get("tokens", {}).get("input", 0) + baseline.get("tokens", {}).get("output", 0)
c_tokens = current.get("tokens", {}).get("input", 0) + current.get("tokens", {}).get("output", 0)
if b_tokens > 0 and c_tokens > b_tokens * 1.5:
    regressions.append(f"Tokens: {b_tokens} → {c_tokens} (+{(c_tokens/b_tokens - 1)*100:.0f}%)")

print(f"  Baseline: {target}/{config} (run {baseline.get('run_id', '?')})")
print(f"  Current:  {target}/{config} (run {os.environ['RUN_ID']})")

if regressions:
    print(f"\nREGRESSION")
    for r in regressions:
        print(f"  ✗ {r}")
    sys.exit(1)
else:
    print(f"\nOK — no regression detected")
PYEOF
