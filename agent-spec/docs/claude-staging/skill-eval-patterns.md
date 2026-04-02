# Skill Evaluation Patterns (from agentskills.io)

Patterns from the Agent Skills open standard that apply to agent-spec. Source: https://agentskills.io/skill-creation/evaluating-skills and related pages.

## Patterns to Adopt

### 1. With/Without Comparison

Every experiment should run the task TWICE: with the `.claude/` config and without (or with a minimal baseline). This answers: "Does this config actually help, or would the agent succeed anyway?"

The "A-baseline" config (1-line CLAUDE.md: "A coding project.") IS the without-skill run. If the agent passes with A-baseline at the same cost as a 60-line config, the config isn't adding value — it's adding token cost.

**How this maps to agent-spec:**
- Always include A-baseline in config comparisons
- The delta between A-baseline and the tested config IS the measured value of the instructions
- A config that costs more tokens than A-baseline with the same pass rate is actively harmful

### 2. Assertions (Richer Verification)

agentskills.io uses individual assertions per test case, not just binary pass/fail:

```json
{
  "assertions": [
    "The output includes a bar chart image file",
    "The chart shows exactly 3 months",
    "Both axes are labeled"
  ]
}
```

Each assertion produces PASS/FAIL + evidence ("Found chart.png (45KB) in outputs directory").

**What this means for agent-spec:**

Today verify.sh produces one binary result. Adding assertions gives multi-dimensional scoring:

```yaml
# target assertions (proposed)
assertions:
  # Functional correctness (Layer 1)
  - "test.py outputs 5/5 tests passed"
  - "report.py uses only standard library imports"
  - "output includes Total Revenue line with dollar format"

  # Behavioral quality (Layer 3 — checkable from event JSONL)
  - "agent read test.py before writing report.py"
  - "agent read data/sales.csv before writing report.py"
  - "agent did not attempt to overwrite test.py"
  - "agent ran tests after writing code"
  - "total tool calls under 15"
```

The Layer 3 assertions are the breakthrough — they score the PROCESS, not just the output. They're verifiable from the event trace without running additional tests.

### 3. Grading with Evidence

Don't just record PASS/FAIL — record WHY:

```json
{
  "assertion": "agent read test.py before writing report.py",
  "passed": true,
  "evidence": "Event trace shows Read(test.py) at turn 2, Write(report.py) at turn 4"
}
```

Evidence makes diagnosis faster. When something fails, you see exactly what happened instead of re-reading the full trace.

### 4. Iteration Directory Structure

Each iteration gets its own directory with results:

```
targets/<name>/
  iterations/
    iteration-1/
      config-A/
        result.json       # tokens, cost, turns, pass/fail
        assertions.json   # per-assertion PASS/FAIL with evidence
        events.jsonl      # raw event trace
      config-B/
        ...
      benchmark.json      # aggregated comparison
    iteration-2/
      ...
```

This preserves history — you can compare iteration 1 vs 3 to see if changes helped or hurt.

### 5. Train/Validation Splits

When optimizing `.claude/` instructions, don't tune against ALL targets. Hold some back:

- **Train set (~60%):** The targets you use to identify failures and guide improvements
- **Validation set (~40%):** Targets you only use to check whether improvements generalize

If a `.claude/` change improves csv-reporter but breaks sqlite-window-queries, the instructions overfit. The validation set catches this.

**How this applies:**
- With 3 targets, hold 1 back as validation
- With 6+ targets, use a proper 60/40 split
- Never use validation target failures to guide instruction changes

### 6. Blind Comparison for Subjective Quality

For screenshot/visual references, present two outputs to an LLM judge without revealing which config produced them. The judge scores holistic quality on its own rubric.

This solves the "does the dashboard match the YouTube player?" problem:
- Screenshot both outputs
- Present them to the judge with the reference image
- Judge scores without knowing which is config A vs config B
- Removes bias about which "should" be better

### 7. Benchmark Aggregation

After grading, compute summary statistics per config:

```json
{
  "with_config": {
    "pass_rate": { "mean": 0.83, "stddev": 0.06 },
    "tokens": { "mean": 3800, "stddev": 400 },
    "cost": { "mean": 0.18, "stddev": 0.04 }
  },
  "without_config": {
    "pass_rate": { "mean": 0.33, "stddev": 0.10 },
    "tokens": { "mean": 2100, "stddev": 300 },
    "cost": { "mean": 0.09, "stddev": 0.02 }
  },
  "delta": {
    "pass_rate": 0.50,
    "tokens": 1700,
    "cost": 0.09
  }
}
```

The delta tells you what the config costs (more tokens) and what it buys (higher pass rate). A config that adds $0.09 but improves pass rate by 50 points is worth it. One that doubles cost for 2 points isn't.

## Patterns We Already Have That They Don't

| agent-spec has | agentskills.io doesn't |
|---|---|
| Cordyceps — rewrite anything in the sandbox | Can only modify the skill, not the environment |
| Multi-target comparison | Tests one skill at a time |
| Cost-to-correctness as primary metric | Tracks tokens but doesn't treat cost as THE signal |
| Recursive Level 0/1/2 architecture | No separation between harness and product |
| Reference types (screenshot, API, exit code) | Only test-file references |

## Skill Design Best Practices (applicable to .claude/ design)

From agentskills.io best practices, directly applicable to writing `.claude/` configs:

1. **Add what the agent lacks, omit what it knows.** Don't explain what a CSV is. DO explain your specific column names and data format.

2. **Explain the why.** "Do X because Y tends to cause Z" works better than "ALWAYS do X, NEVER do Y." Agents follow instructions more reliably when they understand the purpose.

3. **Provide defaults, not menus.** "Use pdfplumber. For scanned PDFs, use pytesseract instead." Not "you can use pypdf, pdfplumber, PyMuPDF, or pdf2image."

4. **Gotchas sections are the highest-value content.** Concrete corrections to mistakes the agent WILL make: "The users table uses soft deletes — queries must include WHERE deleted_at IS NULL."

5. **Favor procedures over declarations.** Teach HOW to approach a class of problems, not WHAT to produce for a specific instance.

6. **Progressive disclosure.** SKILL.md under 500 lines / 5000 tokens. Move detail to references/ with clear "load this when X" triggers.

7. **Match specificity to fragility.** Give freedom when multiple approaches work. Be prescriptive when operations are fragile or a specific sequence must be followed.

8. **When traces show wasted work, instructions are too vague.** The agent trying several approaches before finding one that works = ambiguous instructions. The agent following instructions that don't apply = over-broad instructions.

## Open Questions

- Where do assertions live? In verify.sh? In a separate assertions.yaml? In target.yaml?
- How do we check Layer 3 assertions against event JSONL? A script that parses events and checks tool call order?
- Should blind comparison use the reviewer-agent pattern from intercept2, or a simpler LLM judge?
- How do iteration directories interact with the existing `/tmp/agent-spec/{run_id}/` structure?
