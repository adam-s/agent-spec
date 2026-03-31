# agent-spec

## The Trainer of Trainers

**The `.claude/` directory and CLAUDE.md are the product.** Every iteration improves the instructions, rules, skills, and utilities. The code exists to test the instructions. The instructions are what ship.

This applies recursively. agent-spec trains other projects' `.claude/` directories — the product of that training can itself be a skill that guides autonomous agent behavior. This creates nested levels: the trainer (Level 0) iterates on instructions (Level 2) by observing sub-agents (Level 1) that follow those instructions in disposable sandboxes.

See @.claude/reference/recursive-training.md for the full architecture, guards, and fix classification rules.

**MANDATORY**: We do not use the word "kill" in user-facing output, comments, or documentation, even though the underlying CLI command may be `kill`. Use descriptive terms like "stop", "halt", "terminate", or "shut down" instead.

A deterministic evaluation harness for Claude Code agents. This project copies entire repositories into isolated sandboxes, swaps their `.claude/` configurations, runs prompts via sub-agents, and measures tokens, cost, and correctness.

## How to Operate

Use existing skills and scripts — do not reimplement what already exists. See @.claude/rules/operational-workflow.md for the full tool inventory, workflow patterns, and when to use each.

Key skills: `/run-eval`, `/iterate`, `/report`, `/stop`, `/new-target`

## Key Concepts

- **Sandboxes** live in `/tmp/claude/agent-spec-{uuid}/` — disposable copies, originals never modified
- **Ports** 3100-3110 allocated per run; use `__PORT__` in prompt.md, `--port N` for parallel pre-assignment
- **Cordyceps** — delete, inject, or swap any file in sandbox before the agent sees it

## Reference

- @.claude/rules/operational-workflow.md — tools, scripts, and workflow patterns
- @.claude/rules/port-management.md — port ranges, PID registry, verify.sh patterns
- @.claude/rules/testing-protocol.md — sandbox lifecycle, cordyceps, scoring contract
- @.claude/rules/log-protocol.md — JSONL event format, reading and emitting events
- @.claude/reference/recursive-training.md — Level 0/1/2 architecture and guards
- @.claude/reference/bug-catalog.md — known failure classes from past iterations
- @.claude/reference/claude-directory-reference.md — .claude/ directory best practices
