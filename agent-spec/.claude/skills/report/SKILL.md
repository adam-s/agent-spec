---
name: report
description: Show evaluation results and comparisons
argument-hint: [run_id | --latest | --all]
---

# /report — Show evaluation results

## Usage

- `/report` or `/report --latest` — Dashboard summary of the most recent run
- `/report <run_id>` — Dashboard summary of a specific run
- `/report --all` — Full comparison report across all runs

## Steps

```bash
case "${1:---latest}" in
  --latest)
    bash "$CLAUDE_PROJECT_DIR/scripts/dashboard.sh" --latest --summary
    ;;
  --all)
    python3 "$CLAUDE_PROJECT_DIR/scripts/report.py" --all
    ;;
  *)
    bash "$CLAUDE_PROJECT_DIR/scripts/dashboard.sh" "$1" --summary
    ;;
esac
```
