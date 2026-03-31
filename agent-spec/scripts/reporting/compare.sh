#!/usr/bin/env bash
# compare.sh — Compare results across multiple runs.
#
# Usage: scripts/reporting/compare.sh [run_id ...]
#        scripts/reporting/compare.sh --all
set -euo pipefail

if [[ "${1:-}" == "--all" ]]; then
  RUNS=$(ls /tmp/agent-spec/ 2>/dev/null)
else
  RUNS="$*"
fi

if [[ -z "$RUNS" ]]; then
  echo "Usage: compare.sh <run_id> <run_id> ... | --all" >&2
  exit 1
fi

# Header
printf "| %-10s | %-20s | %-15s | %8s | %8s | %8s | %6s |\n" \
  "Run ID" "Target" "Config" "Input" "Output" "Total" "Result"
printf "|%s|%s|%s|%s|%s|%s|%s|\n" \
  "------------" "----------------------" "-----------------" "----------" "----------" "----------" "--------"

for run_id in $RUNS; do
  LOG="/tmp/agent-spec/$run_id/events.jsonl"
  [[ -f "$LOG" ]] || continue

  TARGET=$(jq -r 'select(.event=="agent_started") | .data.target // "?"' "$LOG" 2>/dev/null | tail -1)
  CONFIG=$(jq -r 'select(.event=="agent_started") | .data.config // "?"' "$LOG" 2>/dev/null | tail -1)
  INPUT=$(jq -r 'select(.event=="token_update") | .data.input // 0' "$LOG" 2>/dev/null | tail -1)
  OUTPUT=$(jq -r 'select(.event=="token_update") | .data.output // 0' "$LOG" 2>/dev/null | tail -1)
  TOTAL=$(( ${INPUT:-0} + ${OUTPUT:-0} ))
  RESULT=$(jq -r 'select(.event=="score") | .data.result // "N/A"' "$LOG" 2>/dev/null | tail -1)

  printf "| %-10s | %-20s | %-15s | %8s | %8s | %8s | %6s |\n" \
    "$run_id" "${TARGET:-?}" "${CONFIG:-?}" "${INPUT:-0}" "${OUTPUT:-0}" "$TOTAL" "${RESULT:-N/A}"
done
