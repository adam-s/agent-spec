# Journey 3: Compare Approaches

**Capabilities tested:** A/B testing configs, model benchmarking, matrix orchestration, reporting with --group-by and --compare, cost analysis

## Scenario

You have two instruction variants and want to know which is better. Or you want to know if haiku is good enough, or if you need sonnet.

## Steps

### 1. A/B test two configs

```bash
scripts/tuning/parallel-invoke.sh my-project --configs baseline,tuned \
  --model claude-haiku-4-5-20251001 --budget 0.50
```

### 2. Compare configs

```bash
python3 scripts/reporting/report.py --compare <baseline_id> <tuned_id>
python3 scripts/reporting/report.py <baseline_id> <tuned_id> --group-by config
```

### 3. Benchmark two models

```bash
scripts/tuning/parallel-invoke.sh my-project tuned \
  --models claude-haiku-4-5-20251001,claude-sonnet-4-6 --budget 1.00
```

### 4. Full matrix

```bash
scripts/tuning/parallel-invoke.sh my-project \
  --configs baseline,tuned \
  --models claude-haiku-4-5-20251001,claude-sonnet-4-6 \
  --budget 1.00
```

## Verification Checklist

### Config variant orchestration

- [ ] `--configs baseline,tuned` launches exactly 2 runs
- [ ] Run 1 uses baseline config, run 2 uses tuned config (verify via events.jsonl agent_started.config)
- [ ] Both runs target the same source repo
- [ ] Both runs use the same model (from --model flag)
- [ ] Both runs use the same budget
- [ ] Each run gets a unique port (no collision)
- [ ] Each run gets a unique sandbox
- [ ] Config names correctly propagated to events.jsonl (not "baseline" for both)

### Model variant orchestration

- [ ] `--models haiku,sonnet` launches exactly 2 runs
- [ ] Run 1 uses haiku, run 2 uses sonnet (verify via events.jsonl agent_started.model)
- [ ] Both runs use the same config
- [ ] Model names correctly propagated to events.jsonl
- [ ] Different models may produce different token counts — both captured correctly

### Matrix orchestration

- [ ] `--configs a,b --models x,y` launches exactly 4 runs (a/x, a/y, b/x, b/y)
- [ ] All 4 combinations are present (no duplicates, no missing)
- [ ] Each of the 4 gets a unique port (3100, 3101, 3102, 3103)
- [ ] Port range 3100-3110 supports up to 11 simultaneous runs
- [ ] With 11+ instances, error or graceful degradation (not silent collision)
- [ ] Manifest file contains all 4 run_ids
- [ ] `--instances 2 --configs a,b` launches 4 runs (2 instances × 2 configs)

### Reporting: --compare

- [ ] `--compare <id1> <id2>` produces table with both run metrics
- [ ] Delta column shows numeric difference (positive or negative)
- [ ] % Change column shows relative change
- [ ] Cost displayed as dollars with 3 decimal places
- [ ] Duration displayed in milliseconds
- [ ] Turns displayed as integer
- [ ] Result row shows PASS/PASS or PASS/FAIL etc. (no delta for categorical)
- [ ] Both runs' target/config/model shown in footer
- [ ] `--compare` with same run_id twice shows all zeros (self-comparison)
- [ ] `--compare` with nonexistent run_id prints error (not crash)

### Reporting: --group-by config

- [ ] Groups runs by config name
- [ ] First group is the baseline for delta calculations
- [ ] Delta columns show difference vs first group
- [ ] Handles groups with different number of runs (1 baseline, 3 tuned)
- [ ] Pass count is sum of PASS results in group
- [ ] Avg Tokens is mean of (input + output) across group
- [ ] Avg Cost is mean of cost_usd across group

### Reporting: --group-by model

- [ ] Groups runs by model name
- [ ] Model names displayed correctly (not truncated)
- [ ] Works with runs from different configs in the same report
- [ ] Handles models with 0 completed runs (empty token data) gracefully

### Reporting: --group-by target

- [ ] Groups runs by target name
- [ ] Useful for cross-target comparison (csv-reporter vs hono-websocket-counter)

### Cost analysis

- [ ] Token breakdown: input, output shown separately
- [ ] Cache tokens (create, read) captured in events but may not be in report table
- [ ] Cost calculated correctly for each model's pricing
- [ ] Total cost across matrix computable by summing individual costs
- [ ] `--compare` cost delta is negative when tuned is cheaper (correct sign)

### Statistical edge cases

- [ ] A/B test where both configs PASS — comparison shows cost/speed differences only
- [ ] A/B test where one PASS one FAIL — visible in report
- [ ] Model benchmark where haiku PASS sonnet FAIL — model quality difference captured
- [ ] All runs FAIL — report still generates (no division by zero in averages)
- [ ] Single run (not A/B) — `--group-by config` shows one group with no delta
- [ ] Report with 50+ runs — `--all --group-by config` handles large datasets
- [ ] Runs from weeks ago mixed with today — grouping still works (no time-based bugs)
