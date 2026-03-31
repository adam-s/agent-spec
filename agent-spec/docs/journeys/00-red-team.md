# Journey 0: Red Team

**Purpose:** An adversarial agent reads all journey checklists and systematically attempts to make each item fail. Every failure it finds becomes a bug fix for the harness.

## How It Works

The red team agent is a sub-agent launched by the orchestrator (Level 0). It receives:
1. The journey docs (01-05)
2. Read access to the harness scripts
3. A sandbox to experiment in

Its job: pick a checklist item, design an input that should trigger a failure, run it, and report whether the harness handled it correctly.

## Red Team Protocol

### Phase 1: Read all journeys

Read every checklist item across all 5 journeys. Build a prioritized attack list:
- Items involving edge cases (spaces in paths, empty files, zero tokens)
- Items involving concurrency (parallel port allocation, simultaneous writes)
- Items involving failure cascades (one crash affecting others)
- Items involving boundary conditions (exactly 50% cost increase, 11 simultaneous runs)

### Phase 2: Attack plan

For each item, write:
- **Target:** which checklist item
- **Attack:** specific input or sequence that should trigger the edge case
- **Expected:** what the harness SHOULD do
- **Method:** exact bash commands to execute

### Phase 3: Execute attacks

Run each attack. Record:
- **Actual:** what the harness DID do
- **Verdict:** PASS (handled correctly) or FAIL (bug found)
- **Fix:** for FAILs, describe what needs to change

### Phase 4: Report

Produce a structured report:

```
## Red Team Report — YYYY-MM-DD

### Summary
Attacks: N
Passed: N
Failed: N

### Failures

#### RT-001: [checklist item]
- Attack: [what was tried]
- Expected: [correct behavior]
- Actual: [what happened]
- Fix: [what to change]
- Severity: HIGH/MEDIUM/LOW
```

## Example Attacks

### Attack: Port exhaustion
Target: Journey 3 — "Port range 3100-3110 supports up to 11 simultaneous runs"
```bash
scripts/tuning/parallel-invoke.sh csv-reporter --instances 12 \
  --model claude-haiku-4-5-20251001 --budget 0.10
```
Expected: 11 succeed, 12th gets error or waits. Not: silent port collision.

### Attack: Corrupt baseline
Target: Journey 4 — "Baseline file exists but is corrupt JSON"
```bash
echo "not json" > results/baselines/csv-reporter_baseline.json
scripts/reporting/check-regression.sh <some_run_id>
```
Expected: error message. Not: Python traceback.

### Attack: Inject into .claude/
Target: Journey 5 — "Injecting a .claude/CLAUDE.md — does it survive the swap?"
```bash
mkdir -p /tmp/inject-test/.claude
echo "INJECTED" > /tmp/inject-test/.claude/CLAUDE.md
scripts/run-eval.sh csv-reporter baseline --inject /tmp/inject-test
```
Expected: swap replaces it. Verify sandbox .claude/CLAUDE.md says "A coding project." not "INJECTED".

### Attack: Spaces in paths
Target: Journey 1 — "Source repo with spaces in path works correctly"
```bash
cp -a ../csv-reporter "/tmp/my project with spaces"
# Modify target.yaml source to point to "/tmp/my project with spaces"
scripts/run-eval.sh csv-reporter baseline
```
Expected: sandbox created, eval runs. Not: bash word-splitting errors.

### Attack: Simultaneous save-baseline
Target: Journey 4 — "Two users save baselines simultaneously"
```bash
scripts/reporting/save-baseline.sh run1 &
scripts/reporting/save-baseline.sh run2 &
wait
cat results/baselines/csv-reporter_baseline.json | jq .
```
Expected: valid JSON (one of the two wins). Not: interleaved writes producing corrupt JSON.

### Attack: Self-referencing target
Target: Journey 5 — "Agent running rm -rf / inside sandbox"
```bash
# What if target.yaml source points to agent-spec itself?
# The sandbox would be a copy of agent-spec, agent could see harness scripts
```
Expected: sandbox isolation prevents agent from seeing real harness. Or: target validation rejects self-reference.

## Running the Red Team

Use `/iterate` on agent-spec itself, but instead of improving a target's `.claude/`, the red team agent follows this journey to find bugs in the harness. Every bug found → fix → re-attack → verify.

The red team agent operates at Level 0. Its findings are always Level 0 fixes (harness bugs, not instruction gaps).

## Convergence

The red team converges when:
1. All checklist items across all 5 journeys have been attacked
2. All attacks produce the expected behavior
3. No new attack surfaces discovered in 2 consecutive passes
