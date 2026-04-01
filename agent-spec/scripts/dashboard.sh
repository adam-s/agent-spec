#!/usr/bin/env bash
# dashboard.sh — Live CLI dashboard for agent-spec runs.
#
# Usage:
#   scripts/dashboard.sh <run_id>              # Live tail
#   scripts/dashboard.sh --latest              # Most recent run
#   scripts/dashboard.sh <run_id> --summary    # One-shot summary
#   scripts/dashboard.sh <run_id> --events token_update,score
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
  (if .event == "token_update" then " \u001b[90m[\(.data.input)in/\(.data.output)out $\(.data.cost_usd)]\u001b[0m"
   elif .event == "resource_snapshot" then " \u001b[90m[CPU \(.data.cpu)% Mem \(.data.mem)%]\u001b[0m"
   elif .event == "score" then " \u001b[90m[\(.data.result)]\u001b[0m"
   elif .event == "test_passed" then " \u001b[90m[\(.data.test_name)]\u001b[0m"
   elif .event == "test_failed" then " \u001b[90m[\(.data.test_name): \(.data.details // "")]\u001b[0m"
   elif .event == "agent_complete" then " \u001b[90m[\(.data.duration_ms / 1000)s]\u001b[0m"
   elif (.data | length) > 0 then " \u001b[90m\(.data | tostring)\u001b[0m"
   else "" end)
'

if [[ "$SUMMARY" = true ]]; then
  # One-shot summary
  echo "── agent-spec ─── run: $RUN_ID ──"
  echo ""

  # Target/Config
  TARGET=$(jq -r 'select(.event=="agent_started") | .data.target // "?"' "$LOG" 2>/dev/null | tail -1)
  CONFIG=$(jq -r 'select(.event=="agent_started") | .data.config // "?"' "$LOG" 2>/dev/null | tail -1)
  if [[ -n "$TARGET" ]]; then
    echo "  Target: $TARGET / $CONFIG"
  fi

  # Status + Duration
  LAST_EVENT=$(tail -1 "$LOG" | jq -r '.event' 2>/dev/null || echo "unknown")
  DUR_MS=$(jq -r 'select(.event=="agent_complete" or .event=="agent_error") | .data.duration_ms // 0' "$LOG" 2>/dev/null | tail -1)
  DUR_HUMAN=""
  if [[ -n "$DUR_MS" ]] && [[ "$DUR_MS" -gt 0 ]] 2>/dev/null; then
    DUR_S=$((DUR_MS / 1000))
    if [[ $DUR_S -ge 60 ]]; then
      DUR_HUMAN=" (${DUR_S}s / $((DUR_S / 60))m $((DUR_S % 60))s)"
    else
      DUR_HUMAN=" (${DUR_S}s)"
    fi
  fi
  if [[ "$LAST_EVENT" == "agent_complete" ]] || [[ "$LAST_EVENT" == "score" ]]; then
    echo "  Status: COMPLETE$DUR_HUMAN"
  elif [[ "$LAST_EVENT" == "agent_error" ]]; then
    echo "  Status: ERROR$DUR_HUMAN"
  else
    echo "  Status: $LAST_EVENT"
  fi

  # Tokens
  TOKENS=$(jq -r 'select(.event=="token_update") | .data | "\(.input // 0) in / \(.output // 0) out / $\(.cost_usd // 0)"' "$LOG" 2>/dev/null | tail -1)
  if [[ -n "$TOKENS" ]]; then
    echo "  Tokens: $TOKENS"
  fi

  # Tests
  T_PASS=$(jq -c 'select(.event=="test_passed")' "$LOG" 2>/dev/null | wc -l | tr -d ' ')
  T_FAIL=$(jq -c 'select(.event=="test_failed")' "$LOG" 2>/dev/null | wc -l | tr -d ' ')
  T_TOTAL=$((T_PASS + T_FAIL))
  if [[ $T_TOTAL -gt 0 ]]; then
    echo "  Tests:  $T_PASS passed / $T_FAIL failed ($T_TOTAL total)"
  fi

  # Score
  SCORE=$(jq -r 'select(.event=="score") | .data.result' "$LOG" 2>/dev/null | tail -1)
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
