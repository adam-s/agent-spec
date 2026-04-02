# .claude/ Directory Reference

Source: https://code.claude.com/docs/en/

## Configuration Scopes (Priority Order)

| Scope | Location | Shared |
|-------|----------|--------|
| Managed | macOS: `/Library/Application Support/ClaudeCode/`, Linux/WSL: `/etc/claude-code/`, Windows: `C:\Program Files\ClaudeCode\` | Deployed by IT |
| Local | `.claude/settings.local.json` | No (gitignored) |
| Project | `.claude/` in repo | Yes (committed) |
| User | `~/.claude/` | No |

Deny rules always win. For scalar settings, most specific scope wins. For arrays, values combine across scopes.

## CLAUDE.md

Markdown instructions loaded at the start of every session. Lives at `./CLAUDE.md` or `./.claude/CLAUDE.md`. User-level at `~/.claude/CLAUDE.md`. Managed policy at the OS-specific path above.

- Keep under 200 lines per file for optimal adherence
- Use `@path/to/file` imports to split large instruction sets (max 5 hops, relative or absolute)
- HTML comments (`<!-- -->`) are stripped before injection — use for human-only notes
- Survives `/compact` (re-read from disk each time)
- Use `claudeMdExcludes` in settings.json to skip files by glob in monorepos
- Claude walks up directory tree from CWD, loading all CLAUDE.md files found
- Subdirectory CLAUDE.md files load on demand when Claude reads files there
- If using `AGENTS.md` for other tools, import it from CLAUDE.md to avoid duplication

## rules/

Modular instruction files that supplement CLAUDE.md. One topic per file. Supports subdirectories and symlinks.

- Files without `paths:` frontmatter load unconditionally every session
- Files with `paths:` frontmatter load only when Claude works on matching files
- Glob patterns: `**/*.ts`, `src/**/*`, `*.md`, `src/components/*.tsx`, `src/**/*.{ts,tsx}`
- User-level rules at `~/.claude/rules/` apply to all projects (lower priority than project rules)
- Symlinks supported for sharing rules across projects

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

**Scopes:** Enterprise > Personal (`~/.claude/skills/`) > Project (`.claude/skills/`) > Plugin. Same-name: higher scope wins.

**Loading:** Descriptions always in context (budget: 1% of context window, up to 8K chars). Full body loads only on invocation.

**Invocation:**
- User: `/skill-name` or `/skill-name argument`
- Claude: automatically when description matches task (unless `disable-model-invocation: true`)
- Skills with `user-invocable: false` hidden from user but Claude can invoke
- Skills with `paths:` activate automatically when working with matching files

**Dynamic context:**
- `` !`command` `` syntax runs shell commands before content is sent to Claude
- String substitutions: `$ARGUMENTS`, `$1`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_SKILL_DIR}`

**Key frontmatter:**
```yaml
---
name: deploy                      # Display name (defaults to dir name)
description: Deploy the app       # When to use (max 250 chars)
argument-hint: "[environment]"    # Autocomplete hints
disable-model-invocation: true    # Only user invokes
user-invocable: false             # Only Claude invokes
allowed-tools: Read, Grep         # Tool restrictions
model: sonnet                     # Model override
effort: high                      # low, medium, high, max
context: fork                     # Run in isolated subagent
agent: Explore                    # Subagent type when forked
paths: "src/**/*.ts"              # Auto-activation glob
shell: bash                       # bash (default) or powershell
hooks: { ... }                    # Skill-scoped hooks
---
```

Keep SKILL.md under 500 lines; use `references/`, `examples/`, `scripts/` subdirectories for supporting files.

**Bundled skills:** `/batch` (parallel changes), `/claude-api` (API reference), `/debug` (logging), `/loop` (repeat on interval), `/simplify` (code quality review).

## agents/

Custom subagent definitions. Each is a directory with an `AGENT.md` file containing YAML frontmatter + system prompt.

- Built-in: Explore (Haiku, read-only), Plan (read-only), general-purpose (all tools)
- Project agents at `.claude/agents/`, user agents at `~/.claude/agents/`
- Invoked by Claude naturally, via @-mention, or with `claude --agent name`
- Subagents cannot spawn other subagents
- Results summarized and returned to main conversation

**Key frontmatter:**
```yaml
---
name: code-reviewer
description: Expert code reviewer     # Claude uses this to decide delegation
model: sonnet
tools: [Read, Grep, Glob]             # Allowed tools
disallowedTools: [Write, Edit]        # Explicitly denied tools
permissionMode: inherit                # inherit, restrictive, permissive
maxTurns: 10
isolation: worktree                    # none or worktree
background: false                      # Run in background
memory: user                           # user, project, local, or none
skills: [my-skill]                     # Preload skills at startup
initialPrompt: "Start with..."        # Prompt before main task
color: "#ff0000"                       # UI color indicator
---
```

