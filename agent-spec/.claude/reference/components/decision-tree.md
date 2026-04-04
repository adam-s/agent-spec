# Component Decision Tree

Deterministic rubric for diagnosing whether a `.claude/` directory uses the right component for each concern. Start at the top, follow the first YES branch. Each leaf is a testable assertion.

## The Tree

```
0. Does this belong in the .claude/ product at all?
   │
   │  Test: Would this constraint still be correct if this .claude/ were
   │  dropped into a completely different repo and task?
   │
   ├── NO → It's environment-specific, not product-level.
   │   │    Put it in the eval prompt, cordyceps, workspace setup,
   │   │    or the orchestrator — not in the .claude/ directory.
   │   └── ENVIRONMENT (not a .claude/ component)
   │
   └── YES → Continue to question 1.

1. Is it mechanical — same answer every time, no judgment needed?
   │
   ├── YES → Is it blocking a dangerous action or enforcing a constraint?
   │   │
   │   ├── YES, and it should be client-enforced (cannot be ignored)
   │   │   └── PERMISSIONS (deny/allow/ask rule in settings.json)
   │   │
   │   └── YES, but needs custom logic (pattern matching, validation)
   │       └── HOOK (command type, PreToolUse with exit 2)
   │
   ├── YES → Is it a side effect that should happen after every matching action?
   │   │   (formatting, logging, notifications)
   │   └── HOOK (command type, PostToolUse or Notification)
   │
   ├── YES → Is it lifecycle management?
   │   │   (cleanup on exit, context injection on start, env reload on dir change)
   │   └── HOOK (SessionStart, Stop, CwdChanged, FileChanged, etc.)
   │
   └── NO — requires judgment or context
       │
       2. Does Claude need this information to do its job?
       │
       ├── YES → Must Claude always have it, every session?
       │   │
       │   ├── YES, and it's core identity / project-wide
       │   │   └── CLAUDE.md (under 200 lines)
       │   │
       │   ├── YES, but only for certain file types or paths
       │   │   └── RULE with paths: frontmatter
       │   │
       │   └── YES, it's a behavioral constraint or separable concern
       │       │   (always relevant, but not core identity)
       │       └── RULE without paths: (unconditional)
       │
       ├── SOMETIMES → Is it large or detailed?
       │   │
       │   ├── YES (>50 lines of reference material)
       │   │   └── REFERENCE doc (loaded on demand)
       │   │
       │   └── NO, it's a concise procedure or workflow
       │       └── SKILL
       │
       └── NO — Claude needs to DO something
           │
           3. Is it a repeatable multi-step procedure?
           │
           ├── YES → Does it need isolated context or tool restrictions?
           │   │
           │   ├── YES → SKILL with context: fork (runs in agent)
           │   │         or AGENT definition (if reused with specific config)
           │   │
           │   └── NO → SKILL (runs inline)
           │
           └── NO → Does it need its own context window?
               │
               ├── YES → AGENT
               └── NO → Instruction in RULE or CLAUDE.md
```

## Scoring Rules

Each rule below is a testable assertion. If the condition is true and the content is in the wrong component, it's a misplacement.

### Context-dependent → must NOT be in .claude/

| ID | Condition | Correct location | Common misplacement |
| -- | --------- | ---------------- | ------------------- |
| E1 | Constraint only applies during testing, not in production use | Eval prompt, cordyceps, or workspace setup | permissions.deny in settings.json |
| E2 | Restriction would break the product in a different repo or task | Environment (orchestrator-level) | Rule or CLAUDE.md |
| E3 | "Don't use tool X" but the tool is valuable in other contexts | Eval prompt or cordyceps (e.g., shallow clone) | permissions.deny |

### Mechanical → must be Hook or Permission

