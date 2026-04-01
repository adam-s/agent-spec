# Journey 4: Prevent Regressions

**Capabilities tested:** baseline persistence, regression detection, before/after comparison, cost monitoring, threshold enforcement

## Scenario

You have a working `.claude/` config. You want to make changes without breaking anything or making it more expensive.

## Steps

### 1. Establish the baseline

```bash
python3 scripts/run_eval.py my-project tuned --model claude-haiku-4-5-20251001
python3 scripts/save_baseline.py <run_id>
```

### 2. Make changes, re-run, check

```bash
# Edit configs/tuned/CLAUDE.md
python3 scripts/run_eval.py my-project tuned --model claude-haiku-4-5-20251001
python3 scripts/check_regression.py <new_run_id>
```

### 3. Compare

```bash
python3 scripts/report.py --compare <baseline_id> <new_id>
```

## Verification Checklist

### Baseline persistence

- [ ] `save-baseline.sh <run_id>` creates `results/baselines/{target}_{config}.json`
- [ ] Baseline JSON contains: run_id, target, config, model, tokens (full breakdown), result, duration_ms
- [ ] Saving again for same target/config overwrites previous baseline
- [ ] Saving for different config creates separate file (e.g., `my-project_baseline.json` vs `my-project_tuned.json`)
- [ ] Baseline file is valid JSON (parseable by jq)
- [ ] `results/baselines/` directory created automatically if missing
- [ ] Saving a FAIL run as baseline works (you might want to track improvement from failure)
- [ ] Baseline with 0 tokens (agent crashed) stores zeros, not nulls
- [ ] Baseline file not committed to git (ephemeral test output, per product-vs-test rule)

### Regression detection: result

- [ ] PASS→FAIL detected as REGRESSION
- [ ] PASS→PASS detected as OK
- [ ] FAIL→FAIL detected as OK (no improvement, but not a regression)
- [ ] FAIL→PASS detected as OK (improvement)
- [ ] N/A→PASS detected as OK
- [ ] PASS→N/A detected as REGRESSION (agent crashed)

### Regression detection: cost

- [ ] Cost increase >50% detected as REGRESSION
- [ ] Cost increase of exactly 50% NOT a regression (threshold is "more than")
- [ ] Cost increase of 49% NOT a regression
- [ ] Cost increase of 51% IS a regression
- [ ] Cost decrease (any amount) NOT a regression
- [ ] Baseline cost of $0.00 — no cost regression possible (avoid division by zero)

### Regression detection: tokens

- [ ] Token increase >50% detected as REGRESSION
- [ ] Token count = input + output (not just output)
- [ ] Baseline tokens of 0 — no token regression possible (avoid division by zero)
- [ ] Token decrease NOT a regression

### Regression detection: multiple regressions

- [ ] Can detect result AND cost regressions simultaneously
- [ ] Each regression printed on separate line with specific metrics
- [ ] Exit code 1 when any regression detected
- [ ] Exit code 0 when no regression

### Missing baseline handling

- [ ] No baseline file → prints "NO BASELINE" message, exits 0 (not crash)
- [ ] Baseline file exists but is corrupt JSON → error message (not crash)
- [ ] Baseline file exists but has no tokens field → handles gracefully

### Cross-config independence

- [ ] Changing tuned config doesn't affect baseline config's baseline
- [ ] `check-regression.sh` matches by target AND config (not just target)
- [ ] Baseline for `my-project_baseline` is separate from `my-project_tuned`
- [ ] Running check-regression against wrong config → "NO BASELINE" (correct behavior)

### Workflow integration

- [ ] Save baseline → edit config → run eval → check regression → full cycle works
- [ ] Multiple save→check cycles work (baseline updates each time)
- [ ] `/iterate` can use check-regression in its loop (step 6 in the loop)
- [ ] `--compare` between baseline run and regression run shows exact deltas

### Edge cases

- [ ] Run that timed out (no agent_complete event) — check-regression handles missing duration
- [ ] Run that was killed mid-execution — partial events still produce a baseline
- [ ] Very old baseline vs very new run — no time-based staleness issues
- [ ] Baseline saved from model A, checked against model B — warns about model mismatch? (or doesn't — document which)
- [ ] Two users save baselines simultaneously — last write wins (no corruption)
- [ ] Baseline filename with special characters in target name — sanitized or rejected
