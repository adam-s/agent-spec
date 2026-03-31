#!/usr/bin/env bash
# dashboard.sh — Live CLI dashboard for agent-spec runs.
#
# Usage:
#   scripts/cli/dashboard.sh <run_id>              # Live tail
#   scripts/cli/dashboard.sh --latest              # Most recent run
#   scripts/cli/dashboard.sh <run_id> --summary    # One-shot summary
#   scripts/cli/dashboard.sh <run_id> --events token_update,score
set -euo pipefail

# Parse arguments
RUN_ID=""
SUMMARY=false
EVENT_FILTER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --latest)
      RUN_ID=$(ls -t /tmp/agent-spec/ 2>/dev/null | head -1)
      if [[ -z "$RUN_ID" ]]; then
        echo "No runs found in /tmp/agent-spec/" >&2
        exit 1
      fi
      shift ;;
    --summary) SUMMARY=true; shift ;;
    --events) EVENT_FILTER="$2"; shift 2 ;;
    *) RUN_ID="$1"; shift ;;
  esac
done

if [[ -z "$RUN_ID" ]]; then
  echo "Usage: dashboard.sh <run_id> | --latest [--summary] [--events type,type]" >&2
  exit 1
fi

LOG="/tmp/agent-spec/$RUN_ID/events.jsonl"

if [[ ! -f "$LOG" ]]; then
  echo "No events found: $LOG" >&2
  exit 1
fi

# Build jq filter
JQ_FILTER='.'
if [[ -n "$EVENT_FILTER" ]]; then
  # Convert comma-separated to jq OR expression
  EVENTS=$(echo "$EVENT_FILTER" | sed 's/,/" or .event=="/g')
  JQ_FILTER="select(.event==\"$EVENTS\")"
fi

FORMAT='
  "\u001b[90m[\(.ts[11:19])]\u001b[0m " +
  (if .level == "ERROR" then "\u001b[31m" elif .level == "WARN" then "\u001b[33m" elif .level == "METRIC" then "\u001b[36m" else "\u001b[32m" end) +
  "[\(.level)]\u001b[0m " +
  "\u001b[1m\(.event)\u001b[0m — \(.msg)" +
  (if (.data | length) > 0 then " \u001b[90m\(.data | tostring)\u001b[0m" else "" end)
'

if [[ "$SUMMARY" = true ]]; then
  # One-shot summary
  echo "── agent-spec ─── run: $RUN_ID ──"
  echo ""

  # Status
  LAST_EVENT=$(tail -1 "$LOG" | jq -r '.event' 2>/dev/null || echo "unknown")
  if [[ "$LAST_EVENT" == "agent_complete" ]] || [[ "$LAST_EVENT" == "score" ]]; then
    echo "  Status: COMPLETE"
  elif [[ "$LAST_EVENT" == "agent_error" ]]; then
    echo "  Status: ERROR"
  else
    echo "  Status: $LAST_EVENT"
  fi

  # Tokens
  TOKENS=$(jq -r 'select(.event=="token_update") | .data | "\(.input // 0) in / \(.output // 0) out / $\(.cost_usd // 0)"' "$LOG" 2>/dev/null | tail -1)
  if [[ -n "$TOKENS" ]]; then
    echo "  Tokens: $TOKENS"
  fi

  # Score
  SCORE=$(jq -r "select(.event==\"score\") | .data.result" "$LOG" 2>/dev/null | tail -1)
  if [[ -n "$SCORE" ]]; then
    echo "  Result: $SCORE"
  fi

  # Resources (last snapshot)
  RES=$(jq -r 'select(.event=="resource_snapshot") | .data | "CPU \(.cpu)% | Mem \(.mem)% | Disk \(.disk_free_gb) GB free"' "$LOG" 2>/dev/null | tail -1)
  if [[ -n "$RES" ]]; then
    echo "  Resources: $RES"
  fi

  echo ""
  echo "  Events:"
  jq -r "$JQ_FILTER | $FORMAT" "$LOG" 2>/dev/null | sed 's/^/    /'
else
  # Live tail
  echo "── agent-spec ─── run: $RUN_ID ─── tailing ──"
  echo ""

  # Print existing events
  jq -r "$JQ_FILTER | $FORMAT" "$LOG" 2>/dev/null

  # Tail for new events
  tail -f -n 0 "$LOG" 2>/dev/null | while IFS= read -r line; do
    echo "$line" | jq -r "$JQ_FILTER | $FORMAT" 2>/dev/null
  done
fi
