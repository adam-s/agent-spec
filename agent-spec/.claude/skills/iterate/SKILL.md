---
name: iterate
description: Generalized recursive iteration loop. Runs parallel sub-agents against a target, scores deterministically, diagnoses instruction gaps, applies fixes, and recurses until the stop condition is met or max depth is reached.
argument-hint: <target> [config] [--max-depth N] [--instances N] [--keep]
---

# /iterate — Recursive Instruction Tuning

Read @.claude/reference/recursive-training.md first. You are Level 0.

## Parameters

This skill is a generalized iteration engine. It works with ANY target that has a `target.yaml` and a `verify.sh` producing `RESULT: PASS` or `RESULT: FAIL`.

```
iterate(target, config, stop_condition, depth=0, max_depth=N):
    results = run_parallel(target, config, instances)
    if stop_condition(results) or depth >= max_depth:
        return results                          # BASE CASE
    findings = diagnose(results)
    config' = apply_fixes(config, findings)
    return iterate(target, config', stop_condition, depth+1, max_depth)
```

**Inputs:**
- `target` — a directory in `targets/` with `target.yaml`, `prompt.md`, `verify.sh`
- `config` — a `.claude/` directory variant in `targets/<target>/configs/`
- `instances` — how many parallel sandboxes to run (default 3)
- `max_depth` — maximum iterations before forced stop (default 5)

**Stop condition (deterministic):**
All instances produce `RESULT: PASS` in the same iteration.
This is the base case. No subjective judgment — pass/fail comes from `verify.sh`.

**Output:**
The improved `target/.claude/` directory and a results summary.

## Before Starting — Ask the User

1. **Which target?** Must exist in `targets/`. Read `target.yaml` to confirm.
2. **How many parallel instances?** Default 3. Ask if the user wants different stimuli per instance (wireframes, varied prompts, etc.) or identical runs for statistical coverage.
3. **Max depth?** Default 5. This is the hard stop — iteration halts even if not converged.
4. **Cleanup mode?** Full cleanup (default) or keep sandboxes for inspection.
5. **Stimuli?** Optional per-instance variation (screenshot URLs, data files, etc.) that get injected into each sandbox. If none, all instances are identical.

Do NOT launch agents until the user answers.

## The Loop

```
depth = 0

RECURSE:
  if depth >= max_depth:
    RETURN with summary: "Max depth reached. Best results: ..."

  1. CLEAN
     bash scripts/sandbox/clear-ports.sh

  2. PREPARE STIMULI (if any)
     Capture screenshots, copy data files, etc. to /tmp/agent-spec-stimuli/
     These get injected into sandboxes — one per instance or shared.

  3. LAUNCH
     bash scripts/tuning/parallel-invoke.sh <target> <config> [options]
     Collect run IDs.

  4. MONITOR (every 60s)
     For each run_id, read events.jsonl or dashboard.
     | Instance | Run ID | Status | Notes |
     Stop early if agent is in a known-dead pattern.

  5. SCORE (deterministic)
     For each run_id, extract the RESULT line from verify output.
     pass_count = count of RESULT: PASS
     fail_count = count of RESULT: FAIL

  6. STOP CONDITION CHECK
     if pass_count == instances:
       RETURN with summary: "Converged at depth {depth}. All instances pass."

  7. DIAGNOSE
     For each failing instance, read produced code and events.
     For EVERY finding, classify:
       "Level 0 fix (trainer): ___" or "Level 2 fix (trainee): ___"
     If uncertain, ask the human.

  8. APPLY FIXES
     Level 2 → target's .claude/ (on trainee branch)
     Level 0 → agent-spec (on main, selective)
     After each fix, consistency-check all .claude/ files at that level.

  9. depth += 1
     GOTO RECURSE
```

## Fix Classification

See @.claude/reference/recursive-training.md Guard 2 for the full table.

Two heuristics:
1. "Would this fix help a different target?" Yes → Level 0. No → Level 2.
2. "Is the agent doing the wrong thing, or is the harness measuring wrong?" Wrong behavior → Level 2. Wrong measurement → Level 0.

## Generalization Rule

Every Level 2 fix must work for ANY stimulus, not just the one that failed. If a fix only helps for one specific input, it is overfitting.

Every Level 0 fix must work for ANY target. If it only helps one project, it belongs in target config.

## Branch Discipline

- Level 0 fixes → **main**
- Level 2 fixes → **trainee's feature branch**
- New scripts, configs, stimuli → **iterate feature branch**

Verify you are on the correct branch before each commit.

## Handoff

After the loop terminates (converged or max depth), write `results/tuning-handoff.md`:
- Final depth reached
- Results table (all instances, all passes)
- Fixes applied with level assignments
- Whether converged or hit max depth
- Remaining gaps if not converged
- Recommend fresh session for next run (avoids stale sub-agent context)
