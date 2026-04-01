# Journey 8: Budget Cliff

**Goal:** Find the minimum budget where each target still passes, then iterate instructions to push that floor lower.

**What this exercises:** Token efficiency under real constraints. Can better instructions let an agent succeed with fewer turns and less output?

## Known Cliffs (2026-04, haiku + baseline)

| Target | $0.50 | $0.10 | $0.05 | $0.03 | $0.02 |
| ------ | ----- | ----- | ----- | ----- | ----- |
| csv-reporter | PASS | PASS | PASS | PASS (flaky) | 60% pass (3/5) |
| sqlite-window-queries | PASS | PASS | PASS | PASS | untested |
| hono-websocket-counter | PASS | untested | untested | untested | untested |

The csv-reporter budget cliff is ~$0.02-0.03 with haiku. Cost variance across runs ranges $0.022-$0.045 for the same task, so the cliff is fuzzy, not sharp.

## The Cliff

For each target, binary search for the budget floor:

```bash
# Start high, work down
for budget in 0.50 0.25 0.10 0.05 0.02; do
  python3 scripts/run_eval.py csv-reporter baseline \
    --model claude-haiku-4-5-20251001 --budget $budget
  python3 scripts/score.py $(python3 scripts/dashboard.py --latest --stream 2>/dev/null | tail -1 | awk '{print $NF}')
done
```

Or more precisely — run each budget level and record pass/fail:

```bash
python3 scripts/run_eval.py csv-reporter baseline --model claude-haiku-4-5-20251001 --budget 0.10
python3 scripts/dashboard.py --latest --stream | grep score
```

## Iterate to Lower the Floor

Once you find the cliff (e.g., passes at $0.10, fails at $0.05), create a tuned config and iterate:

```bash
mkdir -p targets/csv-reporter/configs/lean
# Copy token-efficient as starting point
cp targets/_shared/configs/token-efficient/CLAUDE.md targets/csv-reporter/configs/lean/CLAUDE.md
```

Add target-specific hints that reduce exploration:
- Exact output format expected
- Which libraries to use
- What NOT to do (don't write tests, don't explore)

Then test at the budget that previously failed:

```bash
python3 scripts/run_eval.py csv-reporter lean --model claude-haiku-4-5-20251001 --budget 0.05
```

## What to Watch For

- What does the agent do when it runs out of budget mid-task?
- Does it produce partial output that almost passes?
- Do timeout and budget exhaustion look different in the logs?
- Which target has the steepest cliff (passes at X, fails at X-0.01)?

## Success Criteria

- [ ] Budget cliff mapped for each target (pass/fail at each level)
- [ ] At least one target's floor lowered by tuning instructions
- [ ] Cost comparison: tuned config at low budget vs baseline at high budget
- [ ] Documented what instructions help most under budget pressure
