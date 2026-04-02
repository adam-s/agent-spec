# Settings Reference

settings.json is client-enforced configuration — permissions, hooks, environment, model selection, and sandbox. Unlike CLAUDE.md and rules (guidance Claude reads), settings are enforced by Claude Code regardless of what Claude decides.

## Scopes and Precedence

Highest to lowest priority:

| Priority | Scope | Location | Shared |
| -------- | ----- | -------- | ------ |
| 1 | Managed | OS-specific paths + server-managed | Deployed by IT |
| 2 | CLI flags | `--model`, `--allowedTools`, etc. | Session only |
| 3 | Local | `.claude/settings.local.json` | No (gitignored) |
| 4 | Project | `.claude/settings.json` | Yes (committed) |
| 5 | User | `~/.claude/settings.json` | No |

## Merge Behavior

| Type | How it merges |
| ---- | ------------- |
| Scalars | Highest-priority scope wins |
| Arrays | Concatenated and deduplicated across all scopes |
| Objects | Deep-merged; more specific scope overrides per field |
| Deny rules | Always win over allow rules at any scope |

Arrays that merge: `permissions.allow/ask/deny`, `sandbox.filesystem.*`, `allowedHttpHookUrls`, `httpHookAllowedEnvVars`, `availableModels`, `allowedMcpServers`, `deniedMcpServers`.

## Key Settings by Category

### Permissions

| Key | What it does |
| --- | ------------ |
| `permissions.allow` | Tool use without approval. Array of rules. |
| `permissions.ask` | Require confirmation. Array of rules. |
| `permissions.deny` | Block tool use. Always wins. Array of rules. |
| `permissions.defaultMode` | `default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions` |
| `permissions.disableBypassPermissionsMode` | `"disable"` prevents bypass mode |
| `permissions.additionalDirectories` | Extra directories for file access |

### Hooks

| Key | What it does |
| --- | ------------ |
| `hooks` | Lifecycle hooks — see [hooks.md](hooks.md) |
| `disableAllHooks` | `true` disables all hooks and custom status line |
| `allowedHttpHookUrls` | URL patterns HTTP hooks may target (merges) |
| `httpHookAllowedEnvVars` | Env vars HTTP hooks can interpolate (merges) |
| `allowManagedHooksOnly` | (Managed only) Block user/project/plugin hooks |

### Model and Thinking

| Key | What it does |
| --- | ------------ |
| `model` | Override default model (e.g., `"claude-sonnet-4-6"`) |
| `availableModels` | Restrict model selection (e.g., `["sonnet", "haiku"]`) |
| `modelOverrides` | Map model IDs to provider-specific IDs (Bedrock ARNs) |
| `effortLevel` | `"low"`, `"medium"`, `"high"` — persists across sessions |
| `alwaysThinkingEnabled` | Enable extended thinking by default |

### Sandbox

| Key | What it does |
| --- | ------------ |
| `sandbox.enabled` | Enable OS-level Bash sandboxing |
| `sandbox.autoAllowBashIfSandboxed` | Auto-approve Bash when sandboxed |
| `sandbox.filesystem.allowWrite` | Writable paths (merges) |
| `sandbox.filesystem.denyWrite` | Non-writable paths (merges) |
| `sandbox.filesystem.denyRead` | Unreadable paths (merges) |
| `sandbox.network.allowedDomains` | Allowed outbound domains |

### Environment

| Key | What it does |
| --- | ------------ |
| `env` | Environment variables applied to every session |
| `autoMemoryEnabled` | Toggle auto memory (`false` to disable) |
| `autoMemoryDirectory` | Custom memory storage path |
| `claudeMdExcludes` | Skip CLAUDE.md files by glob (monorepos) |
| `agent` | Run main thread as a named subagent |
| `outputStyle` | System prompt style adjustment |

## What Goes in Settings vs Other Components

| Concern | Component | Why |
| ------- | --------- | --- |
| "Block rm -rf" | `permissions.deny` in settings | Client-enforced, can't be ignored |
| "Always run prettier after edits" | `hooks` in settings | Mechanical enforcement via hook |
| "Use 2-space indent" | CLAUDE.md or rule | Guidance, not enforcement |
| "Don't modify .env" | `permissions.deny` + hook | Deny blocks Edit tool; hook blocks Bash access |
| Model selection for project | `model` in settings | Enforced consistently |
| API keys, build env | `env` in settings | Applied to every session |

## Common Misconfigurations

| Problem | Symptom | Fix |
| ------- | ------- | --- |
| Allow rule expecting to override deny | Tool still blocked | Deny always wins — remove the deny or restructure |
| Permission in CLAUDE.md instead of settings | Claude ignores under pressure | Move to `permissions.deny` |
| `sandbox.enabled` without `denyRead` for secrets | Agent reads credentials via Bash | Add `sandbox.filesystem.denyRead` paths |
| Settings in `.claude/settings.json` that should be local | Committed secrets or personal prefs | Use `.claude/settings.local.json` |
| `bypassPermissions` in shared project settings | Entire team skips safety checks | Use only in isolated/container environments |
| Array setting in one scope expecting to replace another | Both scopes' values combine | Arrays merge — add counteracting deny rules instead |
