# agent-spec

**STOP CRASHING THE MACHINE. DO NOT USE ALL SYSTEM RESOURCES.** Before launching ANY process that spawns a Claude agent, confirm with the user. One agent at a time. Sequential, not parallel. Always use `run_in_background`. Never block the conversation waiting for a run. See @.claude/rules/resource-safety.md — these rules are non-negotiable.

we are developing the agent-spec. This is the early period we are doing a lot of trial and error and we can delete, change, or add anything that is needed to ensure the project is simple, clean, and organized. we don't need to worry about backwards compatibility. If we make a change and an older code still uses it, we change the older code to use the better newer code. This is the same with instructions for .claude

## The Trainer of Trainers

agent-spec is a development tool for `.claude/` directories. It takes any project, launches parallel agents in disposable sandboxes, observes what the agents get right and wrong, and uses that signal to improve the project's `.claude/` — its CLAUDE.md, rules, skills, agents, or reference docs.

The target repositories (hono-websocket-counter, csv-reporter, sqlite-window-queries) are test fixtures — they exist to exercise the harness, not as deliverables. The product is agent-spec itself: its skills, scripts, rules, and the ability to sit down with any project and iteratively develop its `.claude/` until autonomous agents succeed without human intervention.

This applies recursively. The `.claude/` that agent-spec develops for a target project can itself contain skills that guide autonomous behavior. See @.claude/reference/recursive-training.md for the Level 0/1/2 architecture and guards.

## Product vs Test Output

Fixture results (run IDs, token counts, pass/fail per target, benchmark tables) are ephemeral test output. Read them, extract the generalized lesson, then improve the harness. Never commit fixture-specific results or domain-specific findings. The only artifacts worth committing are generalized improvements to agent-spec's skills, scripts, rules, and reference docs. If a finding only applies to one fixture, it is noise — the product must work for any project.

**MANDATORY**: We do not use the word "kill" in user-facing output, comments, or documentation, even though the underlying CLI command may be `kill`. Use descriptive terms like "stop", "halt", "terminate", or "shut down" instead.

## How to Operate

Use existing skills and scripts — do not reimplement what already exists. See @.claude/rules/operational-workflow.md for the full tool inventory, workflow patterns, and when to use each.

Before launching any eval or parallel run, confirm with the user. See @.claude/rules/resource-safety.md.

Key skills: `/run-eval`, `/iterate`, `/report`, `/stop`, `/new-target`

## Key Concepts

- **Sandboxes** live in `/tmp/claude/agent-spec-{uuid}/` — disposable copies, originals never modified
- **Ports** 3100-3110 allocated per run; use `__PORT__` in prompt.md, `--port N` for parallel pre-assignment
- **Cordyceps** — delete, inject, or swap any file in sandbox before the agent sees it

## Monitoring

Runs log structured JSONL events to `/tmp/agent-spec/{run_id}/events.jsonl`.

**IMPORTANT**: When launching long-running eval or parallel runs, ALWAYS print the monitoring command for the user to run in a separate terminal. Do NOT block waiting, sleep-poll, or run background watches. Instead, tell the user:

> To watch live, run in another terminal:
> `tail -f /tmp/agent-spec-parallel-out-*.log`
> or: `python3 scripts/dashboard.py --latest`

Then use `run_in_background` for the actual run and let the system notify you when it completes.

### Commands

```bash
# Watch a run live (color-coded, formatted)
python3 scripts/dashboard.py <run_id>
python3 scripts/dashboard.py --latest

# Compact grep-friendly output (no ANSI colors)
python3 scripts/dashboard.py <run_id> --stream

# Watch all parallel runs at once
tail -f /tmp/agent-spec-parallel-out-*.log

# Multi-instance parallel status table
python3 scripts/dashboard.py --parallel <parallel_id>

# Config diff between two runs
python3 scripts/dashboard.py --diff <run_id1> <run_id2>

# Cost rollup across an iterate session
python3 scripts/tokens.py --session <session_id>

# Diagnose a failed run
cat /tmp/agent-spec/<run_id>/stderr.log
python3 scripts/dashboard.py <run_id> --summary
```

See @.claude/rules/log-protocol.md for the full event schema and all reading tools.

## Git

The git repository root is the **parent directory** (`agent-spec/`), not the working directory (`agent-spec/agent-spec/`). All git commands (status, add, commit, push) must target the parent. The parent repo contains multiple applications.

## How `.claude/` Works

- **`rules/`** — Always loaded. Keep lean.
- **`skills/`** — Metadata loaded; body on invocation.
- **`reference/`** — Never auto-loaded. Looked up on demand.
- **`hooks/`** — Shell commands triggered by tool events.
