# Observability

Every experiment must produce visible, real-time progress. If the developer can't see what's happening, the experiment has failed regardless of results.

## Rules

- Every run must print a summary line when it completes: `✓ name: PASS (30s) $0.05` or `✗ name: FAIL (30s) $0.05`
- Never pipe agent output through filters that lose data (`tail -1`, `head -1`, `| grep`). Capture the full output, then summarize.
- After launching a background process, verify it's producing output within 30 seconds. If no output, investigate — don't wait silently.
- When running multiple sequential runs (loops), each run must print its result before the next starts. The developer should see progress accumulating.
- When a run produces no output or UNKNOWN result, diagnose immediately. Don't continue to the next run.

## Checking liveness

To check if an agent is actively working:
```
ps aux | grep 'claude.*-p' | grep -v grep
```

To see the latest run directories:
```
ls -lt /tmp/agent-spec/ | head -5
```

To check the most recent run's status:
```
python3 scripts/dashboard.py --latest
```
