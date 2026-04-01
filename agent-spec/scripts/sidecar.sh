#!/usr/bin/env bash
# sidecar.sh — Background resource monitor that writes snapshots to APC.
#
# Usage: scripts/sidecar.sh [interval_seconds]
# Runs until stopped. Start with & and track the PID.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

INTERVAL="${1:-30}"

while true; do
  SNAPSHOT=$("$SCRIPT_DIR/resources.sh" 2>/dev/null || echo '{"cpu":0,"mem":0,"disk_free_gb":0}')
  apc_log "METRIC" "resource_snapshot" "System resources" "$SNAPSHOT"
  sleep "$INTERVAL"
done
