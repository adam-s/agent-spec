# The Self-Reflective Agent Paradigm

> A working document. Synthesized from four specimens — [agent-spec/.claude](../../.claude/), [alphadidactic/.claude](../../../submodules/alphadidactic/.claude/), [intercept/.claude](../../../submodules/intercept/.claude/), and [testing-claude-agent](../../../../testing-claude-agent/) — that, in different domains and with different vocabularies, all converge on the same architecture.

## 1. Definition

A **self-reflective agent** is an agent whose `.claude/` instructions explicitly task it with observing, measuring, and improving its own behavior — or the behavior of agents it spawns — against deterministic verification, and which treats its own instruction set as the primary product of the work.

The paradigm has three constituent moves, repeated indefinitely:

- **Observe** — capture evidence of what the agent did. Events, transcripts, screenshots, audit tables, token counts, exit codes, JSON findings.
- **Verify** — collapse that evidence into a deterministic signal. `RESULT: PASS` / `RESULT: FAIL`. A score out of 28. A pass rate. A token delta. The agent does not decide if it is done — the test does.
- **Patch** — when the signal is bad, update *instructions*, not code, and rerun. The instruction must generalize beyond the specific failure that produced it.

What separates a self-reflective agent from "an agent with a long prompt" is that the loop above is *built into the instructions themselves*. The agent is not just doing work — it is producing evidence that its instructions are correct, and the instructions know how to use that evidence to improve.

## 2. The Four Specimens

Each specimen is nominally about something else. The giveaway — the place where the meta-purpose surfaces — is quoted.

### agent-spec

Nominally an orchestrator that runs evals against `.claude/` configurations and tunes them. Actually optimizing its *own* `.claude/` — the orchestrator instructions that make the agent capable of running any experiment a developer describes.

> "The product is `agent-spec/.claude/` — the orchestrator instructions that make an agent capable of setting up and running ANY experiment a developer describes. [...] Evals are ephemeral test output. The `.claude/` instructions are the product."
> — [.claude/CLAUDE.md](../../.claude/CLAUDE.md)

### alphadidactic

Nominally a quant-research agent that runs trading experiments. Actually building the instruction set that *produces* correct experiments. The experiments themselves are throwaway test harnesses.

> "We are building `.claude/` — an instruction set that creates experiments. We are NOT building experiments. [...] Experiments are test harnesses that expose gaps in the instruction set. Run → Review → Attack → Patch `.claude/` → Re-run same experiment."
> — [submodules/alphadidactic/.claude/CLAUDE.md](../../../submodules/alphadidactic/.claude/CLAUDE.md)

### intercept

Nominally an API-discovery and dashboard-building agent. The reflective layer is the `instruction-tuning` skill plus the reviewer-agent's `GENERALIZED=yes/no` field, which forces every patch to apply to *any* website rather than the specific site under discovery. Test branches are disposable; only `main` accumulates skills and rules.

> Discoveries flow from `memory/base-fixes-needed.md` on test branches into permanent skill/rule updates on `main`. Site-specific findings are filtered out. The reviewer's `GENERALIZED=yes` flag is the gate.

### testing-claude-agent

Nominally a coding-task benchmark. Actually a controlled experiment in which the *independent variable is the `.claude/` instruction set itself*. Six configs (A-baseline through F-drona23) run identical challenges, and tokens-to-correctness is the dependent variable. It is the only specimen that has empirically *measured* the paradigm rather than just practiced it.

> Findings: F-drona23 (61-line CLAUDE.md) averaged 12,053 total tokens. B-token-efficient (12-line summary of the same ideas) averaged 8,065. All six configs passed all challenges. Conclusion: long CLAUDE.md files cost more in input tokens than they save.

> Note on structure: testing-claude-agent does not have a `.claude/` directory. Its instructions live at root (`CLAUDE.md`) and in `configs/A-F/CLAUDE.md`. This is informative: the paradigm does not require the directory layout, only the discipline.

## 3. The Twelve Shared Patterns

Each pattern is included only because it appears in at least three of the four specimens. Each has a name, a one-line definition, evidence, and a "why it matters" line.

---

### Pattern 1 — Deterministic Verification

**Definition.** No subjective judgment of doneness. Every loop terminates on a signal a machine can read.

