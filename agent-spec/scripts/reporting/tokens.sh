#!/usr/bin/env bash
# tokens.sh — Extract token metrics from a run's events.
#
# Usage: scripts/reporting/tokens.sh <run_id>
set -euo pipefail

RUN_ID="${1:?Usage: tokens.sh <run_id>}"
LOG="/tmp/agent-spec/$RUN_ID/events.jsonl"

if [[ ! -f "$LOG" ]]; then
  echo "No events found: $LOG" >&2
  exit 1
fi

jq -r 'select(.event=="token_update") | .data |
  "Input:        \(.input // 0)",
  "Output:       \(.output // 0)",
  "Cache create: \(.cache_create // 0)",
  "Cache read:   \(.cache_read // 0)",
  "Total:        \((.input // 0) + (.output // 0))",
  "Cost:         $\(.cost_usd // 0)",
  "Turns:        \(.turns // 0)",
  "Duration:     \((.duration_ms // 0) / 1000 | floor)s (\((.duration_ms // 0) / 1000 / 60 | floor)m \((.duration_ms // 0) / 1000 % 60 | floor)s)"
' "$LOG" | tail -8
