# agent-spec — Improvement Loop

You are inside agent-spec, a test harness for `.claude/` directories. Your task is to perform one iteration of the improvement loop: investigate a failed run, diagnose the root cause, and produce an improved config.

## Tools available

- `python3 scripts/dashboard.py <run_id> --summary` — formatted run overview
- `python3 scripts/dashboard.py <run_id> --stream` — compact event stream
- Events are stored as JSONL in `/tmp/agent-spec/<run_id>/events.jsonl`
- Key events to read: `verification_output` (contains test output), `test_passed`/`test_failed`, `score`, `files_deleted`

## How to diagnose

1. Start with the dashboard summary
2. Read the `verification_output` event — its `data.output` field shows what the verify script found
3. Compare what the agent produced vs what was expected
4. Look at `files_deleted` — if test files were deleted and recreated, the agent may have changed the output format contract

## Common failure pattern: hidden output format contracts

The most common failure in agent-spec is when `verify.sh` greps for specific strings (like `"5/5 tests passed"`) but the agent produces different phrasing. When `delete_before_run` removes test files, the agent recreates them with different formatting, and verify.sh breaks — even though the code is functionally correct.

The fix is always in the config: tell the agent what output format is expected, or tell it to read existing test files before writing code.

## Writing the improved config

The improved config must teach the agent HOW to avoid the failure, not WHAT the correct output is. Two mandatory elements:

1. **"Read before write" rule**: The config MUST tell the agent to read existing test files (test.py, etc.) before writing any code, and to match the expected format exactly. This is the single most important instruction for avoiding format mismatches.

2. **No raw data from the failure**: NEVER copy specific values from the failed run into the config (dollar amounts, product names, exact strings). That's overfitting — it only fixes this one test case. Instead, teach the principle: "read the test expectations and match them."

Bad example (overfitting): "Format revenue as $1,247,890.50 with comma separators"
Good example (principle): "If test.py exists, read it first to understand the expected output format, then match it exactly"

CRITICAL: If your improved config contains ANY specific numbers, dollar amounts, product names, or test data values copied from the failed run's verification output, you have overfitted. Delete them. The config must work for ANY dataset, not just this one.

## Output

1. `diagnosis.md` — What happened, Root cause, General principle
2. `workspace/improved-config/CLAUDE.md` — The fixed config
