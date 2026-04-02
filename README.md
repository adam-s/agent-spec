# agent-spec

Test harness for `.claude/` directories. agent-spec takes any project, sandboxes it, runs agents against it, and uses the signal to iteratively improve the project's `.claude/` — until autonomous agents succeed without human intervention.

## Three Testing Layers

1. **Output testing** — Did the agent produce correct results? Sandbox → run → verify → pass/fail.
2. **Config testing** — Is the `.claude/` well-designed? Score against the component decision tree.
3. **Behavior testing** — Did the agent make good decisions? Analyze event traces for tool choices and efficiency.

## Recursive Architecture

- **Level 0 (Orchestrator):** Human + agent-spec. Launches agents, scores, diagnoses, fixes instructions.
- **Level 1 (Sub-agents):** Disposable Claude instances in sandboxes. Their behavior is the signal.
- **Level 2 (The Product):** The `.claude/` directory. Must be self-sufficient — no knowledge of agent-spec.

## Quick Start

```bash
cd agent-spec/agent-spec

# Run an evaluation
python3 scripts/cli.py run csv-reporter

# Run 3 times to check consistency
python3 scripts/cli.py run csv-reporter --parallel --instances 3

# A/B test two instruction sets
python3 scripts/cli.py run csv-reporter --parallel --configs baseline,experimental

# View results
python3 scripts/cli.py report --all
```

## How It Works

1. **Copies** your project to a disposable sandbox
2. **Swaps** `.claude/` with the config variant under test
3. **Deletes** key files so the agent must produce them (cordyceps injection)
4. **Runs** `claude -p` with your prompt inside the sandbox
5. **Scores** the result with a deterministic `verify.sh` script
6. **Reports** PASS/FAIL with cost and token metrics

The agent never touches your real code.

## Key Concepts

| Concept | Description |
| ------- | ----------- |
| **Eval** | Defined by EVAL.md — frontmatter (config) + body (task prompt) |
| **Config** | A `.claude/` directory variant to test |
| **Sandbox** | Disposable copy in `/tmp/claude/agent-spec-{uuid}/` |
| **Cordyceps** | Modifying the sandbox before the agent sees it |
| **Baseline** | Stored result from a known-good run — the control measurement |
| **Verify script** | `verify.sh` that outputs `RESULT: PASS` or `RESULT: FAIL` |

## Project Structure

```text
agent-spec/                    # Repository root
├── agent-spec/                # The harness (this is the product)
│   ├── scripts/               # Core harness scripts
│   ├── evals/                 # Evaluation definitions (EVAL.md + verify.sh + configs)
│   └── .claude/               # agent-spec's own instructions
│       ├── rules/             # Always-loaded behavioral rules
│       ├── skills/            # On-demand procedures (/iterate, /run-eval, etc.)
│       ├── reference/         # Deep docs including component design framework
│       └── hooks/             # Mechanical enforcement scripts
├── csv-reporter/              # Source project: test fixture
├── hono-websocket-counter/    # Source project: test fixture
└── sqlite-window-queries/     # Source project: test fixture
```

## Requirements

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- Python 3.12+
