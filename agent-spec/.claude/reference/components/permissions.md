# Permissions Reference

Permissions control what Claude Code can access and do. Unlike rules and CLAUDE.md (guidance Claude reads), permissions are enforced by the client — Claude cannot override them.

## Evaluation Order

**deny → ask → allow.** First matching rule wins. Deny always takes precedence, regardless of which settings scope defined it.

## Permission Modes

| Mode | Behavior |
| ---- | -------- |
| `default` | Prompts on first use of each tool |
| `acceptEdits` | Auto-accepts file edits (except protected dirs) |
| `plan` | Read-only — no modifications or commands |
| `auto` | AI classifier evaluates each tool call |
| `dontAsk` | Auto-denies unless pre-approved via allow rules |
| `bypassPermissions` | Skips prompts (except protected dirs: `.git`, `.claude`, `.vscode`, `.idea`, `.husky`) |

Set via `defaultMode` in settings, or per-subagent via `permissionMode` frontmatter.

## Rule Syntax

Format: `Tool` or `Tool(specifier)`

### Bash

- `Bash` or `Bash(*)` — all commands
- `Bash(npm run build)` — exact match
- `Bash(npm run *)` — glob with word boundary (space before `*`)
- `Bash(npm*)` — glob without word boundary
- `Bash(* --version)` — wildcard at start
- Shell operators (`&&`) are parsed — `Bash(safe-cmd *)` won't match `safe-cmd && evil-cmd`

### Read and Edit

Follow gitignore pattern spec:

| Pattern | Meaning |
| ------- | ------- |
| `//path` | Absolute from filesystem root |
| `~/path` | From home directory |
| `/path` | Relative to project root |
| `path` or `./path` | Relative to CWD |

- `*` matches within one directory, `**` matches recursively
- `Edit` rules apply to all file-editing tools
- `Read` rules best-effort apply to Grep, Glob, etc.
- **Neither blocks Bash subprocesses** — `Read(./.env)` deny won't stop `cat .env`

### Other tools

- `WebFetch(domain:example.com)` — domain-scoped
- `mcp__server__tool` — specific MCP tool
- `mcp__server` or `mcp__server__*` — all tools from an MCP server
- `Agent(name)` — specific subagent

## Settings Precedence

1. **Managed** (enterprise) — cannot be overridden
2. **CLI flags** (`--allowedTools`, `--disallowedTools`)
3. **Local project** (`.claude/settings.local.json`)
4. **Shared project** (`.claude/settings.json`)
5. **User** (`~/.claude/settings.json`)

If denied at any level, no other level can allow it.

## Permissions vs Hooks vs Rules

| Mechanism | Enforcement | Can block | Who decides |
| --------- | ----------- | --------- | ----------- |
| Permissions | Client-enforced | Yes — hard block | Settings config |
| Hooks | Client-enforced | Yes — exit 2 or deny | Shell script / LLM / HTTP |
| Rules / CLAUDE.md | Guidance only | No — Claude may ignore | Claude's judgment |

**Interaction:** PreToolUse hooks fire before permission checks. A hook `deny` blocks even in `bypassPermissions`. But a hook `allow` does NOT bypass deny rules — hooks can tighten, never loosen past permission rules.

## Permissions vs Sandboxing

- **Permissions** control which tools Claude Code uses (all tools)
- **Sandboxing** provides OS-level enforcement for Bash only (filesystem + network)
- Sandbox filesystem restrictions use Read/Edit deny rules
- Both are complementary — use together for defense-in-depth

## Common Misconfigurations

| Problem | Symptom | Fix |
| ------- | ------- | --- |
| Deny in CLAUDE.md instead of settings | Claude ignores under pressure | Move to `permissions.deny` in settings.json |
| `Read(./.env)` deny without sandbox | Agent uses `cat .env` via Bash | Enable sandbox or add `Bash(cat *.env*)` deny |
| Broad `Bash(*)` allow | No safety guardrails | Allow specific commands, deny dangerous ones |
| `Bash(curl *)` allow for URL restriction | Fragile — options, variables, redirects bypass it | Use `WebFetch(domain:...)` + deny Bash curl |
| Hook returning `allow` expecting to bypass deny | Deny rule still blocks | Hooks cannot loosen past permission rules |
| File protection in CLAUDE.md | Not enforced | Use `Edit` deny rule or PreToolUse hook |

## Auto Mode

AI classifier evaluates tool calls. Reads `autoMode` from user, local, and managed settings only (not shared project settings).

- `autoMode.environment` — prose describing trusted infrastructure (repos, buckets, domains)
- `autoMode.allow` / `autoMode.soft_deny` — **replaces** entire default list when set
- Precedence: soft_deny blocks → allow overrides → explicit user intent overrides both
- CLI: `claude auto-mode defaults`, `claude auto-mode config`, `claude auto-mode critique`
