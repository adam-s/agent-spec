# Journey 1: First Eval

**Capabilities tested:** single eval, /new-target, /report, sandbox lifecycle, port management, cleanup, archiving

## Scenario

You have a project with tests. You want to see if an agent can build it from a prompt, with no `.claude/` instructions.

## Steps

### 1. Scaffold the target

```bash
# /new-target walks you through this interactively, but the manual steps are:
mkdir -p targets/my-project/configs/baseline
```

Create `targets/my-project/target.yaml`:
```yaml
name: my-project
source: ../../../my-project
verify: verify.sh
delete_before_run:
  - main-file.ext
setup:
  - npm install
agent:
  model: claude-haiku-4-5-20251001
  budget: 0.50
```

Create `targets/my-project/prompt.md` (use `__PORT__` not a hardcoded port):
```
Write main-file.ext that does X on port __PORT__.

Run the tests to verify: npm test
```

Create `targets/my-project/verify.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-3100}"
cd "$(dirname "$0")"
OUTPUT=$(npm test 2>&1) || true
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "tests passed"; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
```

Create `targets/my-project/configs/baseline/CLAUDE.md`:
```
A coding project.
```

### 2. Run the eval

```bash
scripts/run-eval.sh my-project baseline
```

### 3. View results

```bash
python3 scripts/report.py --latest
scripts/dashboard.sh <run_id>
scripts/score.sh <run_id>
scripts/tokens.sh <run_id>
```

## Verification Checklist

### Sandbox lifecycle
- [ ] Sandbox created at `/tmp/claude/agent-spec-{uuid}/` (8-char hex UUID)
- [ ] Sandbox is a complete copy of source repo (`diff -r` shows only expected deletions)
- [ ] Source repo is UNMODIFIED after eval (checksum before == checksum after)
- [ ] `delete_before_run` files are absent from sandbox before agent starts
- [ ] `delete_before_run` files still exist in source repo (never touched)
- [ ] Setup commands run inside sandbox CWD (not in harness directory)
- [ ] Setup command failure is non-fatal (warning printed, eval continues)
- [ ] `.claude/` in sandbox is replaced with config variant (not merged, fully replaced)
- [ ] `_apc.py` and `_apc.ts` injected into sandbox root
- [ ] Sandbox removed after eval completes (unless `--keep`)
- [ ] With `--keep`, sandbox persists and contains agent's produced files

### Port management
- [ ] Port allocated from 3100-3110 range
- [ ] `__PORT__` in prompt.md replaced with allocated port number
- [ ] `PORT` env var passed to verify.sh
- [ ] `cleanup.sh` runs before eval starts (no stale processes)
- [ ] `cleanup.sh` runs after eval completes (no orphaned servers)
- [ ] If port 3100 is occupied, next free port (3101+) is allocated
- [ ] Agent's produced code uses the allocated port (grep for hardcoded 3100)

### Agent invocation
- [ ] `claude -p` runs with CWD set to sandbox (not harness)
- [ ] Model matches target.yaml or `--model` override
- [ ] Budget matches target.yaml or `--budget` override
- [ ] `--output-format json` captures structured output
- [ ] `--dangerously-skip-permissions` is set (sandbox is disposable)
- [ ] Exit code 0 logged as `agent_complete`, non-zero as `agent_error`
- [ ] Duration measured in milliseconds (not seconds with rounding errors)

### Verification
- [ ] verify.sh copied into sandbox before execution
- [ ] verify.sh runs with `PORT` and `AGENT_SPEC_RUN_ID` env vars
- [ ] verify.sh output contains individual test results (PASS: / FAIL:)
- [ ] Final line is exactly `RESULT: PASS` or `RESULT: FAIL` (no trailing whitespace)
- [ ] verify.sh exits 0 even when tests fail (exit code is not the scoring mechanism)
- [ ] Each `PASS:` line emits a `test_passed` event
- [ ] Each `FAIL:` line emits a `test_failed` event
- [ ] Final `RESULT:` emits a `score` event

### Event logging
- [ ] Events written to `/tmp/agent-spec/{run_id}/events.jsonl`
- [ ] Every event has `ts` (ISO8601), `level`, `src`, `event`, `msg`, `data`
- [ ] `agent_started` event contains target, config, model, budget, port
- [ ] `agent_complete` or `agent_error` event contains exit_code, duration_ms
- [ ] `token_update` event contains input, output, cache_create, cache_read, cost_usd, turns
- [ ] `resource_snapshot` events appear every 30s during eval
- [ ] `score` event contains result: PASS or FAIL
- [ ] Events are valid JSONL (each line parseable by `jq`)

### Archiving
- [ ] `results/{run_id}/` directory created
- [ ] `results/{run_id}/events.jsonl` is a copy of the run events
- [ ] `results/{run_id}/output.json` contains raw `claude -p` output
- [ ] `results/{run_id}/stderr.log` contains agent stderr
- [ ] `results/{run_id}/produced/` contains agent-produced .py/.js/.ts files
- [ ] `node_modules/` excluded from produced archive
- [ ] `_apc.*` files excluded from produced archive

### Reporting
- [ ] `report.py --latest` shows this run
- [ ] `report.py <run_id>` shows this run
- [ ] `report.py --all` includes this run in the full table
- [ ] `dashboard.sh <run_id>` shows event timeline
- [ ] `score.sh <run_id>` prints pass/fail and test counts
- [ ] `tokens.sh <run_id>` prints input, output, cost, turns, duration
- [ ] All reports handle missing data gracefully (no crashes on partial events)

### Edge cases
- [ ] Running same target twice in a row succeeds (no port collision from previous)
- [ ] Running with `--budget 0.01` terminates quickly without hanging
- [ ] Running with nonexistent target prints error and exits 1
- [ ] Running with nonexistent config prints error and exits 1
- [ ] Source repo with spaces in path works correctly
- [ ] Source repo with no `.claude/` directory works (swap creates one)
- [ ] verify.sh that prints no RESULT line results in N/A score (not crash)
