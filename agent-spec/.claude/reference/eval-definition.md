# Eval Definition

An eval is defined by an EVAL.md file with YAML frontmatter (configuration) and a markdown body (the task prompt). This follows the same pattern as SKILL.md and AGENT.md in Claude Code.

## How Workspaces Are Built

A workspace is a disposable directory where an agent runs. It can be built two ways:

**From a source repo:** Copy an existing project directory into the workspace. Use `source:` in frontmatter.

**From seed files:** Assemble the workspace from individual files listed in `seeds:`. The workspace starts empty and only contains what you put in it.

Both can be combined — copy a source repo, then add seed files on top.

## The Eval-Config Relationship

An eval defines the challenge: what files go into the workspace, what the task is, what success looks like. A config defines how to instruct the agent (the `.claude/` directory).

Configs are independent of evals. The same config can be tested across multiple challenges. In a comparison experiment (e.g., 6 configs × 3 challenges = 18 runs), configs and challenges are the two axes of a matrix.

```
EVAL.md (the challenge)
  │
  ├── What goes in the workspace (source and/or seeds)
  ├── What to delete after copying (cordyceps)
  ├── What success looks like (reference + verify.sh)
  ├── The task prompt (body)
  │
  └── task_context:                    ← the bridge to configs
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

**The dependency:** every config must include the eval's task context — the output format contract, required reads, and protected files. Without this, the agent produces correct code but in a format verify.sh doesn't recognize, causing false FAILs.

**In config comparison experiments:** each config varies the instruction STYLE but shares the same task CONTEXT. The style is the independent variable; the task context is the constant.

## Directory Layout

```
evals/<name>/
├── EVAL.md                    # Definition: frontmatter + prompt body
├── verify.sh                  # Scoring script (must be executable)
├── seeds/                     # (optional) Files to assemble into workspace
├── configs/
│   ├── baseline/
│   │   ├── CLAUDE.md          # Agent instructions for this config
│   │   └── settings.json      # Permissions for this config
│   └── <other-configs>/       # Additional configs for comparison
└── inject/                    # (optional) Additional files injected after setup
```

At least one config directory is required (typically `baseline`).

## EVAL.md Format

### Source-based workspace (copy a project)

```markdown
---
name: csv-reporter
description: Test agent's ability to write code that passes an existing test suite
source: ../../../csv-reporter
model: claude-haiku-4-5-20251001
budget: 1.00
delete:
  - report.py
reference:
  type: test-file
  file: test.py
  pass_pattern: "5/5 tests passed"
task_context:
  required_reads:
    - test.py
    - data/sales.csv
  protected_files:
    - test.py
    - data/*
---

Write report.py that reads data/sales.csv and prints statistics.
Run python3 test.py to verify your work passes all tests.
```

### Seed-based workspace (assemble from parts)

```markdown
---
name: csv-challenge
description: Can the agent write a CSV analysis script from seed files and a test suite?
model: claude-haiku-4-5-20251001
budget: 1.00
seeds:
  - data/sales.csv
  - test.py
reference:
  type: test-file
  file: test.py
  pass_pattern: "5/5 tests passed"
task_context:
  required_reads:
    - test.py
    - data/sales.csv
  protected_files:
    - test.py
    - data/*
---

Write report.py that reads data/sales.csv and prints statistics.
Run python3 test.py to verify your work passes all tests.
```

### Frontmatter Fields

| Field | Required | Type | Description |
| ----- | -------- | ---- | ----------- |
| `name` | Yes | string | Eval identifier. Must match the directory name. |
| `description` | No | string | What this eval tests. |
| `source` | No | path | Path to a project directory to copy into the workspace. |
| `seeds` | No | list | Files to copy into the workspace (relative to eval dir or absolute). |
| `model` | No | string | Model to use. Default: `claude-haiku-4-5-20251001` |
| `budget` | No | string | Max cost in USD. Default: `1.00` |
| `delete` | No | list | Files to delete from workspace after copying source. |
| `setup` | No | list | Shell commands run inside workspace before agent starts. |
| `port` | No | integer | Port to allocate. `__PORT__` in body gets substituted. |
| `reference` | No | object | What defines success. See reference types below. |
| `task_context` | No | object | Task-specific context every config must include. |

Either `source` or `seeds` (or both) must be provided. The workspace must have files in it.

### Body

The markdown body after the second `---` is the task prompt given to the agent.

## Reference Types

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
```

## verify.sh

The scoring script. Must follow the scoring contract:

- Always `exit 0` — the exit code is not the scoring mechanism
- Print exactly `RESULT: PASS` or `RESULT: FAIL` as the final verdict line
- If no RESULT line is found, the harness records `N/A`

## task_context

The bridge between the eval and its configs:

| Field | Type | Description |
| ----- | ---- | ----------- |
| `output_contract` | string | The exact output format verify.sh greps for. |
| `required_reads` | list | Files the agent should read before writing code. |
| `protected_files` | list | Files the agent must not modify (becomes permissions.deny). |

## Configs

Each config is a `.claude/` directory placed into the workspace. Configs are independent — the same config can be used across multiple evals/challenges.

Every config must include the eval's task context (output contract, required reads, protected files). The instruction STYLE varies; the task CONTEXT is constant.
