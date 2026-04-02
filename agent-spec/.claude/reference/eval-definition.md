# Eval Definition

An eval is defined by an EVAL.md file with YAML frontmatter (configuration) and a markdown body (the task prompt). This follows the same pattern as SKILL.md and AGENT.md in Claude Code.

## Directory Layout

```
evals/<name>/
├── EVAL.md                    # Definition: frontmatter (config) + body (prompt)
├── verify.sh                  # Scoring script (must be executable)
├── configs/
│   └── baseline/
│       ├── CLAUDE.md          # Agent instructions for this config
│       └── settings.json      # Permissions for this config
└── inject/                    # (optional) Files copied into sandbox
```

At least one config directory is required (typically `baseline`).

## EVAL.md Format

```markdown
---
name: csv-reporter
description: Test agent's ability to write a Python data analysis script
source: ../../../csv-reporter
model: claude-haiku-4-5-20251001
budget: 1.00
delete:
  - report.py
  - test.py
setup:
  - pip install -r requirements.txt
reference:
  type: test-file
  file: test.py
  pass_pattern: "5/5 tests passed"
---

Write report.py that reads data/sales.csv and prints these 5 statistics...
```

### Frontmatter Fields

| Field | Required | Type | Description |
| ----- | -------- | ---- | ----------- |
| `name` | Yes | string | Eval identifier. Must match the directory name. |
| `description` | No | string | What this eval tests (for humans and orchestrator). |
| `source` | Yes | path | Path to the project folder to sandbox. |
| `model` | No | string | Model to use. Default: `claude-haiku-4-5-20251001` |
| `budget` | No | string | Max cost in USD. Default: `1.00` |
| `delete` | No | list | Files to delete from sandbox so the agent must produce them. |
| `setup` | No | list | Shell commands run inside sandbox before agent starts. |
| `port` | No | integer | Port to allocate. `__PORT__` in body gets substituted. |
| `reference` | No | object | What defines success. See reference types below. |

### Body

The markdown body after the second `---` is the task prompt given verbatim to the agent via `claude -p`.

Conventions:
- Keep it short and concrete — describe the task, not the implementation
- Use `__PORT__` wherever a port number is needed
- If the agent should run tests to verify its own work, say so explicitly

## Reference Types

The `reference` field in frontmatter defines what success looks like:

```yaml
# Test file — run it, grep for pattern
reference:
  type: test-file
  file: test.js
  pass_pattern: "tests passed"

# Screenshot — compare result to reference image
reference:
  type: screenshot
  file: reference.png

# Exit code — command succeeds
reference:
  type: exit-code
  command: "pnpm build && pnpm lint"

# API response — endpoint returns expected data
reference:
  type: api-response
  endpoint: /api/search?q=test
  expected: expected-response.json
```

## verify.sh

The scoring script. Must follow the scoring contract:

- Always `exit 0` — the exit code is not the scoring mechanism
- Print test output to stdout
- Print exactly `RESULT: PASS` or `RESULT: FAIL` as the final verdict line
- If no RESULT line is found, the harness records `N/A`

### Hidden output format contracts

When verify.sh greps for specific strings in test output (e.g., `"5/5 tests passed"`), this creates a hidden contract. If `delete` removes test files and the agent recreates them with different phrasing, verify.sh breaks even though all tests actually pass.

**Fix this in the config**, not in verify.sh. Tell the agent the exact output format that verify.sh expects.

## Configs

Each config is a `.claude/` directory swapped into the sandbox. The agent sees only the config's instructions.

**Naming:** `baseline` is the control config. Additional configs for A/B testing (e.g., `structured`, `token-efficient`).

The CLAUDE.md inside a config should:
- Tell the agent to read existing files before writing (especially test files)
- Document output format contracts that verify.sh depends on
- Use permissions.deny in settings.json for files the agent must not modify
