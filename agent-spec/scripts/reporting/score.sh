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

# Test events (grep valid JSON lines first to tolerate malformed entries)
PASSED=$(grep -c '"test_passed"' "$LOG" 2>/dev/null || echo 0)
FAILED=$(grep -c '"test_failed"' "$LOG" 2>/dev/null || echo 0)

# Overall score
RESULT=$(grep '"score"' "$LOG" 2>/dev/null | jq -r '.data.result' 2>/dev/null | tail -1)

echo "Tests passed: $PASSED"
echo "Tests failed: $FAILED"
echo "Result:       ${RESULT:-N/A}"
