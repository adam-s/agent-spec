---
name: run-eval
description: Run an evaluation against an eval with a specific config
argument-hint: <eval> [config] [--model MODEL] [--challenge NAME] [--prompt-variant VARIANT] [--keep]
---

# /run-eval — Run an evaluation

Run a Claude agent in a workspace, score the result, then compare against the most recent prior run.

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
- `--prompt-variant <name>` — use `prompt-<name>.md` instead of `prompt.md` (e.g. `--prompt-variant vague`)
- `--keep` — keep workspace after completion for inspection

## Steps

1. Run the evaluation:

```bash
python3 scripts/run_eval.py <eval> <config> [--model MODEL] [--budget USD] [--challenge NAME] [--prompt-variant VARIANT] [--keep]
```

`run_eval.py` handles everything: EVAL.md parsing, config resolution, challenge iteration, prompt templating, and invoke.py delegation. It always runs in stream mode so the agent's transcript is archived to `stream.jsonl` for `/compare` to read.

Use `run_in_background: true` for the run command. Monitor with `python3 scripts/dashboard.py --latest`.

2. After the run finishes, show the result:

```bash
python3 scripts/dashboard.py --latest --summary
```

3. **For each challenge that just ran**, find the most recent prior run for the same target/config (if any) and call `/compare`:

```text
/compare <prior-run-id> <current-run-id>
```

To find the prior run id: list `evals/<eval>/results/` sorted by mtime, skip the current run, take the next one whose `events.jsonl` shows the same target and config in `agent_started`. If there is no prior run, skip the comparison and just show the run result.

The `/compare` skill spawns a sub-agent that reads both runs' evidence (events, transcript, produced artifacts) and writes a markdown summary. Print its output below the run summary so the developer sees both in one place.

If the developer ran multiple challenges (matrix eval), call `/compare` once per challenge — each comparison is independent.
