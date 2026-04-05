# Known System Limits

Empirical limits discovered through testing. These are not hard constraints — they shift with model, config, and task complexity.

## Budget Behavior

Cost variance for the same task is ~2x. Budget cliffs are fuzzy, not sharp — there's no clean threshold between "always passes" and "always fails."

## Output Format Contracts

When verify.sh greps for specific strings in test output, it creates a hidden contract. If the agent recreates files, it will use different phrasing and fail verification even though the code is correct.

**Fix:** Document the exact output format contract in the config's CLAUDE.md. Any verify.sh that pattern-matches output requires a corresponding instruction telling the agent what format to produce.

## Hooks in Headless Mode

Project hooks (`.claude/settings.json`) do not fire for sub-agents launched via `claude -p` with `--dangerously-skip-permissions`.

For behaviors that must be enforced in headless mode, use prompt injection via the eval prompt or CLAUDE.md instructions. Hooks are still valuable for interactive use — they just can't be tested through the eval harness.

## Agent Resilience to Contradictory Instructions

Agents ignore contradictory CLAUDE.md instructions when project structure provides strong signal (e.g., imports, test expectations). Config poisoning via CLAUDE.md is a weak attack vector. Verify.sh or setup command changes are more effective at creating regressions.

## Parallel Limits

Max simultaneous instances is bounded by the reserved port range (3100-3110). Concurrent parallel runs on different targets risk port collision.
