# Testing Protocol

## Targets

Each target is a directory in `targets/` with:

- `target.yaml` — source repo path, verify script, setup commands, agent settings
- `prompt.md` — the task given to the agent
- `verify.sh` — scoring script that prints `RESULT: PASS` or `RESULT: FAIL`
- `configs/` — `.claude/` directories to swap in (each is a test variant)

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

## Scoring Contract

verify.sh must:
- Exit 0 (even on test failure — exit code is not the scoring mechanism)
- Print test output to stdout
- Print exactly `RESULT: PASS` or `RESULT: FAIL` as the final verdict

## Cleanup

Always run `/stop` if a run fails mid-execution. The SubagentStop hook handles automatic cleanup when agents terminate.

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
