# Testing Protocol

## Evals

See @.claude/reference/eval-definition.md for the full EVAL.md schema, field reference, and conventions.

## Workspace Lifecycle

1. Create workspace directory at `/tmp/claude/agent-spec-{uuid}/`
2. Populate workspace: copy source repo and/or seed files
3. Delete files listed in `delete` (cordyceps — forces agent to produce them)
4. Run `setup` commands if any (e.g., `npm install`)
5. Place the config's `.claude/` into the workspace
6. Inject `_apc.py` and `_apc.ts` emitter libraries
7. Start resource monitor sidecar
8. Run `claude -p` from inside the workspace (CWD isolation)
9. Parse token metrics from JSON output
10. Copy verify.sh into workspace, run it, capture RESULT
11. Stop sidecar, clean up workspace

## Cordyceps Injection

See @.claude/reference/cordyceps.md for the full cordyceps reference — mechanisms, order of operations, and common patterns.

## Scoring Contract

verify.sh must exit 0 always and print `RESULT: PASS` or `RESULT: FAIL`. See @.claude/reference/eval-definition.md for the verify.sh contract and task_context.

## Agent Timeout

Agents run with a 10-minute timeout by default (configurable via `TIMEOUT` env var). If an agent exceeds the timeout, it is terminated and an `agent_timeout` event is logged.

## Cleanup

invoke.py uses an EXIT trap that automatically stops the sidecar, clears ports, and removes the workspace on any exit (success, failure, or signal). Manual cleanup with `/stop` is only needed if the trap itself is bypassed.
