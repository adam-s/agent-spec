---
name: stop
description: Emergency stop — halt all agent-spec processes, clear ports, remove sandboxes, prune worktrees, verify clean state.
disable-model-invocation: true
---

# /stop — Emergency Cleanup

Run these steps in order:

## 1. Stop all background agents

Stop any running agents using TaskStop for each active agent ID. If IDs are unknown, proceed to process cleanup.

## 2. Stop agent-spec processes

```bash
# Stop tracked PIDs
if [ -f /tmp/agent-spec-pids.txt ]; then
  while IFS='|' read -r pid port purpose; do
    kill "$pid" 2>/dev/null && echo "Stopped PID $pid ($purpose) on port $port"
  done < /tmp/agent-spec-pids.txt
  : > /tmp/agent-spec-pids.txt
fi

# Stop processes on reserved port ranges
for port in $(seq 3100 3110) $(seq 4000 4010); do
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "$pids" | xargs kill -9 2>/dev/null || true
    echo "Cleared port $port"
  fi
done
```

## 3. Stop orphaned processes

```bash
pkill -9 -f "bun.*server" 2>/dev/null || true
pkill -9 -f "node.*queries" 2>/dev/null || true
pkill -f "chromium.*agent-spec" 2>/dev/null || true
pkill -f "patchright" 2>/dev/null || true
pkill -f "sidecar.sh" 2>/dev/null || true
```

## 4. Remove sandboxes and temp data

```bash
rm -rf /tmp/claude/agent-spec-*/
rm -rf /tmp/agent-spec/*/
rm -rf /tmp/agent-spec-inject-*/
rm -rf /tmp/agent-spec-parallel-*.txt
```

## 5. Prune worktrees

```bash
git worktree prune 2>/dev/null || true
rm -rf .claude/worktrees/*/ 2>/dev/null || true
```

## 6. Verify clean state

```bash
echo ""
echo "=== Verification ==="
echo "Sandboxes:    $(ls -d /tmp/claude/agent-spec-*/ 2>/dev/null | wc -l | tr -d ' ')"
echo "APC channels: $(ls -d /tmp/agent-spec/*/ 2>/dev/null | wc -l | tr -d ' ')"
echo "Tracked PIDs: $(cat /tmp/agent-spec-pids.txt 2>/dev/null | wc -l | tr -d ' ')"
echo "Port 3100:    $(lsof -ti:3100 2>/dev/null | wc -l | tr -d ' ')"
echo "Bun procs:    $(pgrep -f 'bun.*server' 2>/dev/null | wc -l | tr -d ' ')"
echo "Node procs:   $(pgrep -f 'node.*queries' 2>/dev/null | wc -l | tr -d ' ')"
```

All counts should be 0. If any are non-zero, re-run the relevant step.
