# Port Management

## Reserved Ranges

- `3100-3110` — Target test servers (hono-websocket-counter uses 3100)
- `4000-4010` — Agent-chosen ports (if agent picks its own)

## Before and After Every Run

`scripts/cleanup.sh` runs automatically at the start and end of each `invoke.sh` run (via the EXIT trap in `scripts/lib.sh`). It:
1. Reads the PID registry for known port assignments
2. Sweeps the reserved port ranges
3. Stops orphaned Chromium/Patchright browser instances

## In verify.sh Scripts

Any verify.sh that starts a server MUST:
1. Stop existing processes on its port before starting
2. Start the server in background and record the PID
3. Stop the server after tests complete, in ALL exit paths
4. Pattern: `lsof -ti:PORT | xargs kill -9 2>/dev/null || true`

## PID Registry Format

`/tmp/agent-spec-pids.txt` — one line per process: `PID|PORT|PURPOSE`

Track every background process via the `apc_track_pid` function in `scripts/lib.sh`. The port field enables port-aware cleanup.
