# agent-spec

A deterministic evaluation harness for Claude Code agents. This project copies entire repositories into isolated sandboxes, swaps their `.claude/` configurations, runs prompts via sub-agents, and measures tokens, cost, and correctness.

## What this project does

- Copies target repos into `/tmp/claude/agent-spec-{uuid}/` for isolation
- Swaps `.claude/` directories to A/B test different instruction sets
- Invokes `claude -p` with structured JSON output capture (APC)
- Monitors token burn, system resources, and task completion
- Scores results with per-target verification scripts
- Reports comparisons across configs for the same target

## What this project does NOT do

- It does not contain the applications being tested — those live in sibling directories or external repos
- It does not modify the target repos — sandboxes are disposable copies
