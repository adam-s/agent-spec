# Journey 3: Model Shootout

**Goal:** Prove that your instructions work across models, and find the cheapest model that still passes.

**What this exercises:** Model benchmarking, the `--models` flag in parallel.py, cross-model reporting, and whether instructions are model-dependent.

## The Question

Good instructions should be model-agnostic. If your `.claude/` only works with Sonnet but fails with Haiku, the instructions are doing too little — the model's general capability is compensating.

## Run the Benchmark

Pick a target and config that passes reliably:

```bash
python3 scripts/parallel.py csv-reporter --configs baseline \
  --models claude-haiku-4-5-20251001,claude-sonnet-4-6 \
  --instances 2
```

This creates a 1 config x 2 models x 2 instances = 4-run matrix.

```bash
python3 scripts/report.py --all --group-by model
```

## Interpret the Results

The report shows per-model: pass rate, avg tokens, avg cost, and delta vs first model.

| Outcome | What it means |
|---------|---------------|
| Both pass, Haiku cheaper | Instructions are good — use Haiku |
| Sonnet passes, Haiku fails | Instructions need more detail for weaker models |
| Both fail | Instructions or verify.sh need work regardless |
| Haiku passes, Sonnet fails | Very unusual — investigate if Sonnet is overthinking |

## If Haiku Fails

This is the interesting case. Run `/iterate` with Haiku to improve instructions:

```bash
/iterate csv-reporter --model claude-haiku-4-5-20251001 --instances 3
```

The iterate loop will diagnose what Haiku gets wrong and add instructions to compensate. After convergence, re-run the model benchmark to confirm Sonnet still passes too:

```bash
python3 scripts/parallel.py csv-reporter --configs tuned \
  --models claude-haiku-4-5-20251001,claude-sonnet-4-6 \
  --instances 2
python3 scripts/report.py --all --group-by model
```

## Cross-Target Validation

If the tuned config passes for csv-reporter on both models, does it generalize?

```bash
# Test the shared config on a different target
python3 scripts/parallel.py sqlite-window-queries --configs baseline \
  --models claude-haiku-4-5-20251001,claude-sonnet-4-6 \
  --instances 2
python3 scripts/report.py --all --group-by model
```

## Success Criteria

- [ ] At least 2 models benchmarked on the same target+config
- [ ] `report.py --group-by model` shows clear cost/quality comparison
- [ ] If the cheaper model fails, iterate to fix instructions
- [ ] After iteration, both models pass with the same config
- [ ] Cross-target validation confirms instructions aren't model-specific

## What to Improve After

1. **Is model comparison obvious?** If you have to squint at the report, add a "model efficiency" metric (cost per passing run).
2. **Did the Haiku-targeted fixes help Sonnet too?** If not, the fixes might be too model-specific.
3. **Would a 3-model benchmark (Haiku/Sonnet/Opus) reveal anything?** Consider adding it if budget allows.
