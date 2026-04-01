# Journey 6: Cross-Target Consistency

**Goal:** Improve a shared config so it works across ALL targets simultaneously, not just the one you're iterating on.

**What this exercises:** The generalization principle — Level 2 fixes that only help one target are overfitting. This journey forces you to think in terms of config changes that help all projects.

## The Problem

Most iteration work focuses on one target at a time. You tune csv-reporter's config, then move to sqlite-window-queries. But shared configs (`targets/_shared/configs/`) are meant to work everywhere. How do you improve a shared config without breaking targets you're not looking at?

## Full Matrix Baseline

Run every target with every shared config:

```bash
for target in csv-reporter sqlite-window-queries hono-websocket-counter; do
  for config in baseline token-efficient structured; do
    python3 scripts/run_eval.py $target $config --model claude-haiku-4-5-20251001
  done
done
```

Generate the matrix report:

```bash
python3 scripts/report.py --all --group-by config
python3 scripts/report.py --all --group-by target
```

This gives you a 3x3 (or larger) matrix. Some cells will be PASS, some FAIL. That's your starting map.

## Pick a Losing Config

Find a shared config that fails on 2+ targets. That's your improvement target — fixing it for one target is easy, fixing it for all is the real challenge.

## Iterate with Cross-Validation

For each depth of iteration:

1. **Iterate on one target:**
   ```bash
   /iterate csv-reporter <config> --instances 3 --max-depth 2
   ```

2. **Cross-validate on other targets:**
   ```bash
   python3 scripts/run_eval.py sqlite-window-queries <config>
   python3 scripts/run_eval.py hono-websocket-counter <config>
   ```

3. **Check for regressions:**
   ```bash
   python3 scripts/report.py --all --group-by target
   ```

If your fix helps csv-reporter but breaks sqlite-window-queries, the fix is too specific. Back it out and find a more general instruction.

## The Generalization Test

For every instruction you add to the shared config, ask:

- "Would this make sense for a Python project? A JavaScript project? A TypeScript project?"
- "Does this instruction assume anything about the target's structure?"
- "Would a developer reading this for a NEW project find it helpful or confusing?"

Instructions that pass this test belong in shared configs. Instructions that fail belong in target-specific configs.

## Build the Leaderboard

After improving, re-run the full matrix and compare:

```bash
# Before (use saved run IDs)
python3 scripts/report.py <before_ids...> --group-by config

# After
python3 scripts/report.py <after_ids...> --group-by config
```

The goal: more cells are PASS, total cost is flat or lower, no cell went from PASS to FAIL.

## Success Criteria

- [ ] Full matrix baseline established (all targets x all configs)
- [ ] At least one shared config improved
- [ ] Cross-target validation after each improvement
- [ ] No regression in any target that was previously passing
- [ ] Report shows improvement across multiple targets
- [ ] Instructions that failed the generalization test moved to target-specific configs

## What to Improve After

1. **Is the full matrix easy to run?** If it takes too many commands, add a `scripts/matrix.py` that runs everything.
2. **Can you see the matrix at a glance?** If `report.py --group-by` isn't enough, add a cross-tab view (target x config).
3. **Did the iteration loop naturally cross-validate?** If not, add a cross-target step to the iterate skill.
4. **Are shared configs actually shared?** If every target has overrides, the shared configs aren't pulling their weight.
