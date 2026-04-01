#!/usr/bin/env bash
# score.sh — Print the PASS/FAIL result for a run.
#
# Usage: scripts/score.sh <run_id>
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

RUN_ID="${1:?Usage: score.sh <run_id>}"
EVENTS="$RUN_ROOT/$RUN_ID/events.jsonl"
require_file "$EVENTS" "No events for run $RUN_ID"

RESULT=$(grep '"event":"score"' "$EVENTS" | tail -1 | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['result'])" 2>/dev/null || echo "N/A")
echo "$RESULT"
