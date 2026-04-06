# Evals

Each eval is an experiment. Challenges define tasks with deterministic pass/fail tests. Configs are `.claude/` directory variants injected into sandboxes. Every config runs against every challenge.

```
challenges × configs = runs
```

See `.claude/reference/eval-definition.md` for the full spec.

## Running an eval

```bash
# List available evals and configs
python3 scripts/cli.py list

# Run one config against all challenges
python3 scripts/cli.py run <eval> <config>

# Run a single challenge
python3 scripts/cli.py run <eval> <config> --challenge <name>

# Compare results
python3 scripts/report.py --all --group-by config
```

## Evals in this repo

| Eval | What it tests | Configs | Challenges |
|------|--------------|---------|------------|
| `token-efficiency` | Do token-saving CLAUDE.md strategies reduce tokens-to-correctness? | 7 instruction styles (baseline through drona23/caveman) | 3 coding tasks (Python, Node.js, WebSocket) |
| `bug-squashing` | Can the bug-squasher product fix real open-source bugs? | 1 (bug-squasher `.claude/`) | 12 real bugs across Python projects |
| `config-comparison` | Baseline vs token-efficient instructions | 2 instruction styles | 2 coding tasks |
| `cordyceps-stress` | Can an agent fix injected bugs? | 1 | 1 (GIF builder) |
| `parallel-isolation` | Do concurrent agents contaminate each other? | 1 | 4 parallel instances |

## Adding an eval

Use `/new-eval` to scaffold the directory structure, or copy an existing eval and modify it.
