---
name: stop
description: Emergency stop — halt all agent-spec processes, remove sandboxes, clean up
disable-model-invocation: true
---

# /stop — Emergency Cleanup

Stop all tracked processes, remove all sandboxes, and verify clean state.

## Steps

1. Halt all tracked PIDs from `/tmp/agent-spec-pids.txt`
2. Stop processes on common test ports (3100-3105)
3. Shut down orphaned bun/node processes from test runs
4. Remove all sandbox directories in `/tmp/claude/agent-spec-*/`
5. Remove all APC channel data in `/tmp/agent-spec/`
6. Verify clean state

## Run

```bash
bash "$CLAUDE_PROJECT_DIR/scripts/sandbox/cleanup.sh"

# Also clean APC channels
rm -rf /tmp/agent-spec/*/

# Shut down any remaining bun/node orphans
pkill -9 -f "bun.*server" 2>/dev/null || true
pkill -9 -f "node.*queries" 2>/dev/null || true

# Verify
echo ""
echo "=== Verification ==="
echo "Sandboxes: $(ls -d /tmp/claude/agent-spec-*/ 2>/dev/null | wc -l | tr -d ' ' || echo 0)"
echo "APC channels: $(ls -d /tmp/agent-spec/*/ 2>/dev/null | wc -l | tr -d ' ' || echo 0)"
echo "Tracked PIDs: $(cat /tmp/agent-spec-pids.txt 2>/dev/null | wc -l | tr -d ' ' || echo 0)"
echo "Bun processes: $(pgrep -f 'bun.*server' 2>/dev/null | wc -l | tr -d ' ' || echo 0)"
echo "Node processes: $(pgrep -f 'node.*queries' 2>/dev/null | wc -l | tr -d ' ' || echo 0)"
```

After running, confirm all counts are 0.
