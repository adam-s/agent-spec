# Resource Safety

## Before Launching Agents

ALWAYS confirm with the user before running any command that spawns Claude agent processes. This includes:

- `python3 scripts/cli.py run` (single or parallel)
- `python3 scripts/parallel.py`
- `python3 scripts/invoke.py`
- `/run-eval`
- `/iterate`

State what you are about to launch: how many agents, which target, which config. Wait for confirmation.

**"Run it again"** means one sequential run unless the user explicitly says "parallel" or "simultaneously."

## Parallel Runs

- Default to `--instances 1` unless the user specifies a count
- Never launch more than 3 parallel instances without explicit user approval of the exact count
- Before any parallel run, warn: "This will launch N concurrent Claude agents. Each uses ~500MB RAM + CPU. Proceed?"

## Use run_in_background

All eval and parallel runs MUST use `run_in_background: true` in the Bash tool. Never block the conversation waiting for an agent to finish. Print the monitoring command and let the system notify on completion.

## Sequential Over Parallel

When the user asks to "run it a few times" or "check consistency," default to sequential runs (one at a time) unless they explicitly request parallel. Sequential is slower but won't overload the machine.

## Process & Port Management

Every process agent-spec spawns must be tracked and cleaned up. Orphaned processes consume resources indefinitely.

**Process lifecycle:**
1. **Track on spawn:** Every background process gets registered via `track_pid()` in `lib.py`
2. **Prune on start:** `invoke.py` prunes dead PIDs from the registry before each run
3. **Stop on exit:** `_archive_and_cleanup()` stops the agent process tree on ANY exit (normal, error, signal)
4. **Sweep on demand:** `cleanup.py` stops all tracked processes and sweeps reserved ports

**PID Registry:** `/tmp/agent-spec-pids.txt` — one line per process: `PID|PORT|PURPOSE`

**Reserved ports:** `3100-3110` (target test servers), `4000-4010` (agent-chosen ports)

## Shutdown Protocol

When stopping a run or cleaning up:
1. Stop process trees (children first, then parent) — not just the parent PID
2. Escalate: SIGTERM → wait 5s → SIGKILL
3. Verify the process is actually dead before moving on
4. Clear the PID registry after all processes are confirmed stopped

Use `/stop` or `python3 scripts/cleanup.py` to stop everything. After any crash or unexpected exit, run cleanup immediately.

## In verify.sh Scripts

Any verify.sh that starts a server MUST:
1. Stop existing processes on its port before starting
2. Start the server in background and record the PID
3. Stop the server after tests complete, in ALL exit paths

## Sandbox Hygiene

- Sandboxes in `/tmp/claude/agent-spec-*` trigger Spotlight indexing on macOS. Each sandbox creates a `.metadata_never_index` file to prevent this.
- Always remove sandboxes on exit (unless `--keep` is specified)
- Parallel log files in `/tmp/agent-spec-parallel-*` are cleaned up by `cleanup.py`
