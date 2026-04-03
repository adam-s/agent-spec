---
name: run-eval
description: Run an evaluation against an eval with a specific config
argument-hint: <eval> [config] [--model MODEL] [--challenge NAME] [--keep]
---

# /run-eval — Run an evaluation

Run a Claude agent in a workspace, then score the result.

## Before Starting

Confirm with the user:

1. Eval and config to run
2. Single challenge or all challenges (matrix evals run all by default)
3. Single run or parallel (default: single)

Do NOT launch until the user confirms.

## Arguments

- `$1` — eval name (directory in `evals/`)
- `$2` — config name (directory in `evals/<eval>/configs/`, default: `baseline`)
- `--model <name>` — override model (default from EVAL.md frontmatter)
- `--budget <usd>` — override budget
- `--challenge <name>` — run only this challenge (matrix evals)
- `--keep` — keep workspace after completion for inspection

## Steps

1. Run the evaluation:

```bash
python3 scripts/run_eval.py <eval> <config> [--model MODEL] [--budget USD] [--challenge NAME] [--keep]
```

`run_eval.py` handles everything: EVAL.md parsing, config resolution, challenge iteration, prompt templating, and invoke.py delegation.

2. After completion, show results:

```bash
python3 scripts/dashboard.py --latest --summary
```

Use `run_in_background: true` for the run command. Monitor with `python3 scripts/dashboard.py --latest`.
