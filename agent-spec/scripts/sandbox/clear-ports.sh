#!/usr/bin/env bash
# clear-ports.sh — Stop processes on ports used by agent-spec targets.
#
# Reads the PID registry for port info, then sweeps known test port ranges.
# Also detects and stops headless browser instances (Chromium/Patchright).
#
# Usage: scripts/sandbox/clear-ports.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../apc/lib.sh"

STOPPED=0

# 1. Stop processes on registered ports from PID file
PID_FILE="/tmp/agent-spec-pids.txt"
if [[ -f "$PID_FILE" ]]; then
  while IFS='|' read -r pid port purpose; do
    if [[ "$port" -gt 0 ]] 2>/dev/null; then
      pids=$(lsof -ti:"$port" 2>/dev/null || true)
      if [[ -n "$pids" ]]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
        ((STOPPED++))
      fi
    fi
  done < "$PID_FILE"
fi

# 2. Sweep known test port ranges (3100-3110 for targets, 4000-4100 for agent-chosen ports)
for port in $(seq 3100 3110) $(seq 4000 4010); do
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill -9 2>/dev/null || true
    echo "  Port $port: stopped"
    ((STOPPED++)) || true
  fi
done

# 3. Stop orphaned headless browser instances (Patchright/Playwright Chromium)
# Only stop instances launched by agent-spec, identified by tmp path
for pid in $(pgrep -f "chromium.*agent-spec" 2>/dev/null || true); do
  kill -9 "$pid" 2>/dev/null || true
  echo "  Chromium $pid: stopped"
  ((STOPPED++)) || true
done

# Also stop patchright instances
for pid in $(pgrep -f "patchright" 2>/dev/null || true); do
  kill -9 "$pid" 2>/dev/null || true
  echo "  Patchright $pid: stopped"
  ((STOPPED++)) || true
done

if [[ $STOPPED -gt 0 ]]; then
  apc_log "DEBUG" "ports_cleared" "Stopped processes on test ports" "{\"stopped\":$STOPPED}"
fi
