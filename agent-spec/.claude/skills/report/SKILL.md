---
name: report
description: Show evaluation results and comparisons
argument-hint: [run_id | --latest | --all | --summarize <eval>]
---

# /report — Show evaluation results

## Usage

- `/report` or `/report --latest` — Dashboard summary of the most recent run
- `/report <run_id>` — Dashboard summary of a specific run
- `/report --all` — Full comparison report across all runs
- `/report --summarize <eval_name>` — Generate eval summary (terminal + RESULTS.md)

## Steps

Parse the arguments and dispatch:

1. If args contain `--summarize`, extract the eval name and run:
   ```bash
   python3 "$CLAUDE_PROJECT_DIR/scripts/summarize.py" <eval_name> --filter-eval
   ```

2. If args contain `--all`, run:
   ```bash
   python3 "$CLAUDE_PROJECT_DIR/scripts/report.py" --all
   ```
   If `--group-by` is also present, pass it through.

3. If args contain a run_id (8+ hex chars), run:
   ```bash
   python3 "$CLAUDE_PROJECT_DIR/scripts/dashboard.py" <run_id> --summary
   ```

4. Otherwise (no args or `--latest`):
   ```bash
   python3 "$CLAUDE_PROJECT_DIR/scripts/dashboard.py" --latest --summary
   ```
