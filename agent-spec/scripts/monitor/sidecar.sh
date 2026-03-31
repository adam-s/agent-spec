#!/usr/bin/env bash
# sidecar.sh — Background resource monitor that writes snapshots to APC.
#
# Usage: scripts/monitor/sidecar.sh [interval_seconds]
# Runs until killed. Start with & and track the PID.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../apc/lib.sh"

INTERVAL="${1:-30}"

while true; do
  SNAPSHOT=$("$SCRIPT_DIR/resources.sh" 2>/dev/null || echo '{"cpu":0,"mem":0,"disk_free_gb":0}')
  apc_log "METRIC" "resource_snapshot" "System resources" "$SNAPSHOT"
  sleep "$INTERVAL"
done
