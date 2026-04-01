#!/usr/bin/env bash
# tokens.sh — Print token metrics for a run.
#
# Usage: scripts/tokens.sh <run_id>
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

RUN_ID="${1:?Usage: tokens.sh <run_id>}"
EVENTS="$RUN_ROOT/$RUN_ID/events.jsonl"
require_file "$EVENTS" "No events for run $RUN_ID"

grep '"event":"token_update"' "$EVENTS" | tail -1 | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print(f\"Input: {d.get('input',0)}  Output: {d.get('output',0)}  Cost: \${d.get('cost_usd',0)}\")
" 2>/dev/null || echo "No token data"
