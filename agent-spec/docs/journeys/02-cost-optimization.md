# Journey 2: Cost Optimization

**Goal:** Take a target that already passes and iterate to reduce token spend without breaking the pass rate.

**What this exercises:** A/B testing configs, cost regression detection, the tension between instruction quality and token efficiency, and the reporting/comparison stack.

## Establish the Baseline

Run 3 instances with baseline config to get a reliable cost measurement:

```bash
python3 scripts/parallel.py csv-reporter --configs baseline --instances 3 \
  --model claude-haiku-4-5-20251001
```

Record the baseline cost:

```bash
python3 scripts/report.py <id1> <id2> <id3>
```

Note: avg tokens, avg cost, pass rate. This is your floor.

## Create a Token-Efficient Variant

```bash
cp -r targets/_shared/configs/token-efficient targets/csv-reporter/configs/lean
```

Edit `targets/csv-reporter/configs/lean/CLAUDE.md` — add target-specific hints that reduce agent exploration:
- Tell it the exact output format
- Tell it which libraries to use
- Tell it not to write tests (verify.sh handles that)

## A/B Test

```bash
python3 scripts/parallel.py csv-reporter --configs baseline,lean \
  --instances 3 --model claude-haiku-4-5-20251001
```

Compare:

```bash
python3 scripts/report.py --all --group-by config
```

## Iterate on the Lean Config

```bash
/iterate csv-reporter lean --max-depth 3 --instances 3
```

But this time the stop condition is different. You're not trying to go from FAIL to PASS — you're trying to maintain PASS while reducing cost. After each depth:

```bash
# Compare cost to baseline
python3 scripts/report.py --compare <baseline_id> <latest_id>

# Watch for cost regression between depths
python3 scripts/tokens.py --session <session_id>
```

## What to Look For

### Cost signals
- Does adding specific instructions reduce output tokens? (fewer agent "thinking" turns)
- Does telling the agent what NOT to do help? (e.g., "don't write tests")
- Does the `drona23` config's "zero sycophancy" actually reduce tokens?

### Traps
- Instructions that are too specific → agent can't adapt to minor variations
- Instructions that suppress exploration → agent misses edge cases in verify.sh
- Cost drops but pass rate drops too → net negative

### Config comparison
- Use `--group-by config` to see which variant wins on cost vs pass rate
- Use `--compare` to see exact token deltas between two specific runs

## Success Criteria

- [ ] Baseline cost measured (3+ runs averaged)
- [ ] At least one config variant tested that reduces cost
- [ ] Pass rate maintained at 3/3 (or improved)
- [ ] Cost reduction quantified: `report.py --compare` shows negative delta
- [ ] No regression in pass rate between optimization depths
- [ ] Best config documented with rationale for what worked

## What to Improve After

1. **Is cost comparison easy enough?** If you had to manually calculate deltas, improve report.py.
2. **Can you spot the cheapest passing config at a glance?** If not, add a "cost-optimized leaderboard" view.
3. **Did instruction changes generalize?** Test the winning lean config on sqlite-window-queries too.
