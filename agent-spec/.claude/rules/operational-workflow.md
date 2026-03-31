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
| `scripts/cli/dashboard.sh <run_id>` | Monitor a run (live or post-completion) |
| `scripts/reporting/score.sh <run_id>` | Get pass/fail for a run |
| `scripts/reporting/tokens.sh <run_id>` | Get token metrics for a run |
| `scripts/reporting/report.py --all` | Full report across all runs |
| `scripts/reporting/report.py --all --group-by config` | Compare configs with deltas |
| `scripts/reporting/report.py --all --group-by model` | Compare models with deltas |
| `scripts/reporting/report.py --compare <id1> <id2>` | Side-by-side two-run diff |
| `scripts/reporting/save-baseline.sh <run_id>` | Save a run as the baseline for its target/config |
| `scripts/reporting/check-regression.sh <run_id>` | Compare against saved baseline (REGRESSION or OK) |
| `scripts/sandbox/clear-ports.sh` | Sweep reserved port ranges |
| `scripts/sandbox/cleanup.sh` | Full state reset |
| `scripts/sandbox/track-pid.sh <pid> <port> <purpose>` | Register a background process for cleanup |
| `scripts/tuning/parallel-invoke.sh <target> [config]` | Launch N parallel evals with stimuli injection |
| `scripts/tuning/parallel-invoke.sh <target> --configs a,b` | A/B test two configs in parallel |
| `scripts/tuning/parallel-invoke.sh <target> --models x,y` | Benchmark two models in parallel |
| `scripts/tuning/capture-wireframe.sh <url> <output>` | Screenshot a URL to PNG |

## Workflow patterns

### One-shot eval
1. `/run-eval target config`
2. `/report --latest`

### A/B test configs
1. `parallel-invoke.sh target --configs baseline,tuned --model haiku`
2. `report.py <id1> <id2> --group-by config` or `report.py --compare <id1> <id2>`

### Model benchmark
1. `parallel-invoke.sh target baseline --models haiku,sonnet`
2. `report.py <id1> <id2> --group-by model`

### Regression check
1. Save a known-good run: `save-baseline.sh <run_id>`
2. After changes, re-run: `/run-eval target config`
3. Check: `check-regression.sh <new_run_id>`

### Parallel iteration
1. `/iterate target` — follows the recursive loop
2. Classify every fix as Level 0 (trainer) or Level 2 (trainee) before applying
3. Save baseline at convergence: `save-baseline.sh <run_id>`

### After any failure or stuck state
1. `/stop` — clears everything
2. Check `scripts/cli/dashboard.sh <run_id>` for what went wrong
3. Check @.claude/reference/bug-catalog.md for known failure patterns

### Adding a new target
1. `/new-target`
2. Set `source:` path in target.yaml
3. Use `__PORT__` in prompt.md (not a hardcoded port)
4. Write verify.sh following the scoring contract in @.claude/rules/testing-protocol.md
