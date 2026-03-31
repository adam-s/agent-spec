#!/usr/bin/env bash
# score.sh — Extract pass/fail results from a run's events.
#
# Usage: scripts/reporting/score.sh <run_id>
set -euo pipefail

RUN_ID="${1:?Usage: score.sh <run_id>}"
LOG="/tmp/agent-spec/$RUN_ID/events.jsonl"

if [[ ! -f "$LOG" ]]; then
  echo "No events found: $LOG" >&2
  exit 1
fi

# Test events
PASSED=$(jq -r 'select(.event=="test_passed") | .data.test_name' "$LOG" 2>/dev/null | wc -l | tr -d ' ')
FAILED=$(jq -r 'select(.event=="test_failed") | .data.test_name' "$LOG" 2>/dev/null | wc -l | tr -d ' ')

# Overall score
RESULT=$(jq -r 'select(.event=="score") | .data.result' "$LOG" 2>/dev/null | tail -1)

echo "Tests passed: $PASSED"
echo "Tests failed: $FAILED"
echo "Result:       ${RESULT:-N/A}"