| System | Mechanism |
|---|---|
| agent-spec | `verify.sh` outputs literal `RESULT: PASS` or `RESULT: FAIL`. "The agent does not decide if it is done. The test decides." |
| alphadidactic | 8-step verification protocol with 1e-8 numerical tolerance; temporal audit table where every row must be `Causal=Y`; independent reimplementation in Check 6 (must not import from strategy code). |
| intercept | Elimination table is a mandatory gate before route code is written: every transport (Embedded JSON, JSON API, GraphQL, WebSocket, …) has a ✓/✗ with cited evidence. "ANY FAIL = fix before committing." |
| testing-claude-agent | `verify.sh` per challenge; pass/fail is exit code; no human in the loop. |

**Why it matters.** Subjective stop conditions are how iteration loops degenerate. The agent declares victory, the human nods, the bug ships. A deterministic signal removes the agent's ability to lie to itself or to you.

---

### Pattern 2 — Instructions Over Code

**Definition.** When something fails, the default fix is a generalized rule in `.claude/`, not a specific code patch.

| System | Evidence |
|---|---|
| agent-spec | "Prefer instructions over code fixes. When a problem is discovered, the default response should be adding or improving a rule or guideline — not writing specific code to handle the case." |
| alphadidactic | "Every iteration can and should change anything — instructions, utilities, infrastructure, shared code, agent definitions, hooks, skills. Nothing is sacred except the principle that the instructions must improve." |
| intercept | `instruction-tuning` skill exists explicitly so that discoveries flow back into permanent skill updates on `main`. |
| testing-claude-agent | The harness *measures* this principle. F-drona23's verbose instructions cost ~50% more tokens than B's terse summary on identical work. The principle is empirically constrained: more instructions are not free. |

**Why it matters.** A code patch fixes the case you've seen. A rule fixes every future instance of the pattern. But — see testing-claude-agent — instructions are not free either, so the rule has to earn its bytes.

---

### Pattern 3 — Generalization Guards

**Definition.** Every instruction patch must apply beyond the specific case that produced it. Patches that name a library, file, error, or symbol are overfit and rejected.

| System | Mechanism |
|---|---|
| agent-spec | "If a finding names the domain, it's overfit." Held-out validation against unseen cases. See [reference/iteration/generalization.md](../../.claude/reference/iteration/generalization.md). |
| alphadidactic | 5-step instruction audit before commit: grep for specific symbols/thresholds, contradiction check, duplication check, broken-reference check. |
| intercept | reviewer-agent emits `GENERALIZED=yes/no` on every finding. Only `yes` findings are kept. |
| testing-claude-agent | Implicit: configs are tested across multiple challenges, so any instruction that helps one challenge but hurts another washes out. |

**Why it matters.** Without this guard, the instruction set becomes a scar tissue of past failures, growing forever, helping less and less. Generalization is what keeps the instruction set bounded.

---

### Pattern 4 — Level / Branch Separation

**Definition.** Strict scoping of who writes what, where. The meta-system, the working agent, and the product are kept in separate filesystems / branches / contexts that cannot contaminate each other.

| System | Implementation |
|---|---|
| agent-spec | Three-level recursion (Orchestrator / Sub-agents / Product). "Each level writes only to its designated paths. Every fix belongs to exactly one level — state 'This is a Level N fix because ___' before applying. Level 2 must never reference agent-spec." |
| alphadidactic | Experiment agent runs in a worktree at `/tmp/claudodidact-worktrees/` *outside* the repo. It is structurally blind to `reference_experiments/` and `docs/`. Reviewer/adversary read full repo for forensic analysis but cannot write. |
| intercept | `main` branch is permanent (skills, rules); test branches are disposable. "Delete every test branch — nothing of lasting value is lost." |
| testing-claude-agent | Harness vs. configs vs. challenges. Each agent run sees only its own config plus challenge seed files — verified with `find $WORKTREE -type f`. No answer keys, no other configs. |

**Why it matters.** Level collapse — where the meta-system leaks into the product, or the product references the meta-system — is the failure mode that turns a self-reflective agent into a fragile script. Separation by construction (filesystem, branch, worktree) is more reliable than separation by prose.

---

### Pattern 5 — Bounded Sub-Agents With Explicit Budgets

**Definition.** Sub-agents have hard tool-call ceilings. The budget is both a safety rail and a measurement instrument.

