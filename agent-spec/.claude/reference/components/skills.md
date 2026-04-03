# Skills Reference

Skills are reusable instruction packages that load on demand, not every session. Each skill is a directory with a `SKILL.md` entrypoint. Commands (`.claude/commands/`) are the same mechanism — skills supersede them with additional features.

## Loading Behavior

Skills have a two-tier loading model that minimizes token cost:

| What loads | When | Token impact |
| ---------- | ---- | ------------ |
| Name + description (max 250 chars) | Always in context | ~1% of context window budget across all skills |
| Full SKILL.md body | On invocation only | Temporary — only while skill is active |

**Implication:** Description quality matters — it's Claude's only signal for deciding when to auto-invoke. Front-load the key use case. Descriptions beyond 250 chars are truncated.

## Invocation Control

| Frontmatter | User invokes | Claude invokes | Description in context |
| ----------- | ------------ | -------------- | --------------------- |
| (default) | Yes | Yes | Yes |
| `disable-model-invocation: true` | Yes | No | No |
| `user-invocable: false` | No | Yes | Yes |

**Diagnosis:** If a skill has side effects (deploy, send message), it should have `disable-model-invocation: true`. If it's background knowledge users shouldn't trigger directly, use `user-invocable: false`.

## Frontmatter Fields

| Field | What it does |
| ----- | ------------ |
| `name` | Display name and `/slash-command`. Lowercase, hyphens, max 64 chars. |
| `description` | When to use. Claude matches against this. Max 250 chars effective. |
| `argument-hint` | Autocomplete hint (e.g., `[issue-number]`). |
| `disable-model-invocation` | `true` = user-only invocation. |
| `user-invocable` | `false` = Claude-only invocation. |
| `allowed-tools` | Tools Claude can use without approval when skill is active. |
| `model` | Model override while skill is active. |
| `effort` | `low`, `medium`, `high`, `max` (Opus 4.6 only). |
| `context` | `fork` = run in isolated subagent context. |
| `agent` | Subagent type when `context: fork` (default: `general-purpose`). |
| `hooks` | Lifecycle hooks scoped to this skill. |
| `paths` | Glob patterns for auto-activation when working with matching files. |
| `shell` | `bash` (default) or `powershell`. |

## String Substitutions

| Variable | Expands to |
| -------- | ---------- |
| `$ARGUMENTS` | All arguments passed to the skill |
| `$ARGUMENTS[N]` or `$N` | Nth argument (0-based) |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Directory containing the SKILL.md |

If `$ARGUMENTS` is absent from content, arguments are appended as `ARGUMENTS: <value>`.

## Dynamic Context Injection

`` !`command` `` syntax runs shell commands before content is sent to Claude. Output replaces the placeholder. This is preprocessing — Claude only sees the result.

```markdown
## Current state
- Branch: !`git branch --show-current`
- Changed files: !`git diff --name-only`
```

## Directory Structure

```
my-skill/
├── SKILL.md           # Entrypoint (required, keep under 500 lines)
├── references/        # Detailed docs loaded on demand
├── examples/          # Example outputs
└── scripts/           # Scripts Claude can execute
```

Reference supporting files from SKILL.md so Claude knows when to load them.

## Scopes

| Priority | Location | Scope |
| -------- | -------- | ----- |
| 1 | Enterprise managed settings | All users |
| 2 | `~/.claude/skills/` | All your projects |
| 3 | `.claude/skills/` | This project |
| 4 | Plugin `skills/` | Where plugin enabled |

Same-name: higher priority wins. Plugin skills use `plugin-name:skill-name` namespace.

Skills in `--add-dir` directories are discovered and live-reloaded (unlike most `.claude/` config).

## Skills vs Subagents

| Approach | System prompt | Task | Context |
| -------- | ------------- | ---- | ------- |
| Skill with `context: fork` | From agent type | SKILL.md content | Isolated subagent |
| Subagent with `skills` field | Subagent's markdown body | Claude's delegation message | Isolated subagent |

Skills with `context: fork` need explicit task instructions — guidelines alone without a task produce empty output from the subagent.

## Two Types of Skill Content

**Reference content** — conventions, patterns, domain knowledge. Runs inline, no `context: fork`. Claude applies it alongside conversation context.

**Task content** — step-by-step procedures with side effects. Usually `disable-model-invocation: true` and often `context: fork`. User triggers explicitly.

## Common Misconfigurations

| Problem | Symptom | Fix |
| ------- | ------- | --- |
| Skill triggers when unwanted | Claude invokes on loosely matching prompts | Narrow description or add `disable-model-invocation: true` |
| Skill never triggers | Claude doesn't know it exists | Check description keywords match how users ask |
| Description too long | Truncated, Claude misses key use case | Front-load purpose in first 250 chars |
| Too many skills | Descriptions consume context budget | Trim unused skills; budget is 1% of context window (8K chars fallback) |
| `context: fork` with only guidelines | Subagent returns empty/useless output | Add explicit task instructions, not just conventions |
| Procedure in CLAUDE.md | Loaded every session, wastes tokens | Move to skill — loads only on invocation |
| Skill that should be a hook | Claude might not invoke it | If mechanical and same answer every time, use a hook |
| Large reference in SKILL.md | Bloats context when invoked | Move to `references/` subdirectory, load on demand |

## Relationship to Other Components

- **Skills vs rules:** Rules load every session (or on path match). Skills load on invocation only. Use rules for constraints, skills for procedures.
- **Skills vs hooks:** Hooks are mechanical (deterministic, zero tokens). Skills require Claude's judgment to invoke. If the answer is always the same, use a hook.
- **Skills vs agents:** Skills are instructions. Agents are execution environments. A skill with `context: fork` runs inside an agent. An agent with `skills` preloads skill content.
- **Skills vs reference:** Both load on demand. Skills are actionable (procedures, workflows). Reference is passive (documentation Claude reads when needed).
