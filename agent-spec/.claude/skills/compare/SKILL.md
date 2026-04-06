---
name: compare
description: Compare two eval runs and report what changed. Reads both runs' events, transcripts, and produced artifacts. Writes a short markdown summary classifying differences as regression, improvement, or neutral.
argument-hint: <run-a-id-or-baseline-name> <run-b-id>
context: fork
agent: Explore
---

# /compare — Judge two runs by reading their evidence

You are comparing two runs of the same eval. Read the evidence from both and write a short markdown summary of what changed.

## Arguments — read this first, do not deviate

You receive a single `$ARGUMENTS` string from the caller. Split it on whitespace into two tokens. The first token is **Run A** (the reference run — an 8-char run id, OR a baseline name like `valuation-model_with-skill`). The second token is **Run B** (the current run — an 8-char run id). Do not look anywhere else for the run ids. Do not infer them from filesystem state. The caller put both in `$ARGUMENTS` on purpose.

**Hard rules about argument order:**

1. The first token in `$ARGUMENTS` is always Run A. The second token is always Run B. Do **not** reorder them by timestamp, by which one PASSes, by directory mtime, or by any other heuristic. The caller chose the order on purpose; respect it.
2. The verdict direction is always "A → B" — i.e. "starting from A, did B get better, worse, or stay neutral?" If B is older than A, that is the caller's choice and you still report "A → B".
3. REGRESSION means **B is worse than A**. IMPROVEMENT means **B is better than A**. Never invert.

**Fail-loud check before doing anything else:**

After splitting `$ARGUMENTS`, if either Run A or Run B is empty, stop immediately. Do not guess. Do not list candidate runs. Do not ask the caller to clarify. Output exactly:

```markdown
## /compare — argument error
Expected exactly two arguments: `<run-A> <run-B>`.
Received: run-A=<run-A-value-or-empty> run-B=<run-B-value-or-empty>
```

…filling in the values you parsed (or `<empty>` if missing), and return. The parent agent will re-invoke you with correct arguments.

If Run A is a baseline name (not an 8-char hex id), read `evals/<eval>/results/baselines/<name>` (a one-line pointer file containing a run id) and use that run id as Run A. The verdict direction is still "A → B".

## What to read

For each run, the evidence lives in `evals/<eval>/results/<run-id>/`:

- `events.jsonl` — harness lifecycle events (agent_started, token_update, score, verification_output, etc.)
- `stream.jsonl` — the agent's turn-by-turn tool calls and assistant messages (this is the transcript)
- `produced/` — the files the agent wrote in the sandbox
- `config-snapshot/` — the `.claude/` directory the agent ran with
- `output.json` — the final result blob from the Claude run
- `stderr.log` — agent stderr

You don't need to read everything. Read what's relevant to detecting differences. For most comparisons, start with `events.jsonl` for the score and metrics, then look at `produced/` to see what the agent built, then dip into `stream.jsonl` only if you need to understand *how* the agent worked.

## Find the runs

Run ids are 8-char hex strings. They live in either:

- `evals/<eval>/results/<run-id>/` — archived per-eval (preferred)
- `/tmp/agent-spec/<run-id>/` — live, before archiving

Look in both. If the eval name isn't obvious from the arguments, find the run dir under `evals/*/results/` and the parent's parent is the eval name.

## What to compare

Walk through the differences and classify each one:

- **REGRESSION** — substance got worse. Examples: agent stopped using a convention from the skill (lost formulas, lost specific formatting), agent took a longer/circuitous tool path to reach the same result, agent skipped a step that was working before, the produced artifact lost a structural property, a rule was violated that wasn't violated before.
- **IMPROVEMENT** — substance got better. Examples: agent found a more direct path, fewer tool calls to reach PASS, output gained a property (better error handling, more correctness), behavior flag cleared.
- **NEUTRAL** — within noise. Examples: cell positions shifted, function names different, ±20% token count drift, slightly different phrasing in assistant messages.

A regression is **not just PASS→FAIL**. PASS→FAIL is the obvious case. The harder case is "still passes verify.sh but the agent's approach silently changed." Look for that.

If `config-snapshot/` is byte-identical between A and B (no skill or instruction changed), you cannot diff your way to the answer. Read `stream.jsonl` in both runs, find the tool calls and decisions that differ, and explain the behavioral change in those terms. The config diff is a shortcut for the easy case; behavior analysis is the only path for the hard case.

A regression is also **not just metric drift**. Token counts vary run-to-run by 10-20% from temperature alone. Don't call a 15% token increase a regression. Call it neutral unless something substantive changed. When you've already identified a substantive regression, drift that is downstream of that change must be classified `[NEUTRAL]`, never `[REGRESSION]`. A `[NEUTRAL]` drift bullet is fine; double-counting drift as a second regression is not.

## Output format

Write a short markdown summary. Be specific. Cite evidence from the files (file:line where possible).

The header must use this exact shape — A on the left, B on the right, arrow pointing from A to B. Do not swap them, do not change the arrow.

```markdown
## Compare A (`<run-A-value>`) → B (`<run-B-value>`)

**Verdict:** REGRESSION | IMPROVEMENT | NEUTRAL | MIXED

### What changed
- [REGRESSION] Agent stopped using Excel formulas — produced/dcf.xlsx has 0 cells with `=`-formulas (run A had 52). Evidence: stream.jsonl shows the agent wrote literal numeric values instead of `=SUM(...)`.
- [NEUTRAL] Token count went from 19,846 to 21,103 (+6%). Within run-to-run noise.

### Verdict explanation
One sentence on why the verdict above is what it is. If MIXED, name the dominant signal.
```

If both runs PASS and there are no substantive differences, write a one-line summary:

```markdown
## Compare A (`<run-A-value>`) → B (`<run-B-value>`)
**Verdict:** NEUTRAL — both PASS, no substantive differences detected.
```

## What you must NOT do

- Do not run any tool other than reading files. You are read-only.
- Do not edit any files. Your output is the markdown summary returned to the parent agent.
- Do not declare a regression based on metrics alone. Substance evidence is required.
- Do not write anything to disk. The parent agent prints your output.
- Do not be verbose. The developer reads this in 30 seconds. Two paragraphs max for typical comparisons; longer only if there are many specific differences worth listing.
