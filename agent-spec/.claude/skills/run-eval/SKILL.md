---
name: run-eval
description: Run an evaluation against an eval with a specific config
argument-hint: <eval> [config] [--model MODEL] [--keep]
---

# /run-eval — Run an evaluation

Run a Claude agent in a workspace, then score the result.

## Before Starting

Confirm with the user:

1. Eval and config to run
2. Single run or parallel (default: single)
3. If parallel: how many instances (default: 1)

Do NOT launch until the user confirms.

## Arguments

- `$1` — eval name (directory name in `evals/`, e.g., `csv-reporter`)
- `$2` — config name (directory name in `evals/<eval>/configs/`, default: `baseline`)
- `--model <name>` — override model (default from EVAL.md frontmatter)
- `--keep` — keep workspace after completion for inspection
- `--budget <usd>` — override budget

## Steps

1. Read `evals/$1/EVAL.md` frontmatter to get source path, model, budget, setup commands, delete list, and reference
2. Extract the prompt from the EVAL.md body (everything after the second `---`)
3. Resolve the source path relative to the evals directory
4. Run the evaluation:

```bash
EVAL_DIR="$CLAUDE_PROJECT_DIR/evals/$1"
CONFIG_DIR="$EVAL_DIR/configs/${2:-baseline}"
VERIFY_FILE="$EVAL_DIR/verify.sh"

# Parse EVAL.md frontmatter for source, model, budget
python3 "$CLAUDE_PROJECT_DIR/scripts/invoke.py" \
  "<source from EVAL.md>" \
  "$CONFIG_DIR" \
  "<prompt from EVAL.md body>" \
  --verify "$VERIFY_FILE" \
  --model "${MODEL:-<model from EVAL.md>}" \
  --budget "${BUDGET:-<budget from EVAL.md>}"
```

5. After completion, show the dashboard summary:

```bash
python3 "$CLAUDE_PROJECT_DIR/scripts/dashboard.py" --latest --summary
```