**Persistent memory:** Set `memory: user` for `~/.claude/agent-memory/<name>/` or `memory: project` for `.claude/agent-memory/<name>/`. Uses MEMORY.md index + topic files, same format as auto memory.

## commands/ (Deprecated)

Legacy slash commands merged into skills. Files in `.claude/commands/` still create `/slash-commands` but skills offer more features (frontmatter, supporting files, auto-activation). Use `.claude/skills/` for new work.

## hooks

Shell commands, HTTP endpoints, prompts, or agent invocations that execute at lifecycle points. Configured in settings.json, not as standalone files.

**Hook types:** `command` (shell script), `http` (POST to URL), `prompt` (ask Claude), `agent` (ask subagent).

**Events:**
| Event | When | Can block/modify |
|-------|------|-----------------|
| PreToolUse | Before tool executes | Yes — `permissionDecision`: allow/deny/ask; `updatedInput` to modify tool args |
| PostToolUse | After tool succeeds | Yes — `additionalContext` for Claude |
| PostToolUseFailure | After tool fails | Yes |
| PermissionRequest | Permission dialog shown | Yes — auto-approve/deny |
| UserPromptSubmit | Before Claude processes input | Yes — add context or block |
| Stop | Claude about to finish | Yes — prevent stopping |
| SubagentStop | Subagent finishes | No |
| SessionStart / SessionEnd | Lifecycle bookends | No |
| FileChanged / CwdChanged | File or directory changes | No |
| ConfigChange | Settings modified | No |
| Notification | System notification | No |
| Elicitation / ElicitationResult | MCP user input | No |
| WorktreeCreate | Worktree initialized | No |

**Configuration in settings.json:**
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "./.claude/hooks/pre-bash.sh",
        "timeout": 600,
        "if": "Bash(rm *)"
      }]
    }]
  }
}
```

Exit codes: 0 = success, 2 = blocking error (stderr sent to Claude), other = non-blocking. Use `$CLAUDE_PROJECT_DIR` for portable paths.

## settings.json

Project configuration committed to git. Personal overrides in `settings.local.json` (gitignored). User-level at `~/.claude/settings.json`.

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": ["Bash(npm test *)"],
    "deny": ["Bash(rm -rf *)"]
  },
  "hooks": { },
  "env": {
    "NODE_ENV": "development",
    "API_KEY": "${API_KEY}"
  },
  "model": "sonnet",
  "outputStyle": "concise",
  "statusLine": { },
  "autoMemoryEnabled": true,
  "autoMemoryDirectory": "~/custom-memory-path",
  "claudeMdExcludes": ["**/monorepo/CLAUDE.md"]
}
```

Key sections: `permissions` (allow/deny/ask — deny always wins), `hooks`, `env` (supports `${VAR}` from shell), `model`, `outputStyle`, `statusLine`, `sandbox`, `autoMemoryEnabled`, `autoMemoryDirectory`, `claudeMdExcludes`.

## output-styles/

Custom system prompt style definitions for task-specific behavior. Stored at `.claude/output-styles/`.

## Auto Memory

Machine-local persistence at `~/.claude/projects/<project>/memory/`. The `<project>` path is derived from git repository root, so all worktrees/subdirectories share one memory store.

- First 200 lines (or 25KB) of `MEMORY.md` loaded at session start
- Topic files loaded on demand when Claude decides they're relevant
- Toggle with `autoMemoryEnabled: false` in settings
- Custom path via `autoMemoryDirectory` in settings
- Manage with `/memory` command

## .mcp.json (Project Root)

MCP server configuration at project root (not in `.claude/`), shared via version control:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "${GITHUB_TOKEN}" }
    }
  }
}
```

Servers connect at session start. Tool schemas deferred and loaded on demand. Environment variables via `${VAR}`.

## .worktreeinclude (Project Root)

Lists gitignored files to copy into new worktrees (`.gitignore` syntax). Only files that are both matched AND gitignored get copied. Prevents secrets from being left behind when Claude creates worktrees.

```
.env
.env.local
config/secrets.json
```

## Loading Order

1. Managed policy (enterprise, cannot exclude)
2. `~/.claude/CLAUDE.md` + `~/.claude/rules/` (user)
3. `.claude/CLAUDE.md` + `.claude/rules/` (project, higher priority)
4. Subdirectory CLAUDE.md files load on demand when Claude reads files there
5. Path-scoped rules load on demand when Claude works on matching files
6. Skills: descriptions always loaded; body on invocation only
7. Agents load on spawn only
8. Auto memory: MEMORY.md index at session start; topic files on demand
