#!/usr/bin/env bash
# cleanup.sh — Stop all agent-spec processes, clear ports, remove sandboxes.
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

echo "=== agent-spec cleanup ==="

# 1. Stop tracked PIDs
stop_tracked_pids

# 2. Clear all ports in range
for port in $(seq "$PORT_MIN" "$PORT_MAX"); do
  release_port "$port"
done

# 3. Stop orphaned processes
for pattern in "bun.*server" "node.*queries" "chromium.*agent-spec" "patchright" "sidecar.sh"; do
  pids=$(pgrep -f "$pattern" 2>/dev/null) || true
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill -9 2>/dev/null || true
    echo "  Stopped: $pattern"
  fi
done

# 4. Remove sandboxes and temp data
rm -rf "$SANDBOX_ROOT"-* 2>/dev/null || true
rm -rf "$RUN_ROOT"/*/ 2>/dev/null || true
rm -rf /tmp/agent-spec-inject-* 2>/dev/null || true
rm -rf /tmp/agent-spec-parallel-* 2>/dev/null || true

# 5. Prune worktrees
git worktree prune 2>/dev/null || true

# 6. Verify
echo ""
echo "=== Verification ==="
echo "  Sandboxes:    $(ls -d "$SANDBOX_ROOT"-* 2>/dev/null | wc -l | tr -d ' ')"
echo "  Run dirs:     $(ls -d "$RUN_ROOT"/*/ 2>/dev/null | wc -l | tr -d ' ')"
echo "  Tracked PIDs: $([[ -f "$PID_FILE" ]] && wc -l < "$PID_FILE" | tr -d ' ' || echo 0)"
echo "  Port $PORT_MIN:     $(lsof -ti:"$PORT_MIN" 2>/dev/null | wc -l | tr -d ' ')"

echo ""
echo "Clean."
