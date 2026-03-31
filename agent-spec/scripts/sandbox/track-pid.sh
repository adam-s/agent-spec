#!/usr/bin/env bash
# track-pid.sh — Register a spawned process for cleanup.
#
# Usage: scripts/sandbox/track-pid.sh <pid> <port> <purpose>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../apc/lib.sh"

PID="${1:?Usage: track-pid.sh <pid> <port> <purpose>}"
PORT="${2:-0}"
PURPOSE="${3:-unknown}"
PID_FILE="/tmp/agent-spec-pids.txt"

echo "${PID}|${PORT}|${PURPOSE}" >> "$PID_FILE"

apc_log "DEBUG" "pid_tracked" "Registered process" \
  "{\"pid\":$PID,\"port\":$PORT,\"purpose\":\"$PURPOSE\"}"