| System | Budgets |
|---|---|
| agent-spec | reviewer agent: <40 tool calls, read-only |
| alphadidactic | experiment 200, reviewer 40, adversary 60 |
| intercept | discovery 150, dashboard 80, reviewer 40 |
| testing-claude-agent | Implicit: each agent gets one shot per challenge; cost is recorded |

**Why it matters.** Unbounded sub-agents are how you discover, three days later, that something has been spinning since Tuesday. A ceiling forces the agent to report what it did with what it had — which is exactly the data the reflective loop needs. Budgets-as-signal: hitting the ceiling is itself diagnostic information.

---

### Pattern 6 — Adversarial / Red-Team Review

**Definition.** A second agent whose job is to disbelieve the first. Read-only, separate context, structured output.

| System | Reviewer |
|---|---|
| agent-spec | `reviewer.md` agent — compares a bug-squashing run against the known-good fix.diff, classifies failure into a P0–P7 taxonomy, recommends generalized instruction improvements. |
| alphadidactic | Two reviewers. `research-reviewer-agent` (28-point rubric: 14 temporal, 8 accounting, 6 verification). `adversary-agent` (red-team: assume the experiment is wrong and attack it, with `CONFIRMED`/`PROBABLE`/`SUSPICIOUS` classifications). |
| intercept | `reviewer-agent.md` — 12-point code+UI rubric; emits `GENERALIZED=yes/no`. |
| testing-claude-agent | The benchmark IS the reviewer. Runs the same task across 6 configs and forces them to disagree on cost. |

**Why it matters.** The agent that built the thing is the worst possible judge of whether it's correct. A read-only second agent with a rubric and a smaller budget breaks the self-congratulation loop. The adversary variant goes further: it assumes failure as the prior.

---

### Pattern 7 — Tokens-to-Correctness as Primary Metric

**Definition.** Pass/fail is necessary but not sufficient. The headline number is *how many tokens it took to pass*. Cache reads are excluded — they inflate counts ~100× and make comparisons meaningless.

| System | Where it shows up |
|---|---|
| agent-spec | Codified in [rules/observability.md](../../.claude/rules/observability.md): "Tokens = input + output only; never include cache reads." Summary line per run: `✓ name: PASS (30s) 9,500tok`. |
| alphadidactic | Token cost of `.claude/` itself is tracked: `wc -c .claude/rules/*.md .claude/CLAUDE.md` — target ≤40KB. Sub-agents inherit all rules, so reduction is the only optimization. |
| intercept | Sub-agent budgets (150/80/40) are the tokens-to-correctness signal at the agent level. |
| testing-claude-agent | The whole benchmark is built around this metric. `report.py` aggregates input+output tokens by config. The empirical finding (F:12,053 vs B:8,065 on identical challenges) is the cleanest demonstration of the principle in any of the four specimens. |

**Why it matters.** Without a cost metric, a "better" instruction set is whichever one looks nicer in your editor. With one, you can prove that your beautiful 61-line CLAUDE.md is worse than a 12-line summary. Cache reads must be excluded because they reward repetition of context, not work — a metric that includes them rewards bloat.

---

### Pattern 8 — Structural Constraint Via Hooks, Not Prose

**Definition.** When prose is unreliable — when an agent will reliably violate "don't write outside the worktree" no matter how loudly you say it — encode the constraint as a `PreToolUse` / `SubagentStop` hook that the harness enforces.

| System | Hooks |
|---|---|
| agent-spec | `guard-agent-launch.sh` (PreToolUse reminder before spawning agents); `git-cwd-reminder.sh`; `post-launch-monitor.sh`; `cleanup-on-stop.sh` |
| alphadidactic | `create-worktree.sh` (isolation by construction — worktree lives outside the repo); `guard-worktree-writes.sh` (deny writes outside worktree); `guard-causal-flags.sh` (block hardcoded `causal = True/False` in verify code — H9 guard) |
| intercept | `guard-worktree-writes.sh`, `cleanup-on-stop.sh`, `track-pid.sh`, `create-worktree.sh` |
| testing-claude-agent | `cleanup.sh` and `run-agent.sh` enforce worktree-only writes and clean up orphans |

**Why it matters.** Prose instructions are aspirational. Hooks are real. The discipline is: every time you catch yourself writing "the agent must never X," ask whether X can be made impossible by a hook. The alphadidactic causal-flag hook is the perfect example — instead of repeatedly telling the agent "compute the causal flag, don't hardcode it," they wrote a hook that rejects the file if it contains a hardcoded boolean.

---

