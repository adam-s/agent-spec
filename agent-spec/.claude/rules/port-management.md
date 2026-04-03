# Process & Port Management

## No Orphans, No Zombies

Every process agent-spec spawns must be tracked and cleaned up. Orphaned processes consume resources indefinitely — a rogue agent or background server can saturate CPU, hold ports, or run up API costs.

## Process Lifecycle

1. **Track on spawn:** Every background process gets registered via `track_pid()` in `lib.py`
2. **Prune on start:** `invoke.py` prunes dead PIDs from the registry before each run
3. **Stop on exit:** `_archive_and_cleanup()` stops the agent process tree on ANY exit (normal, error, signal)
4. **Prune on exit:** Dead PIDs are removed from the registry after cleanup
5. **Sweep on demand:** `cleanup.py` stops all tracked processes and sweeps reserved ports

## PID Registry

`/tmp/agent-spec-pids.txt` — one line per process: `PID|PORT|PURPOSE`

Track every background process via `track_pid()` in `scripts/lib.py`. The registry is append-only during a run, pruned of dead PIDs at run start and end.

## Reserved Port Ranges

- `3100-3110` — Target test servers
- `4000-4010` — Agent-chosen ports

## In verify.sh Scripts

Any verify.sh that starts a server MUST:

1. Stop existing processes on its port before starting
2. Start the server in background and record the PID
3. Stop the server after tests complete, in ALL exit paths
4. Pattern: `lsof -ti:PORT | xargs kill -9 2>/dev/null || true`

## After Any Crash

Run `python3 scripts/cleanup.py` immediately. It:

1. Stops all tracked PIDs (process trees, not just parents)
2. Sweeps reserved port ranges for untracked processes
3. Removes leftover sandboxes in `/tmp/claude/agent-spec-*`
4. Clears the PID registry
