#!/usr/bin/env bash
# swap-claude-dir.sh — Replace .claude/ in a sandbox with a test config.
#
# Usage: scripts/sandbox/swap-claude-dir.sh <sandbox_path> <config_path>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../apc/lib.sh"

SANDBOX="${1:?Usage: swap-claude-dir.sh <sandbox_path> <config_path>}"
CONFIG="${2:?Usage: swap-claude-dir.sh <sandbox_path> <config_path>}"

if [[ ! -d "$CONFIG" ]]; then
  echo "Config directory not found: $CONFIG" >&2
  exit 1
fi

if [[ -z "$(ls -A "$CONFIG" 2>/dev/null)" ]]; then
  echo "WARNING: Config directory is empty: $CONFIG (agent will have no instructions)" >&2
fi

rm -rf "$SANDBOX/.claude"
cp -a "$CONFIG" "$SANDBOX/.claude"

apc_log "INFO" "config_swapped" "Replaced .claude/ with test config" \
  "{\"config\":\"$CONFIG\",\"sandbox\":\"$SANDBOX\"}"