### Pattern 9 — Disposable Workspaces

**Definition.** Iterations happen in `/tmp/` worktrees that are destroyed on completion. Cleanup is part of the contract, not an aftercare step that gets skipped.

| System | Workspace policy |
|---|---|
| agent-spec | Sandboxes in `/tmp/claude/agent-spec-*`. `.metadata_never_index` to avoid Spotlight. Always removed on exit unless `--keep`. Tracked PIDs in `/tmp/agent-spec-pids.txt`. |
| alphadidactic | Worktrees at `/tmp/claudodidact-worktrees/`, branched from local HEAD, gitignored cache files copied in. Pruned by `stop` skill. |
| intercept | Discovery worktrees with `track-pid.sh`; cleanup via `cleanup-on-stop.sh`. |
| testing-claude-agent | Worktrees per agent run; `cleanup.sh` removes orphans before each eval. |

**Why it matters.** State that persists across iterations is state that can mislead. The hard rule "delete the failed eval artifacts and start fresh — don't patch around failures" only works if deletion is cheap and total. Workspaces have to be designed to be discarded.

---

### Pattern 10 — Recursion With Convergence Criteria

**Definition.** The reflective loop is a real loop with a measurable stop condition, not a vibes-based "we'll iterate until it feels right."

| System | Stop condition |
|---|---|
| agent-spec | `/iterate` skill has `--max-depth N` and a stop condition based on the deterministic verifier. |
| alphadidactic | Convergence target: 24/28 reviewer points on a *fresh* agent (not the one from earlier cycles), no extra hints beyond `.claude/` files, ≤5 cycles. |
| intercept | Sub-agent call budgets are the per-iteration ceiling; the orchestrator decides when discovery has converged based on elimination-table coverage. |
| testing-claude-agent | `iterate.sh` runs ≤10 iterations and reads `analysis.json.converged` flag from `analyze.py`. |

**Why it matters.** "Recursive self-improvement" without a stop condition is a way to set fire to compute. The convergence criterion is what makes the loop a *machine* rather than a vague intention. Note that all four use *different* criteria — the criterion is task-specific, but its existence is universal.

---

### Pattern 11 — Fail-Loud, No-Silent-Success

**Definition.** Every run produces visible, per-run output. Aggregates must list each individual failure. Silent success is treated as failure.

| System | Mechanism |
|---|---|
| agent-spec | [rules/observability.md](../../.claude/rules/observability.md): per-run summary line; "Aggregates hide failures. Every report that includes a pass rate must also list each individual failure." Verify output within 30s or investigate. |
| alphadidactic | "Silent failure is the default. Internal consistency masks external incorrectness." 99/100 positive backtests are bugs that produce beautiful equity curves. Every check produces explicit pass/fail with a numerical residual. |
| intercept | Sub-agents emit structured JSON findings; `guard-worktree-writes.sh` denies with explicit error reasons; checkpoint reports at budget exhaustion. |
| testing-claude-agent | Per-config token + pass/fail logged; `report.py` prints the full table, not just averages. |

**Why it matters.** A self-reflective agent runs many times. The feedback signal has to survive aggregation. The instinct is to print a percentage; the discipline is to print the specific run that failed, every time.

---

### Pattern 12 — Self-Sufficiency of the Product `.claude/`

**Definition.** The instructions an agent reads must be coherent without knowing the meta-system exists. The product is independent of the harness that produced it.

| System | How it's enforced |
|---|---|
| agent-spec | "Level 2 must never reference agent-spec." The trained `.claude/` is checked for orphaned references to the orchestrator before promotion. |
| alphadidactic | The experiment agent is structurally blind to `reference_experiments/`, `docs/`, the orchestrator, the reviewer rubric — it just reads `.claude/` and works. |
| intercept | Test-branch discoveries are domain-specific and stay on the branch. Only generalized findings are promoted to `main`'s skills/rules. |
| testing-claude-agent | Each config's worktree contains only that config's `CLAUDE.md` plus seed challenge files — verified by `find`. |

**Why it matters.** A product that requires its training harness to be useful is not a product; it's a tightly coupled subsystem. The whole point of the reflective loop is to produce instructions that can be lifted out, dropped into a new agent, and *just work*.

## 4. The Anatomy

The minimum viable layout of a self-reflective agent. Rows are components; columns are which specimen implements them and how.

