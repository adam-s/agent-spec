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

## Output Capture

When running multiple sequential agents in a loop, each run MUST print its result to stdout before starting the next. Never suppress or filter run output with `tail -1`, `head`, or `grep` — capture the full output, then summarize. See @.claude/rules/observability.md.

## Sequential Over Parallel

When the user asks to "run it a few times" or "check consistency," default to sequential runs (one at a time) unless they explicitly request parallel. Sequential is slower but won't overload the machine.

## Process Tracking

Every process spawned by agent-spec MUST be tracked via `track_pid()` in `lib.py`. This includes:
- The sidecar (system_monitor.py)
- The Claude agent subprocess
- Parallel child processes

The PID registry (`/tmp/agent-spec-pids.txt`) is used by `cleanup.py` and `system_monitor.py` to find and stop all processes. Untracked processes become orphans that consume resources indefinitely.

## Shutdown Protocol

When stopping a run or cleaning up:
1. Stop process trees (children first, then parent) — not just the parent PID
2. Escalate: SIGTERM → wait 5s → SIGKILL
3. Verify the process is actually dead before moving on
4. Clear the PID registry after all processes are confirmed stopped

Use `/stop` or `python3 scripts/cleanup.py` to stop everything. After any crash or unexpected exit, run cleanup immediately.

## Sandbox Hygiene

- Sandboxes in `/tmp/claude/agent-spec-*` trigger Spotlight indexing on macOS. Each sandbox creates a `.metadata_never_index` file to prevent this.
- Always remove sandboxes on exit (unless `--keep` is specified)
- Parallel log files in `/tmp/agent-spec-parallel-*` are cleaned up by `cleanup.py`
