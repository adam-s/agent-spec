# Component Design

Guide for designing and diagnosing `.claude/` directories. Use the [decision tree](decision-tree.md) to determine which component is correct. Use the component references for deep detail on each.

## Documents

| Document | What it answers |
| -------- | --------------- |
| [decision-tree.md](decision-tree.md) | Which component should this go in? (deterministic rubric with scoring rules) |
| [hooks.md](hooks.md) | How do I configure mechanical enforcement? (events, types, I/O, patterns) |
| [rules.md](rules.md) | How do I structure guidance? (CLAUDE.md, rules/, loading, sizing) |
| [permissions.md](permissions.md) | How do I control access? (deny/allow/ask, rule syntax, precedence) |
| [settings.md](settings.md) | Where does configuration live? (scopes, merge behavior, key settings) |
| [skills.md](skills.md) | How do I create on-demand procedures? (frontmatter, invocation, context) |
| [agents.md](agents.md) | How do I compose components into isolated workers? (the composition layer) |

## Core Principle: Push Decisions Down the Stack

If it can be enforced mechanically, don't rely on Claude remembering. The further down this list, the more you depend on Claude's judgment — and the more likely it breaks under token pressure, compaction, or model variation.

| Level | Component | Enforcement | Token cost | Reliability |
| ----- | --------- | ----------- | ---------- | ----------- |
| 1 | Hook / Permission | Client-enforced | Zero | Guaranteed |
| 2 | CLAUDE.md / Rule | Guidance | Permanent | High but not guaranteed |
| 3 | Skill | Guidance | On-demand | Depends on invocation |
| 4 | Agent | Client-enforced (tools) + guidance (prompt) | Isolated | High for tool restrictions, variable for prompt |
| 5 | Reference | None | On-demand | Depends on Claude looking it up |

## Token Budget

Every token loaded into context competes with the agent's working memory. Minimize permanent token cost.

| Component | Loading | Budget rule |
| --------- | ------- | ----------- |
| CLAUDE.md | Every session, permanent | Under 200 lines. Split into rules when growing. |
| rules/ | Session start (unconditional) or path match (on-demand) | One concern per file. Use `paths:` when possible. |
| skills/ | Description always (~250 chars); body on invocation | Total descriptions: 1% of context window. |
| hooks | External process | Zero. Always prefer when mechanical. |
| permissions | Settings config | Zero. Always prefer for access control. |
| agents/ | On spawn, isolated window | No impact on parent context. |
| reference/ | On demand | Zero until needed. Use for anything >50 lines of detail. |

## Two Kinds of Enforcement

Understanding this distinction is the key to correct component placement:

**Client-enforced** — Claude Code runs it regardless of what Claude decides. Claude cannot override, forget, or reinterpret it. Hooks, permissions, tool restrictions on agents, and sandbox rules are all client-enforced.

**Guidance** — Claude reads it and tries to follow it. Under token pressure, after compaction, or with model variation, adherence may drop. CLAUDE.md, rules, skill instructions, and agent system prompts are guidance.

**The diagnostic question:** If Claude forgetting this causes a concrete problem (files corrupted, tests not run, dangerous command executed), it must be client-enforced. If Claude forgetting is merely suboptimal (wrong style, missed convention), guidance is acceptable.

## How to Diagnose a `.claude/` Directory

1. **Run the decision tree** ([decision-tree.md](decision-tree.md)) against each instruction, rule, and hook. Flag misplacements using the scoring rules (M1-M8, G1-G6, P1-P4, R1-R3, A1-A5, C1-C4).

2. **Check token budget.** Is CLAUDE.md over 200 lines? Are unconditional rules loading content that only applies to specific files? Are large reference docs embedded in rules or skills?

3. **Check enforcement level.** Is anything in CLAUDE.md or rules that should be client-enforced? "Never do X" → should be a hook or permission deny, not prose.

4. **Check composition.** Are agents using the components available to them? Missing `tools:` restrictions, missing `hooks:` for validation, missing `skills:` for preloaded knowledge?

5. **Check for noise.** Duplicate instructions across files? Conflicting guidance? Obsolete rules for removed features?
