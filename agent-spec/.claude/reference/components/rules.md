# Rules & CLAUDE.md Reference

Rules and CLAUDE.md are instructions Claude reads — guidance, not enforcement. Claude tries to follow them, but there is no guarantee, especially under token pressure, compaction, or conflicting instructions. For guaranteed behavior, use hooks or permissions.

## CLAUDE.md

Project instructions loaded at the start of every session. Lives at `./CLAUDE.md` or `./.claude/CLAUDE.md`. User-level at `~/.claude/CLAUDE.md`. Managed policy at OS-specific paths.

**Loading:**
- Walks up directory tree from CWD, loading all CLAUDE.md files found
- Subdirectory CLAUDE.md files load on demand when Claude reads files there
- Survives `/compact` — re-read from disk each time
- `@path/to/file` imports expand inline (max 5 hops, relative or absolute)
- HTML comments (`<!-- -->`) stripped before injection — use for human-only notes

**Sizing:** Target under 200 lines per file. Longer files still load in full but reduce adherence. When approaching 200 lines, split into rules.

**Priority order (highest to lowest):**
1. Managed policy (enterprise, cannot exclude)
2. Project (`.claude/CLAUDE.md` or `./CLAUDE.md`)
3. User (`~/.claude/CLAUDE.md`)

When instructions conflict, more specific scope wins.

## rules/

Topic-scoped instruction files in `.claude/rules/`. One topic per file. Discovered recursively including subdirectories and symlinks.

**Two loading modes:**

| Mode | Frontmatter | When loaded | Token impact |
| ---- | ----------- | ----------- | ------------ |
| Unconditional | No `paths:` field | Session start | Permanent — same as CLAUDE.md |
| Path-scoped | `paths:` with globs | When Claude reads a matching file | On demand — zero until triggered |

**`paths:` frontmatter** is the only configuration field:

```markdown
---
paths:
  - "src/api/**/*.ts"
  - "**/*.test.{ts,tsx}"
---
```

| Pattern | Matches |
| ------- | ------- |
| `**/*.ts` | All TypeScript files in any directory |
| `src/**/*` | All files under `src/` |
| `*.md` | Markdown files in project root only |
| `src/**/*.{ts,tsx}` | TypeScript and TSX under `src/` |

**Scopes:**
- Project: `.claude/rules/` (committed, shared with team)
- User: `~/.claude/rules/` (personal, all projects)
- User-level loads before project-level; project takes higher priority

## What goes where

| Content | Component | Why |
| ------- | --------- | --- |
| Build/test/lint commands | CLAUDE.md | Always relevant, every session |
| Project architecture, stack | CLAUDE.md | Core context for all work |
| File-type conventions (e.g., "API endpoints use Zod") | Path-scoped rule | Only needed when editing those files |
| Behavioral constraints ("never use default exports") | Unconditional rule | Always relevant but one-topic-per-file keeps CLAUDE.md lean |
| "Always run prettier after edits" | **Hook, not rule** | Mechanical — same answer every time |
| "Don't modify .env files" | **Hook, not rule** | Mechanical enforcement, not guidance |
| Large API reference | **reference/** | Too large for always-loaded context |
| Multi-step procedure | **Skill** | Loaded on demand, not every session |

## Common Misconfigurations

| Problem | Symptom | Fix |
| ------- | ------- | --- |
| CLAUDE.md over 200 lines | Reduced adherence, wasted tokens | Split into rules or reference docs |
| Mechanical enforcement in CLAUDE.md | Claude forgets under pressure | Move to hook |
| Unconditional rule that only applies to one file type | Loaded every session for no reason | Add `paths:` frontmatter |
| Conflicting instructions across files | Claude picks arbitrarily | Audit and deduplicate |
| Detailed reference material in a rule | Permanent token cost | Move to `reference/` |
| Instruction given only in conversation | Lost after compaction | Add to CLAUDE.md or rule |
| Monorepo loading irrelevant team's CLAUDE.md | Noise, wasted context | Use `claudeMdExcludes` in settings |

## Relationship to Other Components

- **Rules vs hooks:** Rules are guidance Claude reads. Hooks are mechanical enforcement Claude Code runs. If Claude forgetting causes a concrete problem, it should be a hook.
- **Rules vs skills:** Rules load every session (or on path match). Skills load only on invocation. Use skills for procedures, rules for constraints.
- **Rules vs reference:** Rules are short, always or conditionally loaded. Reference docs are large, loaded on demand. If it's over ~50 lines of detail, it's probably reference material.
- **`@` imports vs rules:** Imports expand inline into CLAUDE.md (always loaded). Path-scoped rules load conditionally. Prefer rules for file-type-specific content.