| ID | Condition | Correct component | Common misplacement |
| -- | --------- | ----------------- | ------------------- |
| M1 | "Always run X after editing files" | PostToolUse hook | CLAUDE.md |
| M2 | "Never modify file/path X" | permissions.deny + PreToolUse hook | CLAUDE.md or rule |
| M3 | "Block command pattern X" | permissions.deny or PreToolUse hook | CLAUDE.md |
| M4 | "Format code after edits" | PostToolUse hook | CLAUDE.md or rule |
| M5 | "Clean up on session end" | SessionEnd or Stop hook | CLAUDE.md |
| M6 | "Notify when waiting for input" | Notification hook | Not applicable |
| M7 | "Inject context after compaction" | SessionStart hook (compact matcher) | Lost and not recovered |
| M8 | "Verify tests pass before stopping" | Stop hook (prompt or agent type) | CLAUDE.md |

### Guidance → must be CLAUDE.md or Rule

| ID | Condition | Correct component | Common misplacement |
| -- | --------- | ----------------- | ------------------- |
| G1 | Build/test/lint commands | CLAUDE.md | Nowhere (agent guesses) |
| G2 | Project architecture, stack description | CLAUDE.md | rule (wastes a file) |
| G3 | File-type-specific conventions | Rule with `paths:` | CLAUDE.md (loaded every session) |
| G4 | Behavioral constraint or separable concern (e.g., "named exports only", escalation strategies) | Rule without `paths:` | CLAUDE.md (bloats it, tangles concerns) |
| G5 | Instruction that only applies to one subdirectory | Rule with `paths:` | Global rule or CLAUDE.md |
| G6 | Content over 200 lines in CLAUDE.md | Split into rules | Single bloated CLAUDE.md |

### Procedures → must be Skill

| ID | Condition | Correct component | Common misplacement |
| -- | --------- | ----------------- | ------------------- |
| P1 | Multi-step deploy/release workflow | Skill with `disable-model-invocation: true` | CLAUDE.md |
| P2 | Repeatable code generation pattern | Skill | CLAUDE.md or rule |
| P3 | Procedure with side effects | Skill with `disable-model-invocation: true` | Skill without (Claude auto-invokes) |
| P4 | Background knowledge, not a user action | Skill with `user-invocable: false` | Skill in `/` menu |

### Reference → must be reference/

| ID | Condition | Correct component | Common misplacement |
| -- | --------- | ----------------- | ------------------- |
| R1 | >50 lines of API docs, schema, or spec | reference/ doc | Rule or CLAUDE.md |
| R2 | Detailed domain knowledge | reference/ doc | Rule (permanent token cost) |
| R3 | Supporting material for a skill | Skill's references/ subdirectory | Inline in SKILL.md |

### Isolation → must be Agent

| ID | Condition | Correct component | Common misplacement |
| -- | --------- | ----------------- | ------------------- |
| A1 | Needs tool restrictions (read-only, no Bash) | Agent with `tools:` | Skill without restrictions |
| A2 | Produces verbose output (test runs, logs) | Agent (isolates context) | Main conversation |
| A3 | Needs different model than main session | Agent with `model:` | Skill (can't isolate model effectively) |
| A4 | Needs scoped MCP servers | Agent with `mcpServers:` | Main conversation MCP |
| A5 | Needs persistent cross-session memory | Agent with `memory:` | Auto memory in main context |

### Configuration → must be settings.json

| ID | Condition | Correct component | Common misplacement |
| -- | --------- | ----------------- | ------------------- |
| C1 | Tool allow/deny rules | `permissions` in settings.json | CLAUDE.md |
| C2 | Environment variables | `env` in settings.json | CLAUDE.md or shell profile |
| C3 | Model selection for project | `model` in settings.json | CLAUDE.md instruction |
| C4 | Hook definitions | `hooks` in settings.json | Standalone script with no wiring |

## Quick Reference

| Component | Loads | Token cost | Enforcement |
| --------- | ----- | ---------- | ----------- |
| Hook | Every matching event | Zero | Client-enforced |
| Permission | Every tool call | Zero | Client-enforced |
| CLAUDE.md | Every session | Permanent | Guidance only |
| Rule | Session start or path match | Permanent or on-demand | Guidance only |
| Skill | On invocation | Temporary | Guidance only |
| Agent | On spawn | Isolated window | Client-enforced (tools/permissions) |
| Reference | On demand | Temporary | None |
| settings.json | Every session | Zero | Client-enforced |
