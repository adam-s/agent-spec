# agent-spec

**Tests must terminate on deterministic, verifiable conditions — never on subjective judgment.** `verify.sh` outputs `RESULT: PASS` or `RESULT: FAIL`. The agent does not decide if it is done. The test decides. If you cannot write a deterministic verification, you do not have a test.

## What This Is

The product is `agent-spec/.claude/` — the orchestrator instructions that make an agent capable of setting up and running ANY experiment a developer describes. A developer says what they want to test, and the orchestrator figures out how to build the workspaces, run the agents, and report the results. Scripts are utilities that the orchestrator uses. Evals are ephemeral test output. The `.claude/` instructions are the product.

A developer might say: "Compare 6 different .claude/ instruction styles against 3 coding tasks and see which one uses the fewest tokens." The orchestrator should be able to take that, understand the experiment, assemble the workspaces, run the matrix, and report the results — without the developer writing YAML, bash, or config files.

Three testing layers, each adding signal:

1. **Output testing** — Did the agent produce correct results? Workspace → run → verify → pass/fail.
2. **Config testing** — Is the `.claude/` directory well-designed? Score against the component decision tree (@.claude/reference/components/decision-tree.md).
3. **Behavior testing** — Did the agent make good decisions? Analyze event traces for tool choices, rule adherence, token efficiency.

The primary metric is **tokens-to-correctness** — not just pass/fail, but how many tokens it took to get there. Token counts are model-independent and comparable across pricing changes. Cost is logged but tokens are the headline.

## Recursive Architecture

agent-spec operates at three nested levels. Understanding which level you're at — and which level a fix belongs to — is the core discipline.

- **Level 0 (Orchestrator):** Human + agent-spec. Launches agents, scores, diagnoses, fixes instructions.
- **Level 1 (Sub-agents):** Disposable Claude instances in workspaces. Their code is throwaway — their *behavior* is the signal.
- **Level 2 (The Product):** The `.claude/` directory. Must be self-sufficient — an agent reading it should never need to know agent-spec exists.

**Guards:**
- Each level writes only to its designated paths
- Every fix belongs to exactly one level — state "This is a Level N fix because ___" before applying
- Level 2 must never reference agent-spec

See @.claude/reference/iteration/recursive-training.md for full detail, guards, and convergence criteria.

## Self-Improvement Loop

Evals exist to test these instructions, not as deliverables. When an experiment fails — bad observability, wrong assumptions, broken output — the failure is signal about the `.claude/` instructions, not about the eval.

The cycle:
1. Attempt an experiment
2. When something goes wrong, STOP running agents
3. Diagnose the failure. Check infrastructure first (setup.sh, verify.sh, fix.diff, dependencies) — broken scaffolding looks like instruction failures but wastes iteration cycles. Then determine: is this an instruction gap, a model capability limit, or an eval defect?
4. Fix at the right level — instruction gap → fix the instruction. Model limit → escalation or hints. Eval defect → fix the eval.
5. Delete the failed eval artifacts and start fresh — don't patch around failures
6. Attempt again

**Generalization guard:** Every instruction improvement must be generalized — never specific to a particular bug, library, or error type. If a finding names the domain, it's overfit. Validate improvements against held-out cases that the improvement process has never seen. See @.claude/reference/iteration/generalization.md.

This is Level 0 self-improvement. The `/iterate` skill improves Level 2 (target `.claude/` directories). This cycle improves Level 0 (the orchestrator's own instructions).

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
