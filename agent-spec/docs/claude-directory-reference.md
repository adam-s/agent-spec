# .claude/ Directory Reference

Source: https://code.claude.com/docs/en/

## CLAUDE.md

Markdown instructions loaded at the start of every session. Lives at `./CLAUDE.md` or `./.claude/CLAUDE.md`. User-level instructions at `~/.claude/CLAUDE.md` apply to all projects.

- Keep under 200 lines per file
- Use `@path/to/file` imports to split large instruction sets (max 5 hops)
- HTML comments (`<!-- -->`) are stripped before injection — use for human-only notes
- Survives `/compact` (re-read from disk each time)
- Use `claudeMdExcludes` in settings.json to skip files by glob in monorepos

## rules/

Modular instruction files that supplement CLAUDE.md. One topic per file. Supports subdirectories and symlinks.

- Files without `paths:` frontmatter load unconditionally every session
- Files with `paths:` frontmatter load only when Claude works on matching files — use this to save context on large instruction sets
- User-level rules at `~/.claude/rules/` apply to all projects (lower priority than project rules)

```markdown
---
paths:
  - "src/api/**/*.ts"
---
# API Rules
...
```

## skills/

Reusable instruction packages that load on demand, not every session. Each skill is a directory with a `SKILL.md` entrypoint. Follows the [Agent Skills](https://agentskills.io) open standard.

- Invoked by user via `/skill-name` or by Claude when `disable-model-invocation` is not set
- `context: fork` runs the skill in an isolated subagent
- `!`command`` syntax in SKILL.md runs shell commands for dynamic context injection
- String substitutions: `$ARGUMENTS`, `$1`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_SKILL_DIR}`
- Keep SKILL.md under 500 lines; use `references/`, `examples/`, `scripts/` subdirectories for supporting files

Key frontmatter: `name`, `description`, `disable-model-invocation`, `allowed-tools`, `model`, `effort`, `context`, `agent`, `paths`.

## agents/

Custom subagent definitions as markdown files with YAML frontmatter. Each runs in its own context window with custom instructions, tool access, and permissions.

- Built-in agents: Explore (Haiku, read-only), Plan (read-only), general-purpose (all tools)
- Project agents at `.claude/agents/`, user agents at `~/.claude/agents/`
- Invoked by Claude naturally, via @-mention, or with `claude --agent name`
- Subagents cannot spawn other subagents

Key frontmatter: `name`, `description`, `tools`, `model`, `maxTurns`, `isolation` (worktree), `memory` (user/project/local), `permissionMode`.

## hooks

Shell commands, HTTP endpoints, or prompts that execute at lifecycle points. Configured in settings.json, not as standalone files.

- **PreToolUse** — Validate or block tool calls before execution. Return `permissionDecision` (allow/deny/ask) or `additionalContext`
- **PostToolUse** — Run linting, notifications, or cleanup after tool calls
- **SubagentStop** — Clean up when a subagent finishes
- **WorktreeCreate** — Initialize isolated worktrees
- **SessionStart/SessionEnd** — Setup and teardown

Exit codes: 0 = success, 2 = blocking error (stderr sent to Claude), other = non-blocking.

Use `$CLAUDE_PROJECT_DIR` for portable paths. Keep hooks fast, especially SessionStart.

## settings.json

Project configuration committed to git. Personal overrides in `settings.local.json` (gitignored). User-level at `~/.claude/settings.json`.

- Add `"$schema": "https://json.schemastore.org/claude-code-settings.json"` for editor autocomplete
- Key sections: `permissions` (allow/deny/ask), `hooks`, `model`, `sandbox`
- Deny rules take priority over allow rules

## agent-memory/

Persistent memory scoped to a named agent. Stored at `.claude/agent-memory/<name>/MEMORY.md` (project) or `~/.claude/agent-memory/<name>/MEMORY.md` (user). Enable with `memory: project` in agent frontmatter.

## Loading Order

1. Managed policy (enterprise, cannot exclude)
2. `~/.claude/CLAUDE.md` + `~/.claude/rules/` (user)
3. `.claude/CLAUDE.md` + `.claude/rules/` (project, higher priority)
4. Subdirectory CLAUDE.md files load on demand when Claude reads files there
5. Skills load on invocation only
6. Agents load on spawn only
