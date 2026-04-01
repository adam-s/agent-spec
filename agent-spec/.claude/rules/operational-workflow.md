# Operational Workflow

## Use existing tools — do not reimplement

Every common operation has a script or skill. Before writing any bash to sandbox a repo, check ports, score a run, or view results — check the table below. If a tool exists, use it.

## Skills (slash commands)

| Skill | When to use |
| ----- | ----------- |
| `/run-eval <target> [config]` | Run one agent in a sandbox and score it |
| `/iterate <target>` | Parallel agents → score → diagnose → fix instructions → recurse |
| `/report` | View results: latest, by run_id, or full comparison |
| `/stop` | Halt everything: processes, ports, sandboxes |
| `/new-target` | Scaffold a new evaluation target |

## Scripts

| Script | When to use |
| ------ | ----------- |
| `scripts/run_eval.py <target> [config]` | Run one eval by target name |
| `scripts/invoke.py <source> <config> <prompt>` | Low-level: sandbox + agent + verify |
| `scripts/parallel.py <target> --configs a,b` | A/B test configs in parallel |
| `scripts/parallel.py <target> --models x,y` | Benchmark models in parallel |
| `scripts/parallel.py <target> --instances N` | N reps of same config |
| `scripts/dashboard.py <run_id>` | Monitor a run (live or summary) |
| `scripts/dashboard.py --latest` | Monitor most recent run |
| `scripts/report.py --all` | Full report across all runs |
| `scripts/report.py --all --group-by config` | Compare configs with deltas |
| `scripts/report.py --all --group-by model` | Compare models with deltas |
| `scripts/cleanup.py` | Full state reset (ports, sandboxes, PIDs) |

## Config resolution

Configs are resolved in order:
1. `targets/<target>/configs/<config>/` (target-specific)
2. `targets/_shared/configs/<config>/` (shared across targets)

Shared configs: baseline, token-efficient, structured, workflow, hybrid, drona23.

## Workflow patterns

### One-shot eval
1. `/run-eval target config`
2. `python3 scripts/dashboard.py --latest --summary`

### A/B test configs
1. `python3 scripts/parallel.py target --configs baseline,tuned --model haiku`
2. `python3 scripts/report.py <ids> --group-by config`

### Model benchmark
1. `python3 scripts/parallel.py target baseline --models haiku,sonnet`
2. `python3 scripts/report.py <ids> --group-by model`

### After any failure or stuck state
1. `/stop` — clears everything
2. `python3 scripts/dashboard.py <run_id> --summary` — see what happened
3. `cat /tmp/agent-spec/<run_id>/stderr.log` — agent stderr

### Adding a new target
1. `/new-target`
2. Set `source:` path in target.yaml
3. Use `__PORT__` in prompt.md (not a hardcoded port)
4. Write verify.sh following the scoring contract in @.claude/rules/testing-protocol.md
