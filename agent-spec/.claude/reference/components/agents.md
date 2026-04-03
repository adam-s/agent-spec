# Agents Reference

Agents (subagents) are isolated execution environments with their own context window, system prompt, tool access, and permissions. They compose the atomic components — hooks, skills, permissions, and model config — into a self-contained worker.

Unlike skills (instructions Claude follows in the main context), agents run in a separate context window. The main conversation only sees the summary they return.

## Built-in Agents

| Agent | Model | Tools | Purpose |
| ----- | ----- | ----- | ------- |
| Explore | Haiku | Read-only | Fast codebase search and analysis |
| Plan | Inherit | Read-only | Research during plan mode |
| general-purpose | Inherit | All | Complex multi-step tasks |

## Frontmatter Fields

Only `name` and `description` are required. Everything else has sensible defaults.

| Field | What it does |
| ----- | ------------ |
| `name` | Unique identifier. Lowercase, hyphens. |
| `description` | When Claude should delegate. Claude matches against this. |
| `tools` | Allowlist of tools. Inherits all if omitted. Supports `Agent(worker, researcher)` to restrict spawnable subagents. |
| `disallowedTools` | Denylist. Applied before `tools`. |
| `model` | `sonnet`, `opus`, `haiku`, full model ID, or `inherit` (default). |
| `permissionMode` | `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan`. |
| `maxTurns` | Max agentic turns before stopping. |
| `skills` | Skills preloaded at startup (full content injected, not just description). |
| `mcpServers` | MCP servers scoped to this agent. Inline definitions or string references. |
| `hooks` | Lifecycle hooks scoped to this agent's execution. |
| `memory` | Persistent memory: `user`, `project`, or `local`. |
| `background` | `true` = always run as background task. |
| `effort` | `low`, `medium`, `high`, `max`. Overrides session level. |
| `isolation` | `worktree` = isolated git worktree copy. |
| `color` | UI color: `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, `cyan`. |
| `initialPrompt` | Auto-submitted first turn when running as main agent (`--agent`). |

## Scopes

| Priority | Location | Scope |
| -------- | -------- | ----- |
| 1 | Managed settings | Organization-wide |
| 2 | `--agents` CLI flag (JSON) | Current session only |
| 3 | `.claude/agents/` | This project |
| 4 | `~/.claude/agents/` | All your projects |
| 5 | Plugin `agents/` | Where plugin enabled |

Same-name: higher priority wins.

## How Agents Compose Other Components

This is what makes agents the composition layer:

| Component | How agents use it |
| --------- | ----------------- |
| **Hooks** | `hooks:` frontmatter scopes hooks to agent lifecycle. PreToolUse for validation, PostToolUse for linting, Stop converted to SubagentStop. |
| **Skills** | `skills:` preloads full skill content at startup (not just description). Agents don't inherit parent skills. |
| **Permissions** | `permissionMode:` sets the mode. `tools:`/`disallowedTools:` restricts access. Parent `bypassPermissions` or `auto` takes precedence. |
| **MCP** | `mcpServers:` connects servers scoped to this agent. Inline definitions stay out of main context. |
| **Model** | `model:` overrides. Resolution: env var > per-invocation > frontmatter > parent model. |

## Permission Inheritance

- Agents inherit parent conversation's permission context
- `permissionMode` in frontmatter can override — with exceptions:
  - Parent `bypassPermissions` → takes precedence, cannot be overridden
  - Parent `auto` mode → agent inherits auto mode, frontmatter `permissionMode` ignored
- Plugin agents cannot use `hooks`, `mcpServers`, or `permissionMode` (security restriction)

## Foreground vs Background

| Mode | Behavior | Permissions |
| ---- | -------- | ----------- |
| Foreground | Blocks main conversation. Permission prompts pass through. | Interactive |
| Background | Concurrent. Permissions pre-approved at launch. | Auto-deny anything not pre-approved |

Background agents that fail due to missing permissions: retry as foreground.

## Persistent Memory

| Scope | Location | Use when |
| ----- | -------- | -------- |
| `user` | `~/.claude/agent-memory/<name>/` | Learnings apply across all projects |
| `project` | `.claude/agent-memory/<name>/` | Project-specific, shareable via git |
| `local` | `.claude/agent-memory-local/<name>/` | Project-specific, not committed |

When enabled: MEMORY.md (first 200 lines / 25KB) loaded at start. Read/Write/Edit tools auto-enabled.

## Key Constraints

- **Subagents cannot spawn other subagents.** For nested delegation, chain from main conversation or use skills.
- **Subagents don't inherit skills.** Must be listed explicitly in `skills:` frontmatter.
- **Results return to main context.** Many agents returning detailed results can consume significant context.
- **`--agent` replaces the system prompt entirely.** CLAUDE.md and memory still load normally.

## Running as Main Agent

`claude --agent code-reviewer` or `"agent": "code-reviewer"` in settings.json. The agent's system prompt replaces Claude Code's default. Can restrict which subagents it spawns via `Agent(name)` in `tools`.

## Common Misconfigurations

| Problem | Symptom | Fix |
| ------- | ------- | --- |
| Agent that should be a skill | Unnecessary context isolation, slower startup | If it doesn't need tool restrictions or isolated context, make it a skill |
| Skill that should be an agent | No tool restrictions, runs in main context | If it needs isolation or restricted tools, make it an agent |
| Missing tool restrictions | Agent inherits everything, does unintended work | Set `tools:` or `disallowedTools:` explicitly |
| Wrong model for the job | Opus for read-only search (expensive), Haiku for complex reasoning (fails) | Match model to task complexity |
| `memory: user` for project-specific knowledge | Knowledge leaks across projects | Use `memory: project` or `memory: local` |
| Many background agents returning verbose results | Main context fills up | Reduce result verbosity or use agent teams for sustained parallelism |
| Plugin agent expecting hooks/permissions | Fields silently ignored | Copy agent to `.claude/agents/` if hooks/mcpServers/permissionMode needed |
| `skills:` listing skills by name but agent can't find them | Skill not in scope for agent | Ensure skills exist at project or user level |

## Relationship to Other Components

- **Agents vs skills:** Skills are instructions that run in context. Agents are isolated environments. Use agents when you need tool restrictions, model override, or context isolation. Use skills for everything else.
- **Agents vs hooks:** Hooks are mechanical (zero tokens, deterministic). Agent `hooks:` frontmatter scopes hooks to the agent's lifecycle — they're complementary, not alternatives.
- **Agents vs rules:** Rules load into the main context. Agent system prompts replace it. If guidance only applies during a specific workflow, put it in an agent's markdown body rather than a rule.
- **Agent teams vs subagents:** Subagents work within one session. Agent teams coordinate across separate sessions with sustained parallelism. Subagents for bounded tasks; teams for open-ended parallel work.
