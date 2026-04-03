---
name: iterate
description: Generalized recursive iteration loop. Runs parallel sub-agents against a target, scores deterministically, diagnoses instruction gaps, applies fixes, and recurses until the stop condition is met or max depth is reached.
argument-hint: <target> [config] [--max-depth N] [--instances N] [--keep]
---

# /iterate — Recursive Instruction Tuning

Read @.claude/reference/recursive-training.md first. You are Level 0.

## Parameters

This skill is a generalized iteration engine. It works with ANY target that has a `EVAL.md` and a `verify.sh` producing `RESULT: PASS` or `RESULT: FAIL`.

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
- `target` — a directory in `evals/` with `EVAL.md`, `prompt.md`, `verify.sh`
- `config` — a `.claude/` directory variant in `evals/<target>/configs/`
- `instances` — how many parallel sandboxes to run (default 3)
- `max_depth` — maximum iterations before forced stop (default 5)

**Stop condition (deterministic):**
All instances produce `RESULT: PASS` in the same iteration.
This is the base case. No subjective judgment — pass/fail comes from `verify.sh`.

**Output:**
The improved `target/.claude/` directory and a results summary.

## Before Starting — Ask the User

1. **Which target?** Must exist in `evals/`. Read `EVAL.md` to confirm.
2. **How many parallel instances?** Default 3. Ask if the user wants different stimuli per instance (wireframes, varied prompts, etc.) or identical runs for statistical coverage.
3. **Max depth?** Default 5. This is the hard stop — iteration halts even if not converged.
4. **Cleanup mode?** Full cleanup (default) or keep sandboxes for inspection.
5. **Stimuli?** Optional per-instance variation (screenshot URLs, data files, etc.) that get injected into each workspace. If none, all instances are identical.

Do NOT launch agents until the user answers.

## The Loop

Use the existing tools at each step — do not reimplement.

```
session_id = uuid4().hex[:8]   # Correlates all iterations in this /iterate invocation
depth = 0

RECURSE:
  if depth >= max_depth:
    EMIT: apc_log("INFO", "iteration_session_complete", "Max depth reached",
           {"session_id": session_id, "final_depth": depth, "converged": false,
            "total_cost_usd": <sum from all runs>, "total_duration_ms": <wall clock>})
    RETURN with summary: "Max depth reached. Best results: ..."

  EMIT: apc_log("INFO", "iteration_started", "Starting iteration",
         {"depth": depth, "max_depth": max_depth, "target": target,
          "config": config, "session_id": session_id, "instances": N})

  1. CLEAN
     python3 scripts/cleanup.py

  2. PREPARE STIMULI (if any)
     # capture-wireframe.sh has been removed; use external screenshot tools if needed
     These get injected via --stimuli-dir.

  3. LAUNCH
     python3 scripts/parallel.py <target> <config> \
       --instances N [--stimuli-dir <path>] [--keep]
     Collect run IDs from stdout.

     For A/B testing configs within iteration:
       --configs baseline,experimental

     For model comparison within iteration:
       --models haiku,sonnet

  4. MONITOR (every 60s)
     python3 scripts/dashboard.py <run_id> --summary
     Build a monitoring table. Stop early if agent is stuck.

  5. SCORE
     python3 scripts/report.py --score <run_id>
     python3 scripts/report.py <run_id1> <run_id2> ... --group-by config

     For two-run comparison:
       python3 scripts/report.py --compare <id1> <id2>

  6. REGRESSION CHECK
     python3 scripts/report.py --baseline check <run_id>
     If first iteration, save baseline:
       python3 scripts/report.py --baseline save <run_id>

  7. STOP CONDITION CHECK
     if all instances PASS and no regressions:
       EMIT: apc_log("INFO", "iteration_complete", "Converged",
              {"depth": depth, "session_id": session_id, "converged": true, "pass_rate": "N/N"})
       EMIT: apc_log("INFO", "iteration_session_complete", "Session converged",
              {"session_id": session_id, "final_depth": depth, "converged": true,
               "total_cost_usd": <sum>, "total_duration_ms": <wall clock>})
       RETURN with summary: "Converged at depth {depth}."

  8. OBSERVE (mandatory before diagnosis)
     For EACH failing instance:
       a. python3 scripts/dashboard.py <run_id> --stream | grep -E "score|FAIL|ERROR|verification"
       b. Read produced code: ls results/<run_id>/produced/
       c. Read verify.sh output: check verification_output event in events.jsonl
       d. If config snapshot exists: python3 scripts/dashboard.py --diff <prev_id> <this_id>

     Do NOT skip this step. Diagnosis without observation leads to wrong fixes.

  9. DIAGNOSE (gate: findings table required)
     Produce a findings table with one row per failure. Every row MUST have:
       | Instance | What failed | Evidence (file:line or event) | Fix | Level (0 or 2) |
     A row without evidence in the "Evidence" column is not diagnosed — go back to OBSERVE.
     If uncertain about Level classification, ask the human.

     EMIT: apc_log("INFO", "iteration_diagnosed", "Diagnosis complete",
            {"depth": depth, "session_id": session_id,
             "findings_count": <N>, "findings_summary": "brief description"})

  10. APPLY FIXES
      Level 2 → target's .claude/
      Level 0 → agent-spec (selective)
      After each fix, consistency-check all .claude/ files at that level.

      EMIT: apc_log("INFO", "iteration_fixed", "Fixes applied",
             {"depth": depth, "session_id": session_id,
              "files_changed": ["path/to/file1", "path/to/file2"]})

      EMIT: apc_log("INFO", "iteration_complete", "Iteration done",
             {"depth": depth, "session_id": session_id, "converged": false,
              "pass_rate": "M/N", "duration_ms": <elapsed>})

  11. depth += 1
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

## Handoff

After the loop terminates (converged or max depth), write `results/tuning-handoff.md`:
- Final depth reached
- Results table (all instances, all passes)
- Fixes applied with level assignments
- Whether converged or hit max depth
- Remaining gaps if not converged
- Recommend fresh session for next run (avoids stale sub-agent context)
