# Observability

Every experiment must produce visible, real-time progress. If the developer can't see what's happening, the experiment has failed regardless of results.

## Rules

- Every run must print a summary line when it completes: `✓ name: PASS (30s) 9,500tok` or `✗ name: FAIL (30s) 9,500tok`
- Token counts in summary output are **input + output only** — never include cache reads. Cache reads are cheap repetition of context, not actual work. Including them inflates totals ~100x and makes comparisons meaningless.
- Never pipe agent output through filters that lose data (`tail -1`, `head -1`, `| grep`). Capture the full output, then summarize.
- After launching a background process, verify it's producing output within 30 seconds. If no output, investigate — don't wait silently.
- When running multiple sequential runs (loops), each run must print its result before the next starts. The developer should see progress accumulating.
- When a run produces no output or UNKNOWN result, diagnose immediately. Don't continue to the next run.

## Output Convention

Scripts follow the Unix convention: **stdout is structured data, stderr is human display**.

- `invoke.py` emits JSONL events on stdout (same schema as events.jsonl) and renders human-readable output on stderr.
- `parallel.py` reads child stdout JSONL to track results — no regex parsing.
- To capture only structured output: `python3 scripts/run_eval.py ... 2>/dev/null | jq .`
- All human display (headers, spinners, status lines) goes to stderr via `render_event()` in lib.py.

## Debug Mode

Set `AGENT_SPEC_DEBUG=0` to suppress debug logging to stderr and events.jsonl. Enabled by default (`AGENT_SPEC_DEBUG=1`).

Debug events are written with level `DEBUG` and event name `debug:{tag}`. Filter with:
```
jq 'select(.level=="DEBUG")' /tmp/agent-spec/{run_id}/events.jsonl
```

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

## Live watching

Watch a run in real-time with vitest-style output (turns, tools, verify results):
```
python3 scripts/run_eval.py ... --stream 2>/dev/null | python3 scripts/watch.py
python3 scripts/watch.py --latest                    # Tail the most recent run
python3 scripts/watch.py --run <run_id>              # Tail a specific run
```

## Reporting commands

```
python3 scripts/report.py --score <run_id>           # PASS/FAIL result
python3 scripts/report.py --tokens <run_id>          # Token breakdown
python3 scripts/report.py --all                      # All runs
python3 scripts/report.py --all --group-by config    # Grouped comparison
python3 scripts/report.py --baseline save <run_id>   # Save baseline
python3 scripts/report.py --baseline check <run_id>  # Check for regression
python3 scripts/behavior.py <run_id>                 # Behavior scorecard
python3 scripts/behavior.py --all --group-by target  # Behavior by challenge
python3 scripts/behavior.py --all --group-by result  # Behavior vs outcome
python3 scripts/dashboard.py <run_id>                # Live event tail
python3 scripts/dashboard.py --diff <id1> <id2>      # Config diff
python3 scripts/system_monitor.py                    # Resource status
```
