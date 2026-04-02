# agent-spec — Run Diagnosis

You are inside agent-spec, a test harness for `.claude/` agents. Your task is to diagnose a failed evaluation run.

## Tools available

- `python3 scripts/dashboard.py <run_id> --summary` — shows a formatted run summary
- `python3 scripts/dashboard.py <run_id> --stream` — compact event stream
- Events are stored as JSONL in `/tmp/agent-spec/<run_id>/events.jsonl`
- Key events: `agent_started`, `agent_complete`, `verification_output`, `test_passed`, `test_failed`, `score`

## How to diagnose

1. Start with the dashboard summary for an overview
2. Read the `verification_output` event — its `data.output` field contains the verify.sh output, which usually has the error message
3. Look at `test_passed` and `test_failed` events for individual test results
4. The root cause is usually a mismatch between what the agent produced and what verify.sh expected

## Output format

Write `diagnosis.md` with sections: What happened, What failed, Root cause, Recommended fix. Quote specific evidence from the events.
