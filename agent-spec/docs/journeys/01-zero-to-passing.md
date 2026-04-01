# Journey 1: Zero to Passing

**Goal:** Take a target that fails with baseline instructions and iterate until all instances pass.

**What this exercises:** The core iteration loop — parallel runs, failure diagnosis, fix classification, convergence detection, and the full monitoring stack.

## Pick Your Target

Use `csv-reporter` for a fast loop (~30s per run, cheap with haiku):

```bash
python3 scripts/run_eval.py csv-reporter baseline
python3 scripts/dashboard.py --latest --summary
```

If the baseline already passes, make it harder — delete more files or tighten the verify.sh criteria. The point is to start from failure.

## Run the Iteration

```bash
/iterate csv-reporter
```

When prompted:
- **Target:** csv-reporter
- **Instances:** 3 (statistical coverage)
- **Max depth:** 3 (keep it short for the first journey)
- **Model:** claude-haiku-4-5-20251001 (fast and cheap)

## What to Watch

In a separate terminal:

```bash
# Live event stream (compact, grep-friendly)
python3 scripts/dashboard.py --latest --stream

# Or watch parallel instance progress
tail -f /tmp/agent-spec-parallel-out-*.log
```

After each depth completes:

```bash
# See what happened
python3 scripts/dashboard.py --latest --summary

# Compare this depth to previous
python3 scripts/report.py --compare <depth0_id> <depth1_id>

# Check cost accumulation
python3 scripts/tokens.py --session <session_id>
```

## What to Look For

### Depth 0 (baseline fails)
- How many instances fail? All 3? Some?
- What does verify.sh actually complain about?
- Read the produced code: `cat results/<run_id>/produced/*.py`

### Diagnosis phase
- Are the findings specific enough to act on?
- Is the fix classified correctly (Level 2 for target instructions, Level 0 for harness)?
- Does the diagnosis miss anything obvious in the verify.sh output?

### Depth 1+ (after fixes)
- Did the pass rate improve?
- Did cost change? (better instructions often mean fewer agent turns)
- Did the fix introduce any new failures?

### Convergence
- When all 3 pass, does the loop stop cleanly?
- Is the handoff doc (`results/tuning-handoff.md`) useful?
- Could a fresh session pick up from the handoff?

## Success Criteria

- [ ] Started from at least 1 failing instance
- [ ] Iterated at least 1 depth
- [ ] All 3 instances pass in a single depth
- [ ] Total cost visible via `tokens.py --session`
- [ ] Config diff visible between depth 0 and final: `dashboard.py --diff <id0> <idN>`
- [ ] Handoff doc written with fixes and rationale

## What to Improve After

After completing this journey, look at:
1. **Was diagnosis accurate?** If the iterate loop misdiagnosed failures, improve the diagnosis step in SKILL.md.
2. **Was monitoring sufficient?** If you had to manually dig through logs, add missing dashboard features.
3. **Were fixes generalized?** If a fix only helped csv-reporter but not other targets, it was overfitted.
