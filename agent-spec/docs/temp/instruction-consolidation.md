# Consolidating instructions: rules vs skills vs reference

## The premise

Rules in `.claude/rules/` are always loaded into context. Every conversation pays the token cost whether the rule is relevant or not. Skill bodies (`.claude/skills/<name>/SKILL.md`) load lazily — only when the skill is invoked. If a rule only matters when a specific skill runs, moving it into that skill's body is a strict win:

- The token cost shifts from "every conversation" to "conversations that use the skill"
- The rule lives next to the action it governs — easier to maintain
- The agent is less likely to forget the rule because it's loaded right when it's relevant

This only works if the rule is genuinely scoped to one skill. A rule that applies broadly (every output, every process) belongs in `rules/`.

## The current state

```
rules/
├── language.md          (AI communication standards)
├── observability.md     (run output, reporting, liveness, debug)
├── resource-safety.md   (agent launch, process mgmt, sandbox hygiene)
└── eval-workflow.md     (baselines, prove-the-eval-works)

skills/
├── handoff/
├── iterate/
├── new-eval/
├── report/
├── run-eval/
└── stop/

reference/
├── operational-workflow.md  (script inventory, workflow patterns)
├── eval-definition.md       (eval structure spec)
├── components/, iteration/  (architecture docs)
└── ...
```

## Walking each rule

### `language.md` — STAY IN RULES

Applies to every output the agent produces — comments, commits, chat responses, descriptions. Not tied to any skill. Genuinely cross-cutting. ~10 lines, cheap to keep always-loaded.

### `observability.md` — SPLIT

Two distinct concerns mixed together:

**Eval-output rules (move to `/run-eval`)**
- "Every run must print a summary line"
- "Token counts are input + output only — never include cache reads"
- "Never pipe agent output through filters that lose data"
- "After launching a background process, verify it's producing output within 30 seconds"
- "When running multiple sequential runs, each run must print its result before the next starts"

These only apply when the agent is *running an eval*. Move into `/run-eval/SKILL.md` or `/iterate/SKILL.md`.

**Reporting integrity rules (move to `/report`)**
- "Aggregates hide failures. Every report that includes a pass rate must also list each individual failure."
- "Reports must support temporal isolation"

These only apply when the agent is producing a report. Move into `/report/SKILL.md`.

**Liveness commands and reporting commands → reference**
- `ps aux | grep claude`, `ls -lt /tmp/agent-spec/`
- `report.py --score`, `report.py --tokens`, etc.

These are already in `reference/operational-workflow.md`. The duplication in the rule should go.

**Output convention (stdout/stderr/JSONL) → reference**
- "stdout is structured data, stderr is human display"
- "invoke.py emits JSONL on stdout"

This is architectural reference, not a runtime rule. Move to `reference/log-protocol.md` (already exists).

### `resource-safety.md` — SPLIT

**Agent-launch rules (move to `/run-eval` and `/iterate`)**
- "Before Launching Agents — confirm with the user"
- "Use run_in_background"
- "Parallel runs default to --instances 1"
- "Sequential Over Parallel"

These only apply when invoking skills that launch sub-agents. Move to those skills.

**Process and port lifecycle (stay in rules OR move to `/stop`)**
- "Process & Port Management" — track on spawn, prune on start, etc.
- "Shutdown Protocol" — SIGTERM → wait → SIGKILL

This is genuinely cross-cutting because *any* command that spawns a process needs to clean up. But — most of the agent's process spawning happens via `/run-eval`, `/iterate`, `/stop`. Could move to those skills with a one-line stub in rules pointing at them.

**verify.sh writing guidance (move to `reference/eval-definition.md`)**
- "Any verify.sh that starts a server MUST..."

This is instructions for *writing* verify.sh, not runtime behavior. Belongs in the reference doc that defines eval structure. Already half-documented there.

**Sandbox hygiene (move to `reference/eval-definition.md` or `/stop`)**
- "Sandboxes trigger Spotlight indexing on macOS"
- "Always remove sandboxes on exit"

Half is cleanup behavior (`/stop`), half is sandbox-creation behavior (`reference`).

### `eval-workflow.md` — MOVE ENTIRELY TO SKILLS

**"Save baselines after every run" → `/run-eval` and `/iterate`**

Only matters when the agent just ran an eval. The skill body is the perfect place — the agent has just finished doing what the skill taught and is about to write a result message. Embed the baseline-save instruction right there.

**"A new skill eval is not done until it catches a regression" → `/new-eval`**

Only matters when the agent is building a new skill eval. The `/new-eval` skill body is exactly where this belongs — it's the build instructions. The current rule reads like a postcondition; in `/new-eval` it becomes part of the recipe.

This was actually the lesson from the recent xlsx work: the rule was there but the agent didn't reliably apply it because rules describe constraints, not procedures. Moving it into the skill body turns it into a step.

## Proposed end state

```
rules/                              (always loaded — keep lean)
├── language.md                     (universal)
└── process-safety.md               (one-line: "before launching processes,
                                     read /run-eval, /iterate, /stop SKILLs")

skills/
├── run-eval/SKILL.md               (+ launch confirm, + summary line,
│                                     + token rules, + save baseline,
│                                     + run_in_background, + sequential default)
├── iterate/SKILL.md                (+ launch confirm, + parallel rules,
│                                     + save baseline)
├── new-eval/SKILL.md               (+ prove-the-eval-works cycle)
├── report/SKILL.md                 (+ no-aggregate-without-failures,
│                                     + temporal isolation)
├── stop/SKILL.md                   (+ process tree shutdown protocol,
│                                     + sandbox cleanup)
└── handoff/

reference/
├── operational-workflow.md         (script inventory — unchanged)
├── eval-definition.md              (+ verify.sh writing guidance,
│                                     + sandbox creation rules)
├── log-protocol.md                 (+ stdout/stderr convention)
└── ...
```

## Tradeoffs

**Wins:**
- Smaller always-loaded context. Every conversation that doesn't run an eval saves ~80 lines of rules.
- Rules colocated with the procedure they govern. Easier to keep in sync when the skill changes.
- Procedures-as-steps land better than rules-as-constraints (the xlsx lesson).

**Risks:**
- A rule moved into a skill only fires if the skill is invoked. If the agent does the action *without* invoking the skill (e.g. runs `python3 scripts/run_eval.py` directly instead of `/run-eval`), the rule isn't loaded. This is the main thing to watch.
- Mitigation: skills should be the only path to those actions. If we're worried about direct script invocation, the rules `process-safety.md` stub can say "any agent-launching action requires reading /run-eval first."
- Some rules genuinely apply to multiple skills (e.g. "save baselines" applies to both `/run-eval` and `/iterate`). Duplicating across skills is fine — it's a one-line reminder, not 80 lines of context.

**The baseline-save lesson:**
Putting "save baselines" in a rule didn't reliably work. Putting it in `/run-eval`'s skill body, where the agent is mid-flow and about to report, is more likely to be followed. This is the strongest argument for the consolidation.

## Next step

If this analysis tracks, the work is:
1. Move the listed sections out of `rules/` into the right `SKILL.md` files
2. Strip duplication between `rules/observability.md` and `reference/operational-workflow.md`
3. Add a one-line stub in `rules/` if a cross-cutting reminder is needed
4. Test with a fresh execution chat — does it still save baselines, still confirm before launching, etc.

The test is: a clean chat reads only `CLAUDE.md` + `rules/language.md` + (whatever the user asked for). Does it still do the right thing when it eventually invokes `/run-eval`?
