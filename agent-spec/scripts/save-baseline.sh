#!/usr/bin/env bash
# save-baseline.sh — Save a run's metrics as the baseline for its target/config.
#
# Usage: scripts/save-baseline.sh <run_id>
# Saves to results/baselines/{target}_{config}.json
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

RUN_ID="${1:?Usage: save-baseline.sh <run_id>}"
EVENTS="$RUN_ROOT/$RUN_ID/events.jsonl"
require_file "$EVENTS" "No events for run $RUN_ID"

if [[ ! -s "$EVENTS" ]]; then
  die "Events file is empty for run $RUN_ID"
fi

BASELINE=$(EVENTS_PATH="$EVENTS" RUN_ID="$RUN_ID" python3 << 'PYEOF'
import json, os, sys

events = []
for line in open(os.environ["EVENTS_PATH"]):
    try:
        events.append(json.loads(line))
    except:
        continue

data = {"run_id": os.environ["RUN_ID"]}
for e in events:
    ev = e.get("event", "")
    if ev == "agent_started":
        data["target"] = e["data"].get("target", "?")
        data["config"] = e["data"].get("config", "?")
        data["model"] = e["data"].get("model", "?")
    elif ev == "token_update":
        data["tokens"] = e["data"]
    elif ev == "score":
        data["result"] = e["data"].get("result", "N/A")
    elif ev == "agent_complete":
        data["duration_ms"] = e["data"].get("duration_ms", 0)

print(json.dumps(data, indent=2))
PYEOF
)

TARGET=$(echo "$BASELINE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('target','unknown'))")
CONFIG=$(echo "$BASELINE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('config','unknown'))")

BASELINES_DIR="$PROJECT_DIR/results/baselines"
mkdir -p "$BASELINES_DIR"

OUTFILE="$BASELINES_DIR/${TARGET}_${CONFIG}.json"
echo "$BASELINE" > "$OUTFILE"
echo "Saved baseline: $OUTFILE"
echo "  Target: $TARGET  Config: $CONFIG  Result: $(echo "$BASELINE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('result','?'))")"
