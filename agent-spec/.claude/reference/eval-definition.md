# Eval Definition

An eval is an experiment. It defines challenges, configs, and produces runs.

```
challenges × configs = runs
```

That's it. Every eval is this cross-product, regardless of what's being tested.

- A focused eval: 1 challenge × 1 config = 1 run
- A config comparison: 3 challenges × 6 configs = 18 runs
- An ablation test: 1 challenge × 6 configs (each with a component removed) = 6 runs
- A model benchmark: 1 challenge × 1 config × 3 models = 3 runs

The dimensions can grow if we encounter experiments that don't fit. But the structure is always: dimensions × runs = results, stored in one place.

## Directory Layout

### Multi-challenge eval

```
evals/<name>/
├── EVAL.md                          # Experiment definition
├── challenges/
│   ├── csv-reporter/
│   │   ├── prompt.md                # Task for this challenge
│   │   ├── verify.sh               # How to score this challenge
│   │   └── seeds/                   # Files placed into workspace
│   │       ├── test.py
│   │       └── data/sales.csv
│   ├── sqlite-window-queries/
│   │   ├── prompt.md
│   │   ├── verify.sh
│   │   ├── setup.sh                # Optional: npm install, etc.
│   │   └── seeds/
│   │       ├── test.js
│   │       ├── seed.sql
│   │       └── package.json
│   └── hono-websocket-counter/
│       ├── prompt.md
│       ├── verify.sh
│       ├── setup.sh
│       └── seeds/
│           ├── test.js
│           └── package.json
├── configs/
│   ├── A-baseline/CLAUDE.md
│   ├── B-token-efficient/CLAUDE.md
│   └── .../
└── results/                         # All runs stored here
```

### Single-challenge eval

The simplest case — one challenge, inline in the EVAL.md body:

```
evals/<name>/
├── EVAL.md                          # Challenge defined inline (source + prompt in body)
├── verify.sh
├── configs/
│   └── baseline/
│       ├── CLAUDE.md
│       └── settings.json
└── results/
```

Both are the same structure. A single-challenge eval is just the case where `challenges/` is omitted and the challenge is defined inline in the EVAL.md frontmatter + body.

## EVAL.md Format

### Multi-challenge

```markdown
---
name: config-comparison
description: Compare .claude/ instruction styles across coding challenges
model: claude-sonnet-4-6
budget: 2.00
---
```

The frontmatter defines defaults. Each challenge in `challenges/` provides its own prompt, verify, and seeds. Configs in `configs/` are shared across all challenges.

### Single-challenge (inline)

```markdown
---
name: csv-reporter
description: Iterate on csv-reporter instructions
source: ../../../csv-reporter
model: claude-haiku-4-5-20251001
budget: 1.00
delete:
  - report.py
---

Write report.py that reads data/sales.csv and prints statistics.
Run python3 test.py to verify your work passes all tests.
```

When `source:` is present and no `challenges/` directory exists, the eval is a single-challenge experiment. The body is the prompt, `verify.sh` is at the eval root, and the source repo is copied into the workspace.

### Frontmatter Fields

| Field | Required | Type | Description |
| ----- | -------- | ---- | ----------- |
| `name` | Yes | string | Eval identifier. Must match the directory name. |
| `description` | No | string | What this experiment tests. |
| `model` | No | string | Default model. Override per run with `--model`. |
| `budget` | No | string | Default max cost in USD. |
| `source` | No | path | Single-challenge: path to project to copy into workspace. |
| `delete` | No | list | Single-challenge: files to delete from workspace. |
| `setup` | No | list | Single-challenge: commands run before agent starts. |
| `port` | No | integer | Port to allocate. `__PORT__` substituted in prompts. |

## Challenges

A challenge defines one task: what goes into the workspace, what the agent must do, and how to verify.

Each challenge directory contains:

