# skill-xlsx Results

## Working as of 2026-04-06

The eval has one challenge — `valuation-model` — that demonstrably catches regressions when the xlsx skill is degraded or removed.

### What works

**Challenge: valuation-model**

The prompt asks for a 5-year DCF valuation for "TechCo Inc." with specific business inputs (revenue, growth, margin, tax rate, terminal growth, WACC). The prompt does not mention formulas, colors, formats, cell layout, or any implementation detail. The agent has to decide how to structure the spreadsheet — and the skill is what tells it.

**verify.sh checks two things the skill consistently produces and unguided agents do not:**

1. **Parens-negative number format** — at least 3 cells with format strings containing `;(` (e.g. `$#,##0;($#,##0);-`). The xlsx skill explicitly mandates this format. No model defaults to it.
2. **Blue font (RGB 0000FF)** — at least one cell with the specific blue. The skill mandates blue 0,0,255 for hardcoded inputs. Models default to no font color.

It also requires at least 5 formulas as a basic sanity check.

### Proven cycle

| Run | Config state | Result | Evidence |
|-----|-------------|--------|----------|
| `ef54badb` (baseline) | Skill present | PASS | 52 formulas, 55 parens-negative formats, 11 blue fonts |
| `a92bb114` (regression test) | Skill removed | FAIL | 0 formulas, 0 parens-negative, 0 blue fonts |

`scripts/report.py --baseline check a92bb114` reports `REGRESSION * Result: PASS -> FAIL`.

The regression is caught because without the skill, sonnet computes the DCF in Python and writes hardcoded values into the spreadsheet — no formulas, no formatting, no skill conventions.

### What doesn't work (lessons from earlier challenges)

The original three challenges (budget-tracker, sales-dashboard, quarterly-projection) were deleted because they could not detect a regression. They failed for two reasons:

1. **Prompts encoded the answer.** The prompts said "use formulas," "blue font," "reference assumption cells." The agent transcribed the prompt; the skill was redundant.
2. **verify.sh checked things any LLM knows.** SUM formulas, basic currency formats, bold headers — sonnet defaults to all of these without help.

### Design principles confirmed

- The prompt must describe a real task in business terms only — never implementation details.
- verify.sh must check things the skill specifically and consistently produces, that the model does not produce by default.
- The strongest assertions are unusual specific things: an exact RGB, an exact number format string, a non-default convention.
- Things mentioned in the skill but not consistently produced (yellow assumption highlights, years-as-text) are not safe to assert.

### Cost

| Run | Tokens | Cost |
|-----|-------:|-----:|
| First baseline (with too-strict checks, FAIL) | 19,509 | $0.55 |
| Baseline (relaxed checks, PASS) | 19,846 | $0.49 |
| Regression test (no skill) | 4,457 | $0.13 |
| **Total** | **43,812** | **$1.17** |

The regression run is much cheaper because without the skill the agent does less work (no skill body to read, simpler hardcoded output).
