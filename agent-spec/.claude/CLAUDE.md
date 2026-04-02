# agent-spec

**Tests must terminate on deterministic, verifiable conditions — never on subjective judgment.** `verify.sh` outputs `RESULT: PASS` or `RESULT: FAIL`. The agent does not decide if it is done. The test decides. If you cannot write a deterministic verification, you do not have a test.

## What This Is

agent-spec tests and improves `.claude/` directories. Given any project, it sandboxes it, runs agents against it, scores results, and uses that signal to iteratively improve the project's CLAUDE.md, rules, skills, hooks, and agents — until autonomous agents succeed without human intervention.

Three testing layers, each adding signal:

1. **Output testing** — Did the agent produce correct results? Sandbox → run → verify → pass/fail.
2. **Config testing** — Is the `.claude/` directory well-designed? Score against the component decision tree (@.claude/reference/decision-tree.md).
3. **Behavior testing** — Did the agent make good decisions? Analyze event traces for tool choices, rule adherence, token efficiency.

The product is agent-spec itself: its skills, scripts, rules, and reference docs. Target repos are test fixtures — they exist to exercise the harness, not as deliverables. Fixture results are ephemeral. The only artifacts worth committing are generalized improvements to agent-spec.

## Recursive Architecture

agent-spec operates at three nested levels. Understanding which level you're at — and which level a fix belongs to — is the core discipline.

- **Level 0 (Orchestrator):** Human + agent-spec. Launches agents, scores, diagnoses, fixes instructions. Writes to `agent-spec/.claude/` and `target/.claude/`.
- **Level 1 (Sub-agents):** Disposable Claude instances in sandboxes. Their code is throwaway — their *behavior* is the signal. Writes only to their own `/tmp/claude/agent-spec-{uuid}/`.
- **Level 2 (The Product):** The `.claude/` directory inside the target project. Must be self-sufficient — an agent reading it should never need to know agent-spec exists.

**Guards:**
- Each level writes only to its designated paths
- Every fix belongs to exactly one level — state "This is a Level N fix because ___" before applying
- Level 2 must never reference agent-spec (`grep -r "agent-spec" target/.claude/` must return nothing)

See @.claude/reference/recursive-training.md for full detail, guards, and convergence criteria.

## Exploratory Project

This is early-stage. No backwards compatibility. When we improve something, we update or delete everything that uses the old version. Old code, stale references, and orphaned patterns are actively harmful — they mislead future agents and waste tokens. If a change makes something obsolete, removing it is part of the change.

## How to Operate

Use existing skills and scripts — do not reimplement. See @.claude/reference/operational-workflow.md for the full inventory.

Before launching any eval or parallel run, confirm with the user. See @.claude/rules/resource-safety.md.

Key skills: `/run-eval`, `/iterate`, `/report`, `/stop`, `/new-target`

## Key Concepts

- **Sandboxes** live in `/tmp/claude/agent-spec-{uuid}/` — disposable copies, originals never modified
- **Ports** 3100-3110 allocated per run; use `__PORT__` in prompt.md
- **Cordyceps** — delete, inject, or swap any file in sandbox before the agent sees it
- **Component design** — see @.claude/reference/component-design.md for the diagnostic framework

## Git

The git repository root is the **parent directory** (`agent-spec/`), not the working directory (`agent-spec/agent-spec/`). All git commands must target the parent.

## How `.claude/` Works

- **`rules/`** — Always loaded. Keep lean.
- **`skills/`** — Metadata loaded; body on invocation.
- **`reference/`** — Never auto-loaded. Looked up on demand.
- **`hooks/`** — Shell commands triggered by tool events.
