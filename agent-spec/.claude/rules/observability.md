# Observability

Every experiment must produce visible, real-time progress. If the developer can't see what's happening, the experiment has failed regardless of results.

## Rules

- Every run must print a summary line when it completes: `✓ name: PASS (30s) 9,500tok` or `✗ name: FAIL (30s) 9,500tok`
- Token counts in summary output are **input + output only** — never include cache reads. Cache reads are cheap repetition of context, not actual work. Including them inflates totals ~100x and makes comparisons meaningless.
- Never pipe agent output through filters that lose data (`tail -1`, `head -1`, `| grep`). Capture the full output, then summarize.
- After launching a background process, verify it's producing output within 30 seconds. If no output, investigate — don't wait silently.
- When running multiple sequential runs (loops), each run must print its result before the next starts. The developer should see progress accumulating.
- When a run produces no output or UNKNOWN result, diagnose immediately. Don't continue to the next run.

## Reporting Integrity

- Aggregates hide failures. Every report that includes a pass rate must also list each individual failure. A percentage is not actionable; a specific failed run is.
- Experiments evolve — when they do, old results that share tags or names silently merge into new aggregates. Reports must support temporal isolation so stale data from prior versions doesn't distort current results.
