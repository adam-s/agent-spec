# Cordyceps

Cordyceps is the pattern of modifying a workspace before the agent sees it. The name comes from the parasitic fungus that rewrites its host's behavior — here, we rewrite the workspace to control what the agent encounters.

The workspace is always disposable. The original source is never modified.

## Why

Cordyceps serves two purposes:

1. **Force the agent to produce work** — delete files so the agent must create them from scratch, rather than reading existing solutions.
2. **Control the experimental conditions** — inject telemetry, swap instructions, corrupt code, or reshape the workspace to test specific agent behaviors.

Without cordyceps, every eval would test "can the agent read and modify existing code." With it, you can test "can the agent build from scratch," "can the agent recover from corruption," or "can the agent work with unfamiliar structure."

## Mechanisms

Cordyceps operates through `invoke.py` flags and EVAL.md frontmatter fields. All modifications happen after the source repo is copied but before the agent starts.

### Delete files (`--delete` / `delete:`)

Remove files so the agent must produce them.

**EVAL.md:**
```yaml
delete:
  - report.py
  - src/utils.py
```

**invoke.py:**
```
--delete "report.py,src/utils.py"
```

Files and directories are both supported. Paths are relative to the workspace root.

### Inject files (`--inject`)

Copy an entire directory into the workspace root. Used for telemetry emitters, test fixtures, or replacement files.

```
--inject path/to/inject-dir/
```

Everything in the inject directory lands at the workspace root. Existing files with the same name are overwritten.

### Seed files (`--seeds` / `seeds/`)

Place starter files into the workspace. Unlike inject, seeds are the *intended* starting state — what the agent is supposed to work with.

**Challenge directory:**
```
challenges/my-task/
  seeds/
    test.py
    data/input.csv
    package.json
```

Seeds are copied before setup runs, so `setup.sh` can install dependencies from seed manifests.

### Setup commands (`--setup` / `setup:`)

Run commands after seeds are placed but before the agent starts.

**EVAL.md:**
```yaml
setup:
  - python3 -m venv .venv
  - .venv/bin/pip install -r requirements.txt --quiet
```

### Swap `.claude/`

The config's `.claude/` directory is placed into the workspace, replacing any `.claude/` from the source repo. This is how different instruction strategies are A/B tested — same workspace, different instructions.

### Built-in injections

The harness always injects:
- `_apc.py` and `_apc.ts` — telemetry emitter libraries
- `verify.sh` — copied into the workspace for scoring

## Order of Operations

1. Copy source repo and/or seed files into workspace
2. Delete files listed in `delete`
3. Inject files from `--inject` directory
4. Run `setup` commands
5. Place config's `.claude/` into workspace
6. Inject emitters (`_apc.py`, `_apc.ts`)
7. Start resource monitor sidecar
8. Launch agent

Steps 2-6 are all cordyceps. The agent sees the workspace only at step 8.

## Common Patterns

### Greenfield: agent builds from scratch

```yaml
delete:
  - src/main.py
  - src/routes.py
```

Keep tests and data, delete implementation. The agent must write the code that makes the tests pass.

### Corruption: agent must diagnose and repair

Don't delete — inject broken versions. Use `--inject` with files that contain subtle bugs (wrong logic, missing imports, syntax errors). The agent must find and fix the corruption. The `cordyceps-stress` eval uses this pattern.

### Scaffold: agent fills in the blanks

Keep the project structure and boilerplate. Delete only the files that require real implementation. Useful for testing whether instructions help the agent work within constraints rather than rewriting everything.

### Config comparison

Same source, same cordyceps, different `.claude/` directories. The only variable is the instructions. This isolates the effect of instruction design.

## Writing New Cordyceps

When designing workspace modifications:

- **Be specific about what you delete.** Deleting too much turns the eval into "can the agent bootstrap an entire project," which tests general capability, not instructions.
- **Keep verify.sh independent.** The scoring script must work regardless of how the agent built the solution. Don't make verify.sh depend on files that cordyceps deleted.
- **Document the expected state.** The prompt should tell the agent what it has (tests, data, dependencies) without revealing what was removed. The agent should experience the workspace as naturally incomplete, not surgically altered.
- **Test the workspace manually.** Before running agents, verify that the workspace after cordyceps is coherent — dependencies resolve, test files reference valid paths, the project isn't broken in ways unrelated to the task.