| Component | agent-spec | alphadidactic | intercept | testing-claude-agent |
|---|---|---|---|---|
| **Identity statement** (CLAUDE.md tells the agent what it is *for*) | "The product is `agent-spec/.claude/`" | "We are building `.claude/`. We are NOT building experiments." | "Skills teach generalized principles; prompts teach domain tasks" | "Deterministic benchmarking for Claude Code" |
| **Always-loaded rules** | `language.md`, `eval-workflow.md`, `resource-safety.md`, `observability.md` | `temporal-correctness.md`, `prompt-compliance.md`, `accounting-correctness.md`, `database-safety.md`, `experiment-checks.md` | `iteration-loop.md`, `discovery.md`, `prompt-compliance.md`, `workflow.md`, `base-branch.md` | Per-config `CLAUDE.md` (1 to 61 lines) |
| **Structured skills** | `iterate`, `run-eval`, `compare`, `new-eval`, `report`, `stop`, `handoff` | `experiment-pipeline`, `instruction-tuning`, `stop` | `dashboard-builder`, `debug-logs`, `instruction-tuning`, `ci-check`, … | `scripts/iterate.sh`, `run-eval.sh`, `evolve.py` |
| **Builder sub-agent** | (the spawned eval agent itself) | `experiment-agent` (200 calls) | `discovery-agent` (150), `dashboard-agent` (80) | The agent under test |
| **Reviewer sub-agent** | `reviewer.md` (<40 calls, P0–P7 taxonomy) | `research-reviewer-agent` (40 calls, 28-point rubric) | `reviewer-agent` (40 calls, 12-point rubric) | `report.py` + `analyze.py` |
| **Adversary sub-agent** | — | `adversary-agent` (60 calls, red-team) | — | (cross-config comparison plays this role) |
| **Enforcement hooks** | `guard-agent-launch.sh`, `git-cwd-reminder.sh`, `post-launch-monitor.sh`, `cleanup-on-stop.sh` | `create-worktree.sh`, `guard-worktree-writes.sh`, `guard-causal-flags.sh`, `cleanup-on-stop.sh` | `guard-worktree-writes.sh`, `create-worktree.sh`, `track-pid.sh`, `cleanup-on-stop.sh` | `cleanup.sh`, `run-agent.sh` worktree enforcement |
| **On-demand reference** | `reference/components/`, `reference/iteration/`, etc. | `reference/pending-row-pattern.md`, `wall-clock-model.md`, `bug-catalog.md`, … | (in skills) | `docs/` |
| **Deterministic verifier** | `verify.sh` → `RESULT: PASS/FAIL` | 8-step verification with 1e-8 tolerance | Elimination table gate | `verify.sh` per challenge |
| **Scoring / aggregation** | `compare` skill (REGRESSION / IMPROVEMENT / NEUTRAL / MIXED) | 28-point rubric + adversary findings | 12-point rubric + `GENERALIZED` flag | `report.py` token+pass/fail table |
| **Iteration loop** | `/iterate` (OBSERVE → DIAGNOSE → APPLY → recurse) | `instruction-tuning` 9-step cycle | `instruction-tuning` skill | `iterate.sh` 10-iteration loop |
| **Convergence criterion** | `--max-depth` + verifier PASS | 24/28 fresh-agent score, ≤5 cycles | Elimination table coverage / call-budget | `analysis.json.converged` flag, ≤10 iters |
| **Cleanup protocol** | `/stop`, `cleanup.py`, PID registry | `stop` skill, 8-step shutdown | `cleanup-on-stop.sh`, `track-pid.sh` | `cleanup.sh` |
| **Memory of past runs** | `results/` + `compare` against baseline | Reference experiments + bug-catalog.md | `memory/base-fixes-needed.md` → `main` promotion | `results/TIMESTAMP/` + `evolve.py` reads history |

The table is the most useful single artifact in this document. To build a new self-reflective agent, copy the leftmost column as a checklist and fill in the right one for your domain.

## 5. Where the Specimens Diverge (Instructive Differences)

The differences are as informative as the commonalities — they show the dimensions along which the paradigm can vary.

- **agent-spec** is the only one that treats the meta-system as the explicit, named subject of the work. The other three discovered the paradigm in the course of doing something else; agent-spec started there.

