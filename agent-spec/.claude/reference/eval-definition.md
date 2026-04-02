# Eval Definition

An eval is defined by an EVAL.md file with YAML frontmatter (configuration) and a markdown body (the task prompt). This follows the same pattern as SKILL.md and AGENT.md in Claude Code.

## The Eval-Config Relationship

An eval defines the experiment: what project, what task, what success looks like. A config defines how to instruct the agent. The eval is the constant; configs are the variable.

```
EVAL.md (the experiment)
  │
  ├── What to sandbox (source)
  ├── What to delete (cordyceps)
  ├── What success looks like (reference + verify.sh)
  ├── The task prompt (body)
  │
  └── task_context:                    ← the bridge
        output_contract: "5/5 tests passed"
        required_reads: [test.py, data/sales.csv]
        protected_files: [test.py, data/*]
```

```
configs/<name>/ (the variable)
  │
  ├── CLAUDE.md — instruction style (the thing being tested)
  ├── settings.json — permissions
  ├── rules/, skills/, hooks/ — optional components
  │
  └── MUST include task_context from EVAL.md
```

**The dependency:** configs are not independent of the eval. Every config must include the eval's task context — the output format contract, required reads, and protected files. Without this, the agent produces correct code but in a format verify.sh doesn't recognize, causing false FAILs.

**In config comparison experiments:** each config varies the instruction STYLE (concise vs structured vs workflow-gated) but shares the same task CONTEXT. The style is the independent variable; the task context is the constant.

## Directory Layout

```
evals/<name>/
├── EVAL.md                    # Definition: frontmatter (config) + body (prompt)
├── verify.sh                  # Scoring script (must be executable)
├── configs/
│   ├── baseline/
│   │   ├── CLAUDE.md          # Agent instructions for this config
│   │   └── settings.json      # Permissions for this config
│   └── <other-configs>/       # Additional configs for comparison
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
task_context:
  output_contract: "{passed}/{total} tests passed"
  required_reads:
    - test.py
    - data/sales.csv
  protected_files:
    - data/*
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
| `task_context` | No | object | Task-specific context every config must include. See below. |

### task_context

The bridge between the eval and its configs. When the orchestrator creates configs for this eval, it must include this context in every config's CLAUDE.md:

| Field | Type | Description |
| ----- | ---- | ----------- |
| `output_contract` | string | The exact output format verify.sh greps for. |
| `required_reads` | list | Files the agent should read before writing code. |
| `protected_files` | list | Files the agent must not modify (becomes permissions.deny). |

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

This is why `task_context.output_contract` exists — it makes the hidden contract explicit so every config can include it.

## Configs

Each config is a `.claude/` directory swapped into the sandbox. The agent sees only the config's instructions. Configs live inside the eval: `evals/<eval>/configs/<config>/`

**Naming:** `baseline` is the control config. Additional configs for A/B testing vary the instruction style.

### Every config must include task context

A config is NOT just generic coding rules. It must include the eval's task context:

1. **Output contract** — the exact format verify.sh expects
2. **Required reads** — files the agent should read before writing
3. **Protected files** — files the agent must not modify (in settings.json permissions.deny)

Without task context, the agent produces correct code in a format verify.sh doesn't recognize. This causes false FAILs — the code works but the eval reports failure.

### Config comparison experiments

When comparing multiple configs, each config varies the instruction STYLE but shares the same task CONTEXT:

- **Variable (what differs):** CLAUDE.md structure, rules, skills, hooks — the instruction philosophy
- **Constant (what's shared):** output contract, required reads, protected files — the task knowledge

The experiment measures which instruction style produces the best cost-to-correctness for the same task.
