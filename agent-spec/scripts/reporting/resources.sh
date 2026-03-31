#!/usr/bin/env bash
# resources.sh — Extract peak resource usage from a run's events.
#
# Usage: scripts/reporting/resources.sh <run_id>
set -euo pipefail

RUN_ID="${1:?Usage: resources.sh <run_id>}"
LOG="/tmp/agent-spec/$RUN_ID/events.jsonl"

if [[ ! -f "$LOG" ]]; then
  echo "No events found: $LOG" >&2
  exit 1
fi

SNAPSHOTS=$(jq -s '[.[] | select(.event=="resource_snapshot") | .data]' "$LOG" 2>/dev/null)
COUNT=$(echo "$SNAPSHOTS" | jq 'length')

if [[ "$COUNT" -eq 0 ]]; then
  echo "No resource snapshots found."
  exit 0
fi

echo "$SNAPSHOTS" | jq -r '
  "Snapshots:     \(length)",
  "Peak CPU:      \([.[].cpu] | max)%",
  "Peak Memory:   \([.[].mem] | max)%",
  "Min Disk Free: \([.[].disk_free_gb] | min) GB",
  "Avg CPU:       \(([.[].cpu] | add) / length | . * 10 | round / 10)%",
  "Avg Memory:    \(([.[].mem] | add) / length | . * 10 | round / 10)%"
'
