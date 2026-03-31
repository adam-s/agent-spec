# agent-spec

**The `.claude/` directory and CLAUDE.md are the product.** Every iteration improves the instructions, rules, skills, and utilities. The code exists to test the instructions. The instructions are what ship.

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

## Port Management

When running multiple targets in parallel:

- **invoke.sh allocates unique ports** from the 3100–3110 range (one per run)
- **__PORT__ substitution** in prompts: `port 3100` → `port 3101` (per allocation)
- **PORT environment variable** passed to verify.sh and test.js (via `process.env.PORT`)
- **Port collision prevention**: Each parallel run gets a unique port; clear-ports.sh sweeps reserved ranges before/after

When adding a new target that needs a port:
1. Use `__PORT__` in prompt.md instead of hardcoding 3100
2. Update verify.sh to accept PORT from environment: `PORT="${PORT:-3100}"`
3. Update test.js to read PORT: `const PORT = process.env.PORT || 3100`
4. invoke.sh handles the rest automatically

## Reference

See @.claude/reference/claude-directory-reference.md for .claude/ directory best practices.
See @.claude/reference/bug-catalog.md for known bug classes discovered during iterations.
