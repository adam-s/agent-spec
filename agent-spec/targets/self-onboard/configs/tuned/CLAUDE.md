# agent-spec — Evaluation Target Development

You are working inside agent-spec, a test harness for `.claude/` directories. Your task is to create a new evaluation target.

## How Targets Work

A target is a directory in `targets/` with:
- `target.yaml` — source repo path, verify script, agent settings
- `prompt.md` — the task given to the agent
- `verify.sh` — scoring script that prints `RESULT: PASS` or `RESULT: FAIL`
- `configs/baseline/CLAUDE.md` — minimal instructions for the baseline config

## Reference

Look at `targets/csv-reporter/` as an example of a well-structured target. Key patterns:
- `source:` in target.yaml is a path to the source repo
- `verify.sh` uses `set -euo pipefail`, captures test output, greps for a success string
- `verify.sh` must always exit 0 — the scoring mechanism is the RESULT line, not the exit code
- `prompt.md` is concise — describe the task and how to verify, not implementation details

## verify.sh Contract

```bash
#!/usr/bin/env bash
set -euo pipefail
OUTPUT=$(python3 test.py 2>&1)
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "4/4 tests passed"; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
```

After creating all files, run `python3 scripts/cli.py list` to confirm the target appears.
