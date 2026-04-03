# Operational Workflow

## Use existing tools — do not reimplement

Every common operation has a script or skill. Before writing any bash to build a workspace, check ports, score a run, or view results — check the table below. If a tool exists, use it.

## Skills (slash commands)

| Skill | When to use |
| ----- | ----------- |
| `/run-eval <eval> [config]` | Run one agent in a workspace and score it |
| `/iterate <eval>` | Parallel agents → score → diagnose → fix instructions → recurse |
| `/report` | View results: latest, by run_id, or full comparison |
| `/stop` | Halt everything: processes, ports, sandboxes |
| `/new-eval` | Scaffold a new evaluation |

## Scripts

| Script | When to use |
| ------ | ----------- |
| `scripts/run_eval.py <eval> [config]` | Run one eval by name |
| `scripts/invoke.py <source> <config> <prompt>` | Low-level: workspace + agent + verify |
| `scripts/parallel.py <eval> --configs a,b` | A/B test configs in parallel |
| `scripts/parallel.py <eval> --models x,y` | Benchmark models in parallel |
| `scripts/parallel.py <eval> --instances N` | N reps of same config |
| `scripts/watch.py` | Live vitest-style renderer (pipe from --stream or --latest) |
| `scripts/dashboard.py <run_id>` | Monitor a run (live or summary) |
| `scripts/dashboard.py --latest` | Monitor most recent run |
| `scripts/dashboard.py <id> --stream` | Compact no-color output (grep-friendly) |
| `scripts/dashboard.py --diff <id1> <id2>` | Config diff between two runs |
| `scripts/dashboard.py --parallel <id>` | Multi-instance status table |
| `scripts/report.py --all` | Full report across all runs |
| `scripts/report.py --all --group-by config` | Compare configs with deltas |
| `scripts/report.py --all --group-by model` | Compare models with deltas |
| `scripts/report.py --compare <id1> <id2>` | Side-by-side two-run diff |
| `scripts/report.py --session <session_id>` | Iterate session report by depth |
| `scripts/report.py --score <run_id>` | Print PASS/FAIL result |
| `scripts/report.py --tokens <run_id>` | Print token breakdown for a run |
| `scripts/report.py --tokens --session <session_id>` | Cost rollup across iterate session |
| `scripts/report.py --baseline save <run_id>` | Save run as baseline for regression detection |
| `scripts/report.py --baseline check <run_id>` | Compare run against saved baseline |
| `scripts/system_monitor.py` | One-shot system resource status |
| `scripts/cleanup.py` | Full state reset (ports, sandboxes, PIDs) |

## Config resolution

Configs live inside the eval: `evals/<eval>/configs/<config>/`

Each config is a complete `.claude/` directory placed into the workspace. Every config MUST include task-specific context — especially the output format contract that verify.sh depends on. Generic configs without task context will fail because the agent produces output in a different format than verify.sh expects.

## Workflow patterns

### One-shot eval

1. `/run-eval eval config`
2. `python3 scripts/dashboard.py --latest --summary`

### A/B test configs

1. `python3 scripts/parallel.py eval --configs baseline,experimental --model haiku`
2. `python3 scripts/report.py <ids> --group-by config`

### Model benchmark

1. `python3 scripts/parallel.py eval baseline --models haiku,sonnet`
2. `python3 scripts/report.py <ids> --group-by model`

### After any failure or stuck state

1. `/stop` — clears everything
2. `python3 scripts/dashboard.py <run_id> --summary` — see what happened
3. `cat /tmp/agent-spec/<run_id>/stderr.log` — agent stderr

### Adding a new eval

1. `/new-eval`
2. Edit EVAL.md: set `source:` path, `reference:`, and the prompt body
3. Use `__PORT__` in the prompt body (not a hardcoded port)
4. Write verify.sh following the scoring contract in @.claude/reference/iteration/testing-protocol.md
