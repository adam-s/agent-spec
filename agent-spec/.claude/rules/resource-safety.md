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
