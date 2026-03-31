#!/usr/bin/env bash
# SubagentStop hook — kill processes tracked by agent-spec.
set -euo pipefail

PID_FILE="/tmp/agent-spec-pids.txt"

if [[ ! -f "$PID_FILE" ]]; then
  exit 0
fi

while IFS='|' read -r pid port purpose; do
  kill -TERM "$pid" 2>/dev/null || true
done < "$PID_FILE"

sleep 2

while IFS='|' read -r pid port purpose; do
  kill -9 "$pid" 2>/dev/null || true
done < "$PID_FILE"

rm -f "$PID_FILE"
