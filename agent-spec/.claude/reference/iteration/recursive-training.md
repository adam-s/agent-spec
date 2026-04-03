# Recursive Training Architecture

## The Pattern

When agent-spec trains a project, it operates at multiple nested levels. The product of training is not code — it is instructions that make agents produce correct code autonomously.

Sometimes those instructions include skills — structured procedures that themselves guide autonomous agent behavior. This creates recursion: the trainer trains instructions that train agents.

This is the "russian doll" or "inception" pattern. Each level is a complete system that functions independently, but during iteration they are nested inside each other. Understanding which level you are operating at — and which level a fix belongs to — is the single most important discipline in this architecture.

## Levels

### Level 0: Orchestrator

- **Who:** Human + agent-spec running `/iterate`
- **Does:** Launches sub-agents, monitors, scores, diagnoses, fixes instructions
- **Writes to:** `agent-spec/.claude/` (meta-improvements to the iteration process), `target/.claude/` (trainee instruction improvements)
- **Never writes to:** Sandboxes — that is Level 1's space

### Level 1: Sub-agents (disposable)

- **Who:** Claude instances running inside `/tmp/claude/agent-spec-{uuid}/` sandboxes
- **Does:** Follows the trainee's `.claude/` instructions to build or modify code
- **Writes to:** Their own sandbox ONLY
- **Never writes to:** Real repos, `agent-spec/`, other sandboxes
- **Key insight:** Their code is throwaway. Their *behavior* is the signal. What they do (and fail to do) reveals gaps in the Level 2 instructions.

### Level 2: The Product

- **What:** The `.claude/` directory (instructions, rules, skills) inside the target project
- **Does:** Nothing during iteration — it is passive text read by Level 1 agents
- **Used by:** Future agents working on the target project WITHOUT agent-spec present
- **Key insight:** This must be self-sufficient. An agent reading these instructions should never need to know that agent-spec exists.

## Guards

Four guards prevent the levels from collapsing into each other. Without these, a common failure is fixing the wrong level — improving the trainee when the harness was broken, or improving the harness when the trainee instructions were unclear.

### Guard 1: Filesystem Scope

Each level can only write to its designated paths:

| Level | Can write to | Cannot write to |
| ----- | ------------ | --------------- |
| 0 (orchestrator) | `agent-spec/.claude/`, `target/.claude/`, `results/` | Sandbox `/tmp` dirs |
| 1 (sub-agents) | Their own `/tmp/claude/agent-spec-{uuid}/` | Real repos, other sandboxes |
| 2 (the product) | N/A — it is instructions, not a running process | N/A |

**Enforcement:** Sub-agents run with CWD inside the sandbox. They never receive real repo paths in their prompts. The sandbox contains no symlinks or references back to the source.

### Guard 2: Identity Confusion Prevention

Every fix discovered during iteration belongs to exactly one level. Before applying ANY fix, state: "This is a Level N fix because ___."

| Signal | Level | Destination |
| ------ | ----- | ----------- |
| Agent didn't follow instructions | 2 | `target/.claude/` |
| Monitoring missed a failure pattern | 0 | `agent-spec/.claude/skills/iterate/` |
| Agent couldn't find a file in the sandbox | 2 | `target/.claude/` (naming/path issue) |
| Sandbox setup was wrong (missing deps, bad injection) | 0 | `agent-spec/scripts/` (infrastructure) |
| The iteration loop needs a new step | 0 | `agent-spec/.claude/skills/iterate/` |
| Agent produced correct code but wrong visual style | 2 | `target/.claude/` (missing design guidance) |

If the orchestrator cannot clearly assign a level, it asks the human. Guessing leads to cascading misdiagnosis.

### Guard 3: Branch Isolation

| What | Branch | Why |
| ---- | ------ | --- |
| Trainer meta-improvements (`agent-spec/.claude/`) | main | These improve the harness for ALL future targets |
| New scripts, target configs, wireframes | Feature branch | Experimental, target-specific |
| Trainee improvements (`target/.claude/`) | Feature branch in trainee repo | Experimental until convergence |

### Guard 4: Recursion Depth Limit

Level 2 (the product) must NEVER invoke agent-spec or create sandboxes. It operates within its own project's tools — test runners, linters, build systems — and knows nothing about the harness.

**Enforcement:** `grep -r "agent-spec" target/.claude/` must return nothing. If a Level 1 agent attempts to create nested sandboxes or reference agent-spec paths, that is a Level 2 instruction bug — the trainee instructions are leaking harness concepts.

## Fix Classification

The most common mistake is applying a fix at the wrong level. Two heuristics:

1. **"Would this fix help a different target?"** If yes → Level 0 (trainer). If no → Level 2 (trainee).
2. **"Is the agent doing the wrong thing, or is the harness measuring the wrong thing?"** Wrong behavior → Level 2. Wrong measurement → Level 0.

## Convergence

The iteration loop converges when fresh Level 1 agents (clean session, no hints, no prior context) using only the Level 2 instructions:

1. Pass all functional tests
2. Meet all qualitative criteria (visual fidelity, code style, etc.)
3. Stay within token budget
4. Require zero human intervention

At convergence, Level 2 is self-sufficient. agent-spec is no longer needed for that target.

## Example: hono-websocket-counter

This is a concrete instance of the pattern, included for illustration. The architecture applies to any target.

- **Level 0:** agent-spec `/iterate` skill launches 3 parallel sub-agents, each given a different wireframe screenshot (e.g., YouTube player, Hacker News, GitHub issues) as a visual design target for the counter app's UI.
- **Level 1:** Three Claude instances in separate `/tmp` sandboxes, each reading `hono-websocket-counter/.claude/` and building `server.ts` to match their wireframe while passing `test.js`.
- **Level 2:** A skill inside `hono-websocket-counter/.claude/skills/build/` that teaches agents how to do test-driven development of Hono/Bun WebSocket apps with visual design targets. This skill has zero knowledge of agent-spec, sandboxes, or the iteration process.

The 3 wireframes are not 3 different tasks — they are 3 stress tests of the same instructions. If the Level 2 instructions only work for one wireframe style, they are overfitting. Convergence means any wireframe produces a passing, visually faithful result.
