# Journey 6: Onboard an External Project

**Capabilities tested:** /new-target, config creation, prompt writing, verify.sh contract, A/B testing, multi-config comparison, full iteration cycle

## Scenario

You have an existing project with tests (like testing-claude-agent, or any repo with a test suite). You want to bring it into agent-spec so you can iteratively develop its `.claude/` directory using all 9 capabilities.

This journey documents the translation from "manual testing project" to "agent-spec target."

## What You're Translating

An external project typically has:
- Source code the agent must produce
- Test files that verify correctness
- Possibly multiple `.claude/` configs to compare
- Manual run scripts

Agent-spec replaces all the manual orchestration with:
- `target.yaml` — declares the source, what to delete, how to verify
- `prompt.md` — the task given to the agent
- `verify.sh` — scoring contract (RESULT: PASS/FAIL)
- `configs/` — each `.claude/` variant as a named directory

## Steps

### 1. Identify the deliverables

What file(s) must the agent produce? These go in `delete_before_run`.
What test command verifies correctness? This goes in `verify.sh`.
What's the task description? This goes in `prompt.md`.

### 2. Scaffold the target

```bash
/new-target
# Or manually:
mkdir -p targets/my-project/configs/baseline
```

### 3. Write target.yaml

```yaml
name: my-project
source: ../../../my-project          # relative path to source repo
verify: verify.sh
delete_before_run:
  - output-file.ext                  # file(s) the agent must produce
setup:
  - npm install                      # dependency setup
agent:
  model: claude-haiku-4-5-20251001   # cheapest model for iteration
  budget: 0.50
```

### 4. Write prompt.md

Translate the task description. Use `__PORT__` for any port references.

```
Write output-file.ext that does X.

Run the tests to verify: npm test
```

### 5. Write verify.sh

Follow the scoring contract: exit 0 always, print RESULT: PASS or RESULT: FAIL.

```bash
#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-3100}"

OUTPUT=$(npm test 2>&1) || true
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "tests passed"; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
```

If the project starts a server, verify.sh must stop it in all exit paths.

### 6. Create config variants

For each `.claude/` variant you want to test:

```bash
mkdir -p targets/my-project/configs/baseline
echo "A coding project." > targets/my-project/configs/baseline/CLAUDE.md

mkdir -p targets/my-project/configs/structured
# Copy a full .claude/ directory with rules/, skills/, etc.
cp -a path/to/structured/.claude/* targets/my-project/configs/structured/
```

### 7. Run first eval

```bash
/run-eval my-project baseline
```

### 8. A/B test all configs

```bash
scripts/parallel.sh my-project \
  --configs baseline,structured,hybrid \
  --model claude-haiku-4-5-20251001 --budget 0.50
```

```bash
python3 scripts/report.py <id1> <id2> <id3> --group-by config
```

### 9. Iterate on the best config

```bash
/iterate my-project
```

## Translating from testing-claude-agent

The predecessor project (testing-claude-agent) used:
- Git worktrees for isolation → agent-spec uses `/tmp` sandboxes
- `scripts/run-agent.sh` → agent-spec uses `scripts/run-eval.sh`
- `configs/A-baseline/` through `configs/F-drona23/` → agent-spec uses `targets/{name}/configs/`
- `challenges/` with seed files and tests → agent-spec uses source repos with `delete_before_run`
- Manual `report.py` → agent-spec has `report.py --group-by config` with deltas
- Sequential runs to avoid port collision → agent-spec pre-assigns ports for parallel runs
- `gitignore-swap.sh` for isolation → agent-spec copies to `/tmp` (no gitignore needed)

The same 3 challenges (csv-reporter, sqlite-window-queries, hono-websocket-counter) are already agent-spec targets. The 6 configs can be added as config variants.

## Verification Checklist

### Target setup

- [ ] target.yaml source path resolves to the external project
- [ ] delete_before_run lists every file the agent must produce from scratch
- [ ] delete_before_run does NOT list test files, seed data, or dependencies
- [ ] setup commands install all dependencies the agent needs
- [ ] prompt.md describes the task clearly without referencing agent-spec
- [ ] prompt.md uses `__PORT__` for any port references (not hardcoded)
- [ ] verify.sh follows scoring contract: exits 0, prints RESULT: PASS or RESULT: FAIL
- [ ] verify.sh stops any servers it starts (in all exit paths)
- [ ] verify.sh reads PORT from environment: `PORT="${PORT:-3100}"`

### Config translation

- [ ] Each external `.claude/` config is a separate directory in `configs/`
- [ ] Configs contain only `.claude/` content (CLAUDE.md, rules/, skills/, etc.)
- [ ] No config references external project paths or agent-spec paths
- [ ] Baseline config exists (minimal instructions for comparison)
- [ ] Each config tested individually with `/run-eval` before comparison

### First run validation

- [ ] `/run-eval my-project baseline` completes without error
- [ ] Sandbox contains the test files and seed data
- [ ] Agent-produced files appear in `results/{run_id}/produced/`
- [ ] verify.sh runs and produces RESULT line
- [ ] Score event in events.jsonl matches verify.sh output

### A/B comparison

- [ ] `--configs` runs all variants in parallel with unique ports
- [ ] `--group-by config` shows meaningful cost/token deltas between variants
- [ ] Pass rate computed correctly (some configs may fail)
- [ ] Results reproducible (running twice gives similar ordering)
- [ ] High-variance tasks (like WebSocket) need 3+ reps for meaningful comparison

### Iteration readiness

- [ ] Target works with `/iterate` (parallel launch, score, diagnose cycle)
- [ ] Regression baseline saved for the best config
- [ ] New `.claude/` improvements don't reference agent-spec internals
- [ ] Target can be handed to a fresh session with zero context

### Edge cases

- [ ] External project with no existing `.claude/` → baseline config provides one
- [ ] External project with complex `.claude/` (rules + skills + agents) → all copied to config
- [ ] External project with multiple test commands → verify.sh chains them
- [ ] External project that needs a running server → verify.sh manages server lifecycle
- [ ] External project with large dependencies → setup handles install (may be slow)
- [ ] Port-dependent project → prompt.md uses `__PORT__`, test.js reads `process.env.PORT`
