# agent-spec

Test harness for `.claude/` directories. Sandboxes projects, runs agents, scores results, and iteratively improves instructions until agents succeed without human intervention.

## Requirements

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- Python 3.12+
- Node.js 18+ (for JavaScript challenges)
- `ANTHROPIC_API_KEY` environment variable set

## Quick Start

```bash
git clone <repo> && cd agent-spec
git submodule update --init
cd agent-spec

# List available evals and configs
python3 scripts/cli.py list

# Run the token-efficiency eval (compares 3 CLAUDE.md strategies)
python3 scripts/cli.py run token-efficiency A-baseline
python3 scripts/cli.py run token-efficiency B-drona23
python3 scripts/cli.py run token-efficiency C-caveman

# Generate a results summary
python3 scripts/summarize.py token-efficiency --filter-eval
```

See [evals/token-efficiency/](agent-spec/evals/token-efficiency/) for a complete worked example with walkthrough.

## Structure

```text
agent-spec/
├── agent-spec/        # The harness (orchestrator, evals, scripts)
├── products/          # .claude/ configs being developed
├── targets/           # Test subject apps for evals
└── submodules/        # Third-party repos (git submodule)
```

## How It Works

An eval defines **challenges** (coding tasks with deterministic tests) and **configs** (`.claude/` directory variants). The harness runs every config against every challenge in isolated sandboxes, measures tokens and cost, and reports the results.

```text
challenges x configs = runs
```

Each run: sandbox the project, inject the config's `.claude/`, give the agent the prompt, let it work, run `verify.sh`. The agent doesn't decide if it's done -- the test decides. The primary metric is **tokens-to-correctness**: not just pass/fail, but how many tokens it took to get there.
