---
name: handoff
description: Write a handoff document so a new chat can continue the work
argument-hint: <name>
---

# /handoff — Prepare a handoff for a new chat

Write a focused handoff document that a fresh Claude session can execute without needing this conversation's context.

## Argument

- `$1` — short name for the handoff file (e.g. `token-efficiency-runs`). If omitted, derive from the current task.

## Steps

1. **Summarize what was done** in this session: key decisions, files created/modified, what's working.

2. **Define what's left** for the next chat: specific tasks, in what order, with exact commands where possible.

3. **State constraints**: rules the next chat must follow (e.g. "one agent at a time", "don't modify configs", "run in background").

4. **Write the handoff** to `docs/handoff/<name>.md`:

```
docs/handoff/<name>.md
```

## Handoff Format

```markdown
# <Title>

## What Was Done
<Brief summary of completed work, key files, decisions made>

## Task
<What the next chat should do, step by step>

## Commands
<Exact commands to run, in order>

## Constraints
<Rules and boundaries>
```

## Guidelines

- The handoff must be **self-contained**. The next chat reads this file and nothing else from the conversation.
- Include file paths when referencing files the next chat needs to read.
- Keep it under 80 lines. If the next chat needs more context, point it at specific files to read — don't paste content into the handoff.
- Do not include reasoning, alternatives considered, or conversation history. Just what to do.
- Tell the user: "Start a new chat and say: `read docs/handoff/<name>.md and execute it`"
