# agent-spec

**MANDATORY**: We do not use the word "kill" in user-facing output, comments, or documentation, even though the underlying CLI command may be `kill`. Use descriptive terms like "stop", "halt", "terminate", or "shut down" instead.

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

## Sandboxes

Sandboxes live in `/tmp/claude/agent-spec-{uuid}/` (not local `tmp/`) so tested agents cannot see the harness. Create `/tmp/claude/` before running evals (Claude Code sandbox bug #36759).

## Reference

See @.claude/reference/claude-directory-reference.md for .claude/ directory structure documentation.
