An evaluation run with ID `test-fail-run` has failed. Your task is to diagnose what went wrong.

Use the agent-spec tools to investigate:
1. Run `python3 scripts/dashboard.py test-fail-run --summary` to see the run overview
2. Read the events at `/tmp/agent-spec/test-fail-run/events.jsonl` for detailed data
3. Look at the verification_output event to understand what the verify script found

Write your diagnosis to `diagnosis.md` with these sections:
- **What happened**: What was the agent trying to do?
- **What failed**: What did the verify script report?
- **Root cause**: Why did it fail? Be specific — name the exact function name mismatch or missing file or wrong output format.
- **Recommended fix**: What should change in the `.claude/` instructions to prevent this?

Be specific and evidence-based. Quote from the events data.
