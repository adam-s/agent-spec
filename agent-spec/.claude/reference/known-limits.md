# Known System Limits

Empirical limits discovered through journey testing. These are not hard constraints — they shift with model, config, and task complexity.

## Budget Floors (haiku + baseline, 2026-04)

| Target | Min budget (reliable) | Flaky zone | Typical cost |
| ------ | --------------------- | ---------- | ------------ |
| csv-reporter | $0.03 | $0.02 (60% pass) | $0.04-0.06 |
| sqlite-window-queries | $0.03 | untested | $0.04-0.05 |
| hono-websocket-counter | $0.05 (estimated) | untested | $0.07-0.20 |

Cost variance for the same task is ~2x (e.g., $0.022-$0.045 for csv-reporter). Budget cliffs are fuzzy, not sharp.

## File Deletion Resilience

All targets break at Level 2 deletion (deliverable + test file removed). The agent recreates test files but with different output format than verify.sh expects.

| Deletion level | What's removed | Result |
| -------------- | -------------- | ------ |
| Level 1 | Deliverable only | PASS (all targets) |
| Level 2 | Deliverable + test file | FAIL (test output format mismatch) |
| Level 3 | Deliverable + test + data | untested |

**Root cause:** verify.sh greps for specific strings in test output (e.g., "5/5 tests passed"). Agent-written tests use different phrasing.

## Config Impact on Cost

Tested on hono-websocket-counter (the most expensive target):

| Config | Cost | vs Baseline |
| ------ | ---- | ----------- |
| token-efficient | $0.070 | -65% |
| baseline | $0.200 | — |
| drona23 | $0.142 | -29% (but +65% on grouped avg) |

token-efficient benefit scales with task complexity: minimal on simple tasks, large on complex ones.

## Model Comparison (csv-reporter, baseline)

| Model | Tokens | Cost | Turns |
| ----- | ------ | ---- | ----- |
| haiku | 2,111 | $0.038 | 8 |
| sonnet | 860 | $0.053 | 4 |

Sonnet uses fewer tokens (-59%) and turns (-50%) but costs more (+40%) due to pricing.

## Parallel Limits

- Max instances: 11 (ports 3100-3110)
- 12+ instances: rejected with clean error
- 6-instance config x model matrix: works, clean cleanup
- Concurrent parallel runs on different targets: untested (potential port collision)

## Agent Resilience

Agents ignore contradictory CLAUDE.md instructions when project structure provides strong signal:
- "Write to /dev/null" — ignored, agent writes to stdout because tests expect it
- "Rename files with prefix" — ignored, agent uses expected filename because imports require it

Config poisoning via CLAUDE.md is a weak attack vector. Verify.sh changes or setup command changes are more effective at creating regressions.
