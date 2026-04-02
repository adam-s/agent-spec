# Testing Protocol

## Targets

See @.claude/reference/target-definition.md for the full target schema, field reference, and conventions.

## Sandbox Lifecycle

1. Copy source repo to `/tmp/claude/agent-spec-{uuid}/`
2. Delete files listed in `delete_before_run` (forces agent to produce them)
3. Run `setup` commands if any (e.g., `npm install`)
4. Swap `.claude/` with the test config
5. Inject `_apc.py` and `_apc.ts` emitter libraries
6. Start resource monitor sidecar
7. Run `claude -p` from inside the sandbox (CWD isolation)
8. Parse token metrics from JSON output
9. Copy verify.sh into sandbox, run it, capture RESULT
10. Stop sidecar, clean up sandbox

## Cordyceps Injection

The harness can override or inject code into any project it tests. Like the cordyceps fungus that takes over its host, agent-spec can:

- **Delete files** (`delete_before_run`) — Remove source files so the agent must produce them from scratch
- **Inject emitters** (`_apc.py`, `_apc.ts`) — Add telemetry the original project doesn't have
- **Swap `.claude/`** — Replace the project's instructions entirely
- **Inject verify scripts** — Add scoring logic the project knows nothing about
- **Inject setup scripts** — Run arbitrary commands before the agent starts
- **Modify source** — Any file in the sandbox can be altered, added, or replaced before the agent sees it

The original project is never modified. Only the disposable sandbox copy is affected. This means any project can become a test target without changing a single line of its own code.

To add custom injections, put files in `targets/<name>/inject/` and add copy commands to the target's `setup` field.

## Scoring Contract

verify.sh must exit 0 always and print `RESULT: PASS` or `RESULT: FAIL`. See @.claude/reference/target-definition.md for the full verify.sh contract, hidden output format contracts, and how to handle them in configs.

## Agent Timeout

Agents run with a 10-minute timeout by default (configurable via `TIMEOUT` env var). If an agent exceeds the timeout, it is terminated and an `agent_timeout` event is logged.

## Cleanup

invoke.py uses an EXIT trap that automatically stops the sidecar, clears ports, and removes the sandbox on any exit (success, failure, or signal). Manual cleanup with `/stop` is only needed if the trap itself is bypassed (e.g., SIGKILL).

## Bug Catalog

When a new class of bug is discovered during iterations, document it in `.claude/reference/bug-catalog.md` using this format:

```
## BNN: Short name

**Story:** What happened (the specific incident)
**Impact:** What broke and how badly
**General principle:** The generalized lesson (not specific to one target)
**Authoritative rule:** The concrete rule to follow going forward
```

This catalog is the institutional memory of the harness. Every iteration that discovers a new failure mode should add an entry.
