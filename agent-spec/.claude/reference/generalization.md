# Generalization

When the self-improvement loop produces instruction changes, those changes must work for ANY future task — not just the task that surfaced the gap. This is the single most important guard against overfitting.

## Why This Matters

An agent that fixes a numpy dtype bug will naturally want to write an instruction like "check numpy array dtypes when PIL fails." That instruction helps with dtype bugs and nothing else. Worse, it adds cognitive load to every future run — the agent reads it, considers it, and wastes tokens on irrelevant advice.

The generalized version — "trace errors upstream from where they surface to where bad data was created" — helps with dtype bugs, encoding bugs, schema mismatches, and any error where the symptom is distant from the cause.

## The Test

Before committing an instruction change, apply this filter:

1. **Can you name the library, error type, or domain in the finding?** If yes, it's too specific. Rewrite until it's domain-free.
2. **Would this help an agent working on a completely different project?** If no, it's overfit.
3. **Does it describe a principle or a recipe?** Principles generalize. Recipes overfit.

## Examples

| Overfit (reject) | Generalized (accept) |
|-------------------|----------------------|
| "Check numpy dtype when PIL Image.fromarray fails" | "When a library rejects input, check the type and shape at every transformation step" |
| "Add conditional type narrowing to fix the `infer` clause in mapped types" | "When the type system rejects a construct, check whether the generic constraints at each layer are compatible with how the value flows through them" |
| "Use `PARTITION BY` to fix the SQL window function" | "When a query produces wrong aggregations, check whether the grouping boundary matches the intended scope of the calculation" |
| "Run pytest first to see failures" | "Reproduce before diagnosing — run the failing test, read the full traceback, identify the error boundary" |
| "Use git blame to find the breaking commit" | "Narrow the search space before reading code — use history, tests, and error messages to constrain where the bug can be" |

## Train/Held-Out Split

When improving instructions iteratively against a benchmark:

- **Training set** — the reviewer sees these cases and their solutions. Findings are extracted from these.
- **Held-out set** — never shown to the reviewer. Used only to validate that instruction changes generalize.
- **Validation gate** — after applying findings, re-run on the held-out set. If pass rate doesn't improve on held-out cases, the finding was overfit. Revert it.

This is the same train/test split from ML, applied to instruction tuning.

## Connection to Existing Principles

- **"No domain noise"** — fixture-specific results are ephemeral. Only generalized lessons become product changes.
- **Level 2 must be self-sufficient** — instructions that reference specific test cases break when the test changes.
- **Deterministic verification** — the held-out set provides deterministic validation of generalization, not subjective judgment.

## Instruction Style

Rules and reference docs use generalized principles with generic examples:

- Good: "When debugging, start from the error message and work backward through the call chain"
- Bad: "When debugging Rich progress bars, check the `_tasks` list for empty state"

If an example is needed, use a domain-neutral one or explicitly mark it as illustrative, not prescriptive.
