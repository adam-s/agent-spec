# Hooks Reference

Hooks are mechanical enforcement — deterministic actions that fire at lifecycle points. If the answer is always the same regardless of context, it should be a hook, not an instruction.

## Hook Types

| Type | What it does | When to use |
| ---- | ------------ | ----------- |
| `command` | Runs a shell script | Most hooks. Fast, local, stdin/stdout. |
| `http` | POSTs event JSON to a URL | External services, shared audit logging. |
| `prompt` | Single-turn LLM call (Haiku default) | Judgment calls that don't need tool access. |
| `agent` | Multi-turn subagent with tools | Verification requiring file reads, test runs. |

**Diagnosis:** If a hook needs to read files or run commands to decide, it's an `agent` hook. If it just needs to reason about the input JSON, it's a `prompt` hook. If the answer is deterministic, it's a `command` hook.

## Events

### Tool lifecycle

| Event | When | Can block | Matcher filters |
| ----- | ---- | --------- | --------------- |
| `PreToolUse` | Before tool executes | Yes — allow/deny/ask | Tool name |
| `PostToolUse` | After tool succeeds | Context injection only | Tool name |
| `PostToolUseFailure` | After tool fails | Context injection only | Tool name |
| `PermissionRequest` | Permission dialog about to show | Yes — auto-approve/deny | Tool name |
| `PermissionDenied` | Tool denied by auto mode | Return `{retry: true}` | Tool name |

### Session lifecycle

| Event | When | Can block | Matcher filters |
| ----- | ---- | --------- | --------------- |
| `SessionStart` | Session begins/resumes | No | `startup`, `resume`, `clear`, `compact` |
| `SessionEnd` | Session terminates | No | `clear`, `resume`, `logout`, etc. |
| `Stop` | Claude finishes responding | Yes — prevent stopping | No matcher |
| `StopFailure` | Turn ends from API error | No | Error type |

### Context and config

| Event | When | Can block | Matcher filters |
| ----- | ---- | --------- | --------------- |
| `UserPromptSubmit` | Before Claude processes input | Yes | No matcher |
| `PreCompact` | Before compaction | No | `manual`, `auto` |
| `PostCompact` | After compaction | No | `manual`, `auto` |
| `InstructionsLoaded` | CLAUDE.md/rule loaded | No | Load reason |
| `ConfigChange` | Settings file modified | Yes — block change | Config source |
| `Notification` | System notification fires | No | Notification type |

### Subagents and tasks

| Event | When | Can block | Matcher filters |
| ----- | ---- | --------- | --------------- |
| `SubagentStart` | Subagent spawned | No | Agent type |
| `SubagentStop` | Subagent finishes | No | Agent type |
| `TaskCreated` | Task created via TaskCreate | No | No matcher |
| `TaskCompleted` | Task marked complete | No | No matcher |
| `TeammateIdle` | Team teammate about to idle | No | No matcher |

### Environment

| Event | When | Can block | Matcher filters |
| ----- | ---- | --------- | --------------- |
| `CwdChanged` | Working directory changes | No | No matcher |
| `FileChanged` | Watched file changes on disk | No | Filename (basename) |
| `WorktreeCreate` | Worktree initialized | No | No matcher |
| `WorktreeRemove` | Worktree removed | No | No matcher |

### MCP

| Event | When | Can block | Matcher filters |
| ----- | ---- | --------- | --------------- |
| `Elicitation` | MCP server requests user input | No | MCP server name |
| `ElicitationResult` | User responds to MCP elicitation | No | MCP server name |

## Execution Model

- All matching hooks for an event run **in parallel**.
- Identical hook commands are deduplicated.
- When multiple hooks return decisions, **most restrictive wins** — one `deny` cancels regardless of other hooks returning `allow`.
- `additionalContext` text is kept from every hook and passed to Claude together.

## Input/Output Contract

**Input:** JSON on stdin with `session_id`, `cwd`, `hook_event_name`, and event-specific fields (e.g., `tool_name`, `tool_input` for tool events).

**Output:**

- **Exit 0** — action proceeds. Stdout added as context (for `UserPromptSubmit`, `SessionStart`).
- **Exit 2** — action blocked. Stderr sent to Claude as feedback.
- **Other exit** — action proceeds. Stderr logged but not shown to Claude.
- **Structured JSON on stdout** — for fine-grained control (permission decisions, context injection, input rewriting).

**Key structured outputs:**
- `PreToolUse`: `permissionDecision` (allow/deny/ask), `updatedInput` (rewrite tool args)
- `PermissionRequest`: `decision.behavior` (allow/deny) with optional `updatedPermissions` to set session permission mode
- `PostToolUse`/`Stop`: `decision: "block"`

## Filtering

**`matcher`** — regex on the group level. Filters by tool name, session source, error type, etc. depending on event. Case-sensitive.

**`if`** — permission-rule syntax on the individual hook level. Filters by tool name AND arguments. Example: `"if": "Bash(git *)"` only fires for git commands, not all Bash.

## Design Principles

- Always consume stdin — hooks that don't read stdin cause pipe errors
- `additionalContext` to guide, `permissionDecision: deny` to hard-block
- Keep hooks fast — they fire on every matching tool call
- Match narrowly — broad matchers fire on unrelated commands
- One concern per script
- Exit 0 silently on no-match, only output JSON when the hook applies
- Use `$CLAUDE_PROJECT_DIR` for paths, never hardcode absolutes
- `PostToolUse` cannot undo — the tool already executed
- `PermissionRequest` does not fire in headless mode (`-p`) — use `PreToolUse` instead
- `PreToolUse` fires before permission-mode checks — a hook `deny` blocks even in `bypassPermissions`. Hooks can tighten restrictions but not loosen them past permission rules

## Key Patterns

**Re-inject context after compaction:** `SessionStart` with `compact` matcher. Stdout becomes Claude's context. Use for reminders that must survive compaction.

**Auto-approve specific prompts:** `PermissionRequest` with narrow matcher (e.g., `ExitPlanMode`). Return `decision.behavior: "allow"`. Can also set session permission mode via `updatedPermissions`.

**Persist environment variables:** `CwdChanged` or `FileChanged` hooks write to `$CLAUDE_ENV_FILE`. Claude applies these before each Bash command. Useful for direnv-style workflows.

## Common Misconfigurations

| Problem | Symptom | Fix |
| ------- | ------- | --- |
| Hook doesn't read stdin | Pipe errors, intermittent failures | Add `INPUT=$(cat)` at top of script |
| Broad matcher | Hook fires on unrelated tools | Narrow with specific tool name or `if` field |
| Stop hook without `stop_hook_active` check | Infinite loop — Claude never stops | Check `stop_hook_active` field, exit 0 if true |
| Shell profile prints to stdout | JSON parse errors | Wrap echo in `[[ $- == *i* ]]` check |
| Multiple hooks rewrite same tool input | Non-deterministic behavior | Only one hook should use `updatedInput` per tool |
| Hook in CLAUDE.md instead of settings.json | Claude forgets under token pressure | Move to settings.json as a proper hook |

## Scope

| Location | Scope | Shareable |
| -------- | ----- | --------- |
| `~/.claude/settings.json` | All projects | No |
| `.claude/settings.json` | Single project | Yes (committed) |
| `.claude/settings.local.json` | Single project | No (gitignored) |
| Managed policy | Organization-wide | Admin-controlled |
| Plugin `hooks/hooks.json` | When plugin enabled | Yes |
| Skill/agent frontmatter | While active | Yes |
