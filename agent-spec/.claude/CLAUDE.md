# agent-spec

**Tests must terminate on deterministic, verifiable conditions — never on subjective judgment.** `verify.sh` outputs `RESULT: PASS` or `RESULT: FAIL`. The agent does not decide if it is done. The test decides. If you cannot write a deterministic verification, you do not have a test.

## What This Is

agent-spec is a test harness for evaluating agent behavior. It assembles disposable workspaces, runs agents in them, and measures the results — pass/fail, token cost, tool calls, time.

A workspace can be built from anything: copying an existing project, assembling seed files into an empty directory, or any combination. The workspace is disposable — created for one run, destroyed after.

Three testing layers, each adding signal:

1. **Output testing** — Did the agent produce correct results? Workspace → run → verify → pass/fail.
2. **Config testing** — Is the `.claude/` directory well-designed? Score against the component decision tree (@.claude/reference/decision-tree.md).
3. **Behavior testing** — Did the agent make good decisions? Analyze event traces for tool choices, rule adherence, token efficiency.

The primary metric is **cost-to-correctness** — not just pass/fail, but how many tokens it took to get there.

The product is agent-spec itself: its skills, scripts, rules, and reference docs. Eval results are ephemeral. The only artifacts worth committing are generalized improvements to agent-spec.

## Recursive Architecture

agent-spec operates at three nested levels. Understanding which level you're at — and which level a fix belongs to — is the core discipline.

- **Level 0 (Orchestrator):** Human + agent-spec. Launches agents, scores, diagnoses, fixes instructions.
- **Level 1 (Sub-agents):** Disposable Claude instances in workspaces. Their code is throwaway — their *behavior* is the signal.
- **Level 2 (The Product):** The `.claude/` directory. Must be self-sufficient — an agent reading it should never need to know agent-spec exists.

**Guards:**
- Each level writes only to its designated paths
- Every fix belongs to exactly one level — state "This is a Level N fix because ___" before applying
- Level 2 must never reference agent-spec

See @.claude/reference/recursive-training.md for full detail, guards, and convergence criteria.

## Exploratory Project

This is early-stage. No backwards compatibility. When we improve something, we update or delete everything that uses the old version. Old code, stale references, and orphaned patterns are actively harmful — they mislead future agents and waste tokens. If a change makes something obsolete, removing it is part of the change.

## How to Operate

Use existing skills and scripts — do not reimplement. See @.claude/reference/operational-workflow.md for the full inventory.

Before launching any eval or parallel run, confirm with the user. See @.claude/rules/resource-safety.md.

Key skills: `/run-eval`, `/iterate`, `/report`, `/stop`, `/new-eval`

## Key Concepts

- **Workspaces** — disposable directories in `/tmp/` where agents run. Built from source repos, seed files, or assembled from parts.
- **Ports** 3100-3110 allocated per run; use `__PORT__` in prompts
- **Cordyceps** — modify the workspace before the agent sees it (delete files, inject code, swap `.claude/`)
- **EVAL.md** — defines an eval with YAML frontmatter + markdown prompt. See @.claude/reference/eval-definition.md
- **Configs** — `.claude/` directory variants. Independent of evals — the same config can be tested across multiple challenges.
- **Baseline** — stored result from a known-good run. Future runs compare against it.

## Git

The git repository root is the **parent directory** (`agent-spec/`), not the working directory (`agent-spec/agent-spec/`). All git commands must target the parent.

## How `.claude/` Works

- **`rules/`** — Always loaded. Keep lean.
- **`skills/`** — Metadata loaded; body on invocation.
- **`reference/`** — Never auto-loaded. Looked up on demand.
- **`hooks/`** — Shell commands triggered by tool events.
