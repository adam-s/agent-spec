# Target Definition

A target is a test fixture that pairs a source project with a task, scoring criteria, and agent configuration. Targets live in `targets/<name>/`.

## Directory Layout

Every target requires these files:

```
targets/<name>/
├── target.yaml              # Source, scoring, agent defaults
├── prompt.md                # Task given to the agent
├── verify.sh                # Scoring script (must be executable)
├── configs/
│   └── <config-name>/
│       └── CLAUDE.md        # Agent instructions for this config variant
└── inject/                  # (optional) Files copied into sandbox before agent runs
```

At least one config directory is required (typically `baseline` or `tuned`).

## target.yaml

### Required Fields

| Field | Type | Description |
| ----- | ---- | ----------- |
| `name` | string | Target identifier. Must match the directory name. |
| `source` | path | Relative path from the target directory to the source repo. External repos use `../../../<repo>`, self-targets use `../../`. |
| `verify` | string | Scoring script filename. Always `verify.sh`. |
| `agent.model` | string | Default model ID (e.g., `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`). |
| `agent.budget` | string | Default max budget in USD (e.g., `"2.00"`). |

### Optional Fields

| Field | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `delete_before_run` | list[string] | `[]` | Files to remove from the sandbox so the agent must produce them from scratch. |
| `setup` | list[string] | `[]` | Shell commands run inside the sandbox before the agent starts. Used for dependency installation, fixture data setup, etc. |

### Example

```yaml
name: csv-reporter
source: ../../../csv-reporter
verify: verify.sh
delete_before_run:
  - report.py
  - test.py
agent:
  model: claude-sonnet-4-6
  budget: 2.00
```

## prompt.md

The task description given verbatim to the agent via `claude -p`.

Conventions:
- Keep it short and concrete — describe the task, not the implementation
- Use `__PORT__` wherever a port number is needed (the harness substitutes the allocated port)
- If the agent should run tests to verify its own work, say so explicitly
- Do not include implementation details the agent should figure out itself

## verify.sh

The scoring script. Must follow the scoring contract exactly:

- Always `exit 0` — the exit code is not the scoring mechanism
- Print test output to stdout
- Print exactly `RESULT: PASS` or `RESULT: FAIL` as the final line of verdict
- If no RESULT line is found, the harness records `N/A`

### Hidden output format contracts

When verify.sh greps for specific strings in test output (e.g., `"4/4 tests passed"`), this creates a hidden contract between the test file's output format and verify.sh's expectations.

If `delete_before_run` removes test files, the agent recreates them with different phrasing, and verify.sh breaks — even though all tests actually pass.

**Fix this in the config**, not in verify.sh. Tell the agent the exact output format that verify.sh expects. Example from a working config:

```markdown
If test.py does not exist, create it. Tests must print individual results
as `PASS: test_name` or `FAIL: test_name`, and a final summary line in
the format `{passed}/{total} tests passed`.
```

### Template

```bash
#!/usr/bin/env bash
set -euo pipefail
OUTPUT=$(python3 test.py 2>&1)
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "4/4 tests passed"; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
```

For targets that start servers, verify.sh must also manage the server lifecycle:
1. Stop any existing process on the port before starting
2. Start the server in background and record the PID
3. Stop the server after tests complete, in all exit paths

## Configs

Each config is a `.claude/` directory that gets swapped into the sandbox, replacing whatever the source project had. The agent sees only the config's instructions.

**Resolution order:** target-specific (`targets/<name>/configs/<config>/`) first, then shared (`targets/_shared/configs/<config>/`).

**Naming conventions:**
- `baseline` — minimal instructions, used to measure what the agent does with little guidance
- `tuned` — improved instructions developed through iteration, the main working config
- Other names for A/B testing specific approaches

The CLAUDE.md inside a config should:
- Tell the agent to read existing files before writing (especially test files)
- Document any output format contracts that verify.sh depends on
- Include conditional instructions for deleted files ("if X exists, read it; if not, create it with this format")

## inject/ Directory

Optional directory of files and subdirectories copied into the sandbox root before the agent starts. Used for:
- Fake run data for self-targets to diagnose
- Sample projects for onboarding tasks
- Pre-built test fixtures

Files in `inject/` are copied by setup commands in target.yaml. Each subdirectory under `inject/` is a named scenario (e.g., `inject/fake-run/`, `inject/sample-app/`).

## Two Categories of Target

**External targets** point at separate source repos. They typically use `delete_before_run` to remove deliverables and test the agent's ability to produce code from scratch.

**Self-targets** point at agent-spec itself (`source: ../../`). They test the harness's own workflows — onboarding, diagnosis, monitoring, improvement. They typically use `setup` and `inject/` to create test scenarios.
