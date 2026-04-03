---
name: stop
description: Stop all agent-spec processes, clear ports, remove sandboxes, verify clean state.
disable-model-invocation: true
---

# /stop — Cleanup

Run cleanup, then verify:

```bash
python3 scripts/cleanup.py
```

`cleanup.py` handles: tracked PIDs (with SIGTERM→SIGKILL escalation and process tree traversal), port clearing, orphaned process detection, sandbox removal, parallel log cleanup, and worktree pruning.

If processes remain after cleanup, escalate with `--force` to also delete /tmp run logs:

```bash
python3 scripts/cleanup.py --force
```

Verify with:

```bash
python3 scripts/system_monitor.py
```

Active Runs, Sandboxes, Ports in use, and Tracked PIDs should all be 0.
