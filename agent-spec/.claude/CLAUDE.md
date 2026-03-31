# agent-spec

## The Trainer of Trainers

agent-spec is a development tool for `.claude/` directories. It takes any project, launches parallel agents in disposable sandboxes, observes what the agents get right and wrong, and uses that signal to improve the project's `.claude/` — its CLAUDE.md, rules, skills, agents, or reference docs. The iteration loop (`/iterate`) is the core workflow: run agents → score → diagnose → fix instructions → rerun until agents pass autonomously.

The target repositories (hono-websocket-counter, csv-reporter, sqlite-window-queries) are test fixtures — they exist to exercise the harness, not as deliverables. The product is agent-spec itself: its skills, scripts, rules, and the ability to sit down with any project and iteratively develop its `.claude/` until autonomous agents succeed without human intervention.

This applies recursively. The `.claude/` that agent-spec develops for a target project can itself contain skills that guide autonomous behavior. See @.claude/reference/recursive-training.md for the Level 0/1/2 architecture and guards.

## Product vs Test Output

Fixture results (run IDs, token counts, pass/fail per target, benchmark tables) are ephemeral test output. Read them, extract the generalized lesson, then improve the harness. Never commit fixture-specific results or domain-specific findings. The only artifacts worth committing are generalized improvements to agent-spec's skills, scripts, rules, and reference docs. If a finding only applies to one fixture, it is noise — the product must work for any project.

**MANDATORY**: We do not use the word "kill" in user-facing output, comments, or documentation, even though the underlying CLI command may be `kill`. Use descriptive terms like "stop", "halt", "terminate", or "shut down" instead.

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
