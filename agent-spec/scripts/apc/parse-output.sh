#!/usr/bin/env bash
# parse-output.sh — Extract token metrics from claude --output-format json.
#
# Usage: scripts/apc/parse-output.sh <json_file>
# Output: JSON with token counts, cost, turns, duration to stdout
set -euo pipefail

JSON_FILE="${1:?Usage: parse-output.sh <json_file>}"

if [[ ! -f "$JSON_FILE" ]]; then
  echo '{"error":"file not found"}' >&2
  exit 1
fi

jq '{
  input:        (.modelUsage | to_entries[0].value.inputTokens // 0),
  output:       (.modelUsage | to_entries[0].value.outputTokens // 0),
  cache_create: (.modelUsage | to_entries[0].value.cacheCreationInputTokens // 0),
  cache_read:   (.modelUsage | to_entries[0].value.cacheReadInputTokens // 0),
  cost_usd:     ((.modelUsage | to_entries[0].value.costUSD // 0) * 1000 | round / 1000),
  turns:        (.num_turns // .numTurns // 0),
  duration_ms:  (.duration_ms // .durationMs // 0)
}' "$JSON_FILE"
