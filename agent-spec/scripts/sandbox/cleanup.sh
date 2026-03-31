#!/usr/bin/env bash
# cleanup.sh — Kill tracked processes and remove sandboxes.
#
# Usage: scripts/sandbox/cleanup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../apc/lib.sh"

apc_log "DEBUG" "cleanup_start" "Starting cleanup" "{}"

KILLED=0
REMOVED=0
PID_FILE="/tmp/agent-spec-pids.txt"

# 1. Kill tracked PIDs (TERM → 2s → KILL)
if [[ -f "$PID_FILE" ]]; then
  while IFS='|' read -r pid port purpose; do
    kill -TERM "$pid" 2>/dev/null && echo "  TERM $pid ($purpose)" && ((KILLED++)) || true
  done < "$PID_FILE"
  sleep 2
  while IFS='|' read -r pid port purpose; do
    kill -9 "$pid" 2>/dev/null && echo "  KILL $pid ($purpose)" || true
  done < "$PID_FILE"
  rm -f "$PID_FILE"
fi

# 2. Remove all agent-spec sandboxes
for dir in /tmp/claude/agent-spec-*/; do
  if [[ -d "$dir" ]]; then
    rm -rf "$dir"
    echo "  Removed: $dir"
    ((REMOVED++))
  fi
done

# 3. Kill orphaned bun/node servers on common test ports
for port in 3100 3101 3102 3103 3104 3105; do
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill -9 2>/dev/null || true
    echo "  Port $port: killed"
  fi
done

# 4. Verify
echo ""
echo "=== Cleanup Complete ==="
echo "  PIDs killed: $KILLED"
echo "  Sandboxes removed: $REMOVED"
REMAINING=$(ls -d /tmp/claude/agent-spec-*/ 2>/dev/null | wc -l | tr -d ' ')
echo "  Remaining sandboxes: $REMAINING"

apc_log "DEBUG" "cleanup_done" "Cleanup complete" \
  "{\"killed_pids\":$KILLED,\"removed_dirs\":$REMOVED}"