- **alphadidactic** is the only one with hardware-grade failsafes (the `guard-causal-flags.sh` hook that rejects hardcoded boolean causal flags in verification code). It needs them because its failure mode is uniquely insidious: a wrong answer that looks like a beautiful equity curve. The instruction "compute, don't hardcode" was being violated reliably enough that prose was insufficient. The lesson generalizes: when prose has failed three times, write a hook.

- **intercept** is the only one whose product has end-users (UI dashboards), and so it is the only one with screenshot-as-verification. The reflective loop has to consume images because the failure mode is "the chart is wrong" rather than "the number is wrong."

- **testing-claude-agent** is the only one that runs the *comparative* experiment — it asks "which `.claude/` shape is best?" and answers empirically. It is also the only one without a `.claude/` directory of its own (its instructions live at root). This is the most important divergence: it suggests the paradigm does not require the directory layout, only the discipline. You can build a self-reflective agent without ever creating a folder named `.claude/`.

## 6. The Paradigm Stated as Design Rules

A builder's checklist. If your system fails any of these, you have an agent with a long prompt, not a self-reflective agent.

1. **Name the deterministic signal that ends your loop.** If you can't name it — if "until it looks right" is the answer — you don't have a self-reflective agent. You have an iteration suggestion.

2. **Make the agent's instructions the product.** If a successful run produces correct *output* but the instruction set didn't change, you ran a script. The instruction set is what gets refined; the output is the test signal.

3. **Default to instructions, not code.** When something fails, the first patch should be a generalized rule. Code patches are permitted only when the rule already exists and the code contradicts it.

4. **Generalize every patch.** If the patch names a library, file, error code, symbol, or domain word, it is overfit. Rewrite it as a domain-free principle, or reject it.

5. **Separate levels by construction, not by prose.** Use worktrees, branches, hooks, and filesystem scopes. "The agent should not write here" is a wish; `guard-worktree-writes.sh` is a fact.

6. **Bound every sub-agent.** A tool-call ceiling is mandatory. Hitting the ceiling is data, not failure.

7. **Run a reviewer that is read-only and structured.** A separate context with a rubric and a smaller budget. Bonus: an adversary that assumes failure as the prior.

8. **Track tokens-to-correctness, not just correctness.** Input + output only. Cache reads excluded. Print the cost of every run.

9. **Encode repeat violations as hooks.** Three failures of the same prose rule means write the hook.

10. **Discard workspaces after every iteration.** Cleanup is part of the contract. State that survives iterations is state that lies.

11. **Aggregates must list every individual failure.** A pass rate without a list of failures is a number, not a signal.

12. **The product `.claude/` must work without knowing the harness exists.** If lifting the instructions out and dropping them into a fresh agent breaks them, they're not a product, they're a coupling.

## 7. Open Questions

These are the places the synthesis breaks down or stops being confident.

- **Does the paradigm require recursion?** Three of the four specimens have a meta-system improving instructions for a sub-agent. Intercept is fuzzier — it has bounded sub-agents and a reviewer, but the "improvement" loop is the human plus the `instruction-tuning` skill. Is single-level self-observation (one agent observing itself, no meta) enough to count, or is the second level constitutive? Lean: the second level is a strong signal but not strictly required, as long as the deterministic signal is real.

- **Is tokens-to-correctness a defining metric or just a useful one?** All four track it, but only testing-claude-agent makes it the primary axis. It might be that *any* deterministic cost metric (wall time, calls, dollars) suffices, and tokens are just the most portable.

- **Where does the paradigm break?** Tasks where verification is inherently subjective (creative writing, design taste), tasks where the agent IS the user (chat assistants), and tasks where the cost of one iteration exceeds the cost of getting it right by hand. The paradigm assumes iteration is cheap and verification is mechanical. When either is false, it doesn't help.

- **Is alphadidactic's "blindness by construction" worth importing into the others?** The experiment agent literally cannot see `reference_experiments/` because the worktree is mounted outside the repo. agent-spec relies on prose Level 2 guards instead. The hook approach is stronger; the prose approach is more flexible. Unclear which generalizes.

- **What replaces the directory layout?** testing-claude-agent shows the paradigm survives without `.claude/`. What's the minimum? CLAUDE.md + verify.sh + a loop script seems to be enough. The `rules/skills/agents/hooks` taxonomy might be a Claude Code convenience rather than a paradigm requirement.

---

*Last updated 2026-04-06. This is a working document in `docs/temp/` — it captures a paradigm as I understand it now, not as final doctrine. Patterns survive only as long as a fourth specimen agrees with them.*
