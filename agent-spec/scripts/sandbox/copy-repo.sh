#!/usr/bin/env bash
# copy-repo.sh — Copy a repository into an isolated sandbox.
#
# Usage: scripts/sandbox/copy-repo.sh <source_path> [run_id]
# Output: Prints the sandbox path to stdout.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../apc/lib.sh"

SOURCE="${1:?Usage: copy-repo.sh <source_path> [run_id]}"
export AGENT_SPEC_RUN_ID="${2:-$(uuidgen | tr '[:upper:]' '[:lower:]' | head -c 8)}"

# Ensure /tmp/claude exists (Claude Code sandbox bug #36759)
mkdir -p /tmp/claude

SANDBOX="/tmp/claude/agent-spec-${AGENT_SPEC_RUN_ID}"

if [[ -d "$SANDBOX" ]]; then
  echo "ERROR: Sandbox already exists: $SANDBOX" >&2
  exit 1
fi

cp -aL "$SOURCE" "$SANDBOX" 2>/dev/null || cp -a "$SOURCE" "$SANDBOX"

apc_log "INFO" "sandbox_created" "Copied repo to sandbox" \
  "{\"source\":\"$SOURCE\",\"sandbox\":\"$SANDBOX\"}"

echo "$SANDBOX"
