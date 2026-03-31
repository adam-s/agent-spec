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

## Scripts (direct invocation)

| Script | When to use |
| ------ | ----------- |
| `scripts/cli/dashboard.sh <run_id>` | Monitor a run (live or post-completion) |
| `scripts/reporting/score.sh <run_id>` | Get pass/fail for a run |
| `scripts/reporting/tokens.sh <run_id>` | Get token metrics for a run |
| `scripts/reporting/compare.sh <id1> <id2>` | Compare two runs side-by-side |
| `scripts/reporting/report.py --all` | Full report across all runs |
| `scripts/sandbox/clear-ports.sh` | Sweep reserved port ranges |
| `scripts/sandbox/cleanup.sh` | Full state reset |
| `scripts/sandbox/track-pid.sh <pid> <port> <purpose>` | Register a background process for cleanup |
| `scripts/tuning/parallel-invoke.sh <target> [config]` | Launch N parallel evals with stimuli injection |
| `scripts/tuning/capture-wireframe.sh <url> <output>` | Screenshot a URL to PNG |

## Workflow patterns

### One-shot eval
1. `/run-eval target config`
2. `/report --latest`

### Parallel iteration
1. `/iterate target` — follows the recursive loop automatically
2. Classify every fix as Level 0 (trainer) or Level 2 (trainee) before applying
3. `/report --all` to compare across iterations

### After any failure or stuck state
1. `/stop` — clears everything
2. Check `scripts/cli/dashboard.sh <run_id>` for what went wrong
3. Check @.claude/reference/bug-catalog.md for known failure patterns

### Adding a new target
1. `/new-target`
2. Set `source:` path in target.yaml
3. Use `__PORT__` in prompt.md (not a hardcoded port)
4. Write verify.sh following the scoring contract in @.claude/rules/testing-protocol.md