| File | Required | Description |
| ---- | -------- | ----------- |
| `prompt.md` | Yes | Task given to the agent |
| `verify.sh` | Yes | Scoring script — must output `RESULT: PASS` or `RESULT: FAIL` |
| `seeds/` | Yes | Files placed into the workspace before the agent runs |
| `setup.sh` | No | Commands run after seeds are placed (e.g., `npm install`) |

The workspace for each run starts empty, receives the seeds, runs setup, then gets the config's `.claude/` placed in it.

### Prompt Content

When real source material exists for the task (issue reports, user feedback, error messages), use it directly in prompt.md. Sanitize only to remove solution hints (diffs, file paths of the fix) — do not rewrite the content. Rewriting introduces bias: synthetic prompts either reveal too much or strip signal that affects agent behavior. Real inputs carry the natural level of specificity that the agent would encounter in practice.

Wrapper context around the source material is fine: workspace description, environment setup (venv location, test commands), and constraints ("do not modify test files"). These are environment facts, not the stimulus.

When no source material exists (greenfield coding tasks), write the prompt as a realistic task description — what a developer would actually say, not a test specification.

## Configs

A config is a `.claude/` directory variant placed into the workspace. Configs are independent of challenges — the same config is tested against every challenge in the eval.

Configs can contain any `.claude/` components: CLAUDE.md, rules/, skills/, hooks/, agents/, settings.json.

### task_context

When an eval has task-specific requirements that every config must respect (e.g., "don't modify test.py"), the challenge's verify.sh encodes this. Configs can optionally include `permissions.deny` rules to mechanically enforce file protection, but this is the config author's choice — it's part of the instruction style being tested.

## Results

All results for one eval go in `evals/<name>/results/`. Each run produces a directory named by run ID containing events.jsonl, token metrics, and verification output.

For a matrix eval, results are tagged with both challenge and config names so they can be grouped and compared.

## Environment Setup

Sandboxes run on the host machine. Dependencies must be installed without polluting the global environment. setup.sh handles this before the agent starts; verify.sh must also be self-sufficient (the agent may modify the environment).

### Python

Create a `.venv` in the workspace. The agent and verify.sh both use it.

**setup.sh:**

```bash
#!/bin/bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt --quiet
```

**verify.sh:**

```bash
#!/bin/bash
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -r requirements.txt --quiet
OUTPUT=$(.venv/bin/python3 test.py 2>&1)
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "RESULT: PASS"; then echo "RESULT: PASS"; else echo "RESULT: FAIL"; fi
```

**prompt.md** — tell the agent the venv exists:

```markdown
A Python virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.
```

### TypeScript / Node.js

Use npm in the workspace directly. No global installs needed.

**setup.sh:**

```bash
#!/bin/bash
npm install --silent
```

**verify.sh:**

```bash
#!/bin/bash
[ -d node_modules ] || npm install --silent
OUTPUT=$(node test.js 2>&1)
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "RESULT: PASS"; then echo "RESULT: PASS"; else echo "RESULT: FAIL"; fi
```

### Conventions

- setup.sh creates the environment; verify.sh recreates it if missing (agent may have broken it)
- Never use `--break-system-packages` — always isolate with venv or node_modules
- Seeds should include dependency manifests (requirements.txt, package.json) not lockfiles
- Tell the agent about the environment in prompt.md — don't make it guess

## verify.sh

The scoring script. Must follow the scoring contract:

- Always exit 0 — the exit code of verify.sh itself is not the scoring mechanism
- Print `RESULT: PASS` or `RESULT: FAIL` as the verdict
- Can use test exit codes internally (e.g., `python3 test.py; if [ $? -eq 0 ]; then echo "RESULT: PASS"`)
- Only verify.sh prints `RESULT:` — test scripts should use exit codes, not the RESULT protocol. This keeps tests reusable and avoids duplicate RESULT lines in output.

## Extending

If a new experiment doesn't fit challenges × configs, add a new dimension. The structure is always:

```
dimensions × runs = results
```

Possible future dimensions: models (same config, different models), stimuli (same config, different input data), repetitions (same everything, multiple runs for variance).
