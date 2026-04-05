# agent-spec as a Toolkit

Exploratory document. What does a developer see when they clone this repo?

## The pitch

Toolkit for agent development. Three tools for three jobs.

## The tools

### 1. Test your agent — regression guard

You're developing a `.claude/` directory. You add a new rule, tweak the CLAUDE.md, add a skill. Did you make it better or worse?

The developer defines evals — coding challenges with deterministic pass/fail. Each eval captures a behavior the agent should get right. As the `.claude/` evolves, the eval suite runs against a baseline snapshot. You see immediately: did the change improve things, regress, or have no effect.

The workflow:
- You're editing your `.claude/` config
- You add a feature — say a new rule about how the agent should handle error messages
- You add an eval that tests that specific behavior
- You run the full suite — the new eval passes, and nothing else regressed
- The baseline updates

This is the test harness use case. The developer's `.claude/` is the code under test. Evals are the test suite. The baseline is the last known good state.

**Example:** A developer building a `.claude/` for a monorepo wants to add a rule that the agent should always run the linter before committing. They add an eval where the prompt asks the agent to fix a bug, and `verify.sh` checks that the linter ran. They run the full suite — the new eval passes, and the existing evals (does it write tests? does it follow the style guide?) still pass too.

### 2. Improve your agent — iterative training

You have an existing `.claude/` directory — maybe it's mature like [intercept's](../../submodules/intercept/.claude/), with rules, skills, hooks, and a multi-step discovery protocol. You want to make it better, but the instructions are complex enough that manual tuning is guesswork.

The tool runs agents against challenges, scores the results, diagnoses instruction gaps, fixes the instructions, and runs again. It repeats until the config passes or hits a depth limit. You don't manually read logs and tweak CLAUDE.md — the system identifies what's wrong and proposes fixes, then validates that each fix actually worked.

The workflow:
- Point the tool at your `.claude/` and a set of challenges
- It runs, fails, diagnoses, fixes, runs again
- Each iteration produces a report: what changed, why, did it help
- You review the accumulated changes and decide what to keep

**Example:** The intercept `.claude/` has a five-step discovery protocol (pre-flight, gather, scan, classify, build) with dozens of rules. An agent using these instructions might waste too many tool calls in GATHER, or skip the elimination table in CLASSIFY. The iteration loop would identify these gaps from actual agent behavior and tighten the instructions — then verify the tighter instructions don't break the steps that were already working.

### 3. Compare approaches — A/B evaluation

You have a question: which instruction strategy is actually better? Not by reading them and guessing — by measuring.

Same challenges, different `.claude/` configs, compare results. The headline metric is tokens-to-correctness: not just did it pass, but how much work did it take.

The workflow:
- Define two or more configs (different CLAUDE.md strategies, different rule sets, different models)
- Run them against the same challenges
- Get back a comparison: pass rate, token count, cost, behavior differences

**Example:** The [token-efficiency eval](../../agent-spec/evals/token-efficiency/) tests whether popular token-saving CLAUDE.md strategies (drona23, caveman) actually reduce token usage compared to a minimal baseline. Same two coding tasks, three different instruction sets, measure the difference. The answer isn't what the README claims — it's what the numbers show.

## What these have in common

All three tools share the same engine:

- A challenge is a workspace + prompt + `verify.sh` that outputs PASS or FAIL
- Every run happens in an isolated sandbox — no cross-contamination
- The agent doesn't decide if it's done — the test decides
- Results come back as tokens, cost, pass/fail, and behavior traces

The developer doesn't configure the engine. They describe what they want to test, and the tools handle sandboxing, scoring, comparison, and reporting.

## What the developer builds

The product is always a portable `.claude/` directory. The three tools are three ways to develop and validate it:

1. **Regression guard** — make sure changes don't break what works
2. **Iterative training** — systematically improve complex instructions
3. **A/B evaluation** — measure which approach is actually better

A developer might use all three in sequence: compare approaches to pick a starting point, iterate to improve it, then use the regression suite to protect it as they continue developing.

## Open questions

- Is "toolkit" the right word, or is it "dev kit", "workbench", something else?
- Should the README lead with the three tools, or with what you can build?
- The current name `agent-spec` suggests a specification. If this is a toolkit, does the name still fit?
- Where do products like bug-squasher fit in the pitch? Are they examples, templates, or the main attraction?
- What are the skill names? The existing `/run-eval`, `/iterate`, `/new-eval` map roughly but not perfectly to these three use cases. The regression guard use case might need its own skill, or it might be a mode of `/run-eval` that compares against a baseline automatically.
- The comparison use case doesn't have a dedicated skill today — it's done by running `/run-eval` multiple times and then looking at the results. Should it be a single skill that takes multiple configs?
