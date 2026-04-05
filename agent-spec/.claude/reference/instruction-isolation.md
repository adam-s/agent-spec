# Instruction Isolation and Context Leaking

## The Problem

When agent-spec launches sub-agents in sandboxes, they must behave as if they only have the Level 2 instructions (.claude/ config). Any leaked context from Level 0 (the orchestrator) or the host machine distorts the experiment — the agent might succeed because of leaked hints, not because the instructions are good.

## What Sub-agents See

A sub-agent launched via `invoke.py` runs in `/tmp/claude/agent-spec-{uuid}/` with:

| Source | What loads | Why |
|--------|-----------|-----|
| **Config (.claude/)** | CLAUDE.md, rules/ | Injected via cordyceps — this IS the experiment |
| **Prompt** | prompt.md content | Passed via `claude -p "..."` |
| **Workspace** | Cloned repo at buggy commit | Created by setup.sh |
| **User-level config** | `~/.claude/settings.json`, `~/.claude/rules/` | Inherited from host — potential leak |
| **User-level memory** | Nothing for this sandbox path | Memory is keyed to project path, so `~/.claude/projects/-tmp-claude-agent-spec-{uuid}/memory/` is empty |

## What Does NOT Leak

- **Project memory** — keyed to project directory path. The sandbox path is unique per run, so no project memory exists for it. See [claude-directory-reference.md](claude-directory-reference.md) line on Configuration Scopes.
- **Orchestrator instructions** — agent-spec's `.claude/` is in a different directory. Sub-agents run with `--dangerously-skip-permissions` and a flat prompt, not in the orchestrator's project context.
- **Other sandboxes** — each sandbox is an isolated directory. Parallel runs cannot see each other.
- **Git history of agent-spec** — the workspace contains only the target repo's history, not agent-spec's.

## What CAN Leak

- **User-level settings** (`~/.claude/settings.json`) — API keys, permission mode, custom hooks. These apply to all Claude invocations regardless of CWD. Mitigated: sub-agents use `--dangerously-skip-permissions` which bypasses permission hooks.
- **User-level rules** (`~/.claude/rules/`) — if the user has global rules, they apply everywhere. Mitigation: keep user-level rules minimal and non-domain-specific.
- **User-level CLAUDE.md** (`~/.claude/CLAUDE.md`) — loads for every session. If this contains debugging advice, it could help sub-agents beyond what the Level 2 config provides. Mitigation: don't put debugging instructions in user-level CLAUDE.md.
- **Agent memory** — agents with `memory: user` (in AGENT.md frontmatter) persist memory to `~/.claude/agent-memory/<name>/`. Our sub-agents don't use this — they're launched via `claude -p`, not as named agents with memory config.
- **Model knowledge** — Claude may have seen the repo/bug in training data. Mitigation: use post-cutoff bugs only.

## How We Mitigate

| Risk | Mitigation | Where documented |
|------|-----------|-----------------|
| Level 0 instructions leak to Level 1 | Separate directories; cordyceps swaps .claude/ | [recursive-training.md](iteration/recursive-training.md) |
| Model memorized the fix | Post-cutoff bugs only (after May 2025) | [../../../evals/bug-squashing/benchmark.md] |
| User-level config affects results | Minimal user-level rules; no debugging advice in ~/.claude/CLAUDE.md | This doc |
| Memory accumulates across runs | Sandbox paths are unique; no project memory persists | Claude memory scoping (path-keyed) |
| Config tested is not config deployed | Config snapshot saved per run in `results/{run_id}/config-snapshot/` | [eval-definition.md](eval-definition.md) |
| Prompt contains fix hints | Real issue text, no synthetic rewrites | CLAUDE.md (real source material rule) |

## Why Not Give Sub-agents Memory?

Sub-agents are **disposable by design**. Each run should be independent — that's how we get statistical signal about whether the *instructions* work, not whether the agent accumulated useful state.

If a sub-agent needs knowledge to succeed, that knowledge belongs in one of:
1. **CLAUDE.md** — always-loaded instructions (tested, generalized)
2. **rules/** — conditional rules that load for specific file patterns
3. **reference/** — on-demand docs the agent can look up
4. **The prompt** — including reviewer hints for multi-agent debugging

These are all part of the Level 2 config and travel with it. Memory is ephemeral and machine-specific — it can't be tested, versioned, or shared.

## Agent Memory (for non-eval use)

Named agents defined in `.claude/agents/` CAN have persistent memory via the `memory:` frontmatter field. This is useful for long-lived agents (reviewers, monitors) but not for eval sub-agents. See [claude-directory-reference.md](claude-directory-reference.md) for the `memory: user | project | local | none` options.
