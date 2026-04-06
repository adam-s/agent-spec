# Ways to improve the concept of a "test"

Brainstorm dump. We can change anything — these are ideas worth exploring.

## Make the test more like science

- Run baseline N times (3, 5, 10) and measure variance. One PASS isn't a baseline — it's a sample.
- Track "reliability" — if 4/5 runs pass with the skill, the eval is noisier than if 5/5 pass.
- Compare distributions, not point values. A regression isn't PASS→FAIL — it's "the rate dropped from 100% to 20%."

## Test what changed, not what could change

- When the skill is edited, run the eval automatically — git hook or watcher. The developer never has to remember.
- Diff the skill before/after and tell the agent what changed in the prompt. "These three lines were added — does the output reflect them?"
- Cache the baseline alongside the skill version. New skill version = new baseline required.

## Make the test self-improving

- When a regression is caught, ask Claude to look at the agent's output and explain *why* the skill change broke it. Save that as a test rationale.
- When a regression *isn't* caught after a deliberate break, the test failed. Ask Claude to propose what to check that would have caught it, and add it to verify.sh automatically.
- Track which skill edits historically caused regressions and which didn't — over time you learn which parts of the skill are load-bearing.

## Use multiple agents as the verifier

- Have a second Claude (a "judge") evaluate the output instead of regex/openpyxl checks. "Does this spreadsheet follow the conventions described in this skill?" Give it the skill and the output, ask for a verdict with reasoning.
- A judge generalizes — verify.sh has to be rewritten when the challenge changes; a judge just reads the new skill.
- Compare judge verdicts to deterministic verify.sh — when they diverge, there's signal.

## Test the test

- Mutation testing for skills: programmatically delete random sections, see which mutations the eval catches. If any mutation passes silently, the eval has blind spots.
- Run the eval on multiple models (haiku, sonnet, opus). A test that catches a regression on sonnet but not opus tells you about the model, not the skill.

## Cordyceps the workspace

- Inject a known-broken `dcf.xlsx` before the agent starts and ask it to fix it. Tests reading + repair, not just generation.
- Inject a half-finished spreadsheet — does the agent extend it correctly per the skill's conventions?
- Inject a malformed input file — does the agent handle it the way the skill says?

## Make the prompts adversarial

- Generate prompts dynamically. Same task, different wording, different business domain. If the eval only catches regressions on one specific phrasing, it's brittle.
- Add distractors — irrelevant requirements that shouldn't change the skill-specific output. If the agent gets distracted, that's a skill failure too.

## Measure cost of the skill, not just correctness

- Skill present: 10,699 tokens. Skill absent: 5,030 tokens. The skill costs ~5,000 tokens per run. Is it worth it? That's a real metric.
- Track "value per token" — how much correctness does each chunk of skill content buy?
- Use this to drive skill compression — strip sections that don't move the metric.

## Test composability

- What happens when two skills are loaded together? Does one override the other?
- What happens with a deliberately contradictory skill loaded alongside? Does the agent notice?

## Differential testing

- Run the same task with skill A and skill B. Compare outputs structurally. Tell the developer what changed.
- Useful for "I refactored the skill — same output, fewer tokens?"

## The biggest one

**Make verify.sh a Claude judge instead of a Python script.** verify.sh is the brittle part of every eval. A judge agent reading the skill and the output is more like how a human would test it — and it scales to any skill without writing new openpyxl code.
