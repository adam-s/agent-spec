# Toward an Agent Language Specification

> A spec for things that don't execute deterministically. Third in a series with [self-reflective-agent-paradigm.md](self-reflective-agent-paradigm.md) and [agent-language-vs-code.md](agent-language-vs-code.md).

## 0. The question

The four self-reflective agents — [agent-spec](../../.claude/), [alphadidactic](../../../submodules/alphadidactic/.claude/), [intercept](../../../submodules/intercept/.claude/), and [testing-claude-agent](../../../../testing-claude-agent/) — perform tasks consistently. They produce reproducible behavior on a probabilistic substrate. They were not built by the same people; they do not share infrastructure; they target wildly different domains. And yet they converge, structurally and operationally, on the same set of primitives.

The question: **can we define a constant — a structured set of instructions, commands, and syntax — that accomplishes tasks probabilistically, and write it down as a specification?**

This document argues yes, sketches what such a spec would look like, and identifies the one genuinely novel thing it would require: **statistical conformance tests against probabilistic specifications**, which have no precedent in code-language specs.

## 1. The convergence is the evidence

When biological evolution converges independently on the same structure — eyes in cephalopods and vertebrates, wings in birds and bats and insects — that structure is selecting for something real in the environment. Convergence under selection is evidence that there exists a narrow set of solutions to a fixed problem.

The four specimens are convergent evolution. They were each written by people trying to get reliable task completion out of a probabilistic resolver. Without coordinating, they all reinvented:

- Deterministic verification (`verify.sh` → `RESULT: PASS/FAIL`)
- Hook-enforced structural constraints
- Sub-agent isolation with fresh contexts
- Generalization guards on instruction patches
- Tokens-to-correctness as the headline metric
- Level / capability separation
- Disposable workspaces
- Bounded sub-agents with explicit fuel
- Adversarial / read-only review
- Recursion with measurable stop conditions

That list is the answer to "what selects for working on a stochastic substrate." The constant exists. The spec is the project of writing it down. The hard part isn't *whether* it's possible — the four specimens are existence proof. The hard part is **figuring out what *level of abstraction* the spec lives at**, given that the substrate refuses to be deterministic.

## 2. Why a code-style spec doesn't work

Code language specs (K&R C, ECMA-262, the Python language reference) define two things:

1. **A grammar.** Which strings of characters constitute a well-formed program.
2. **An operational semantics.** What each well-formed program *does*, deterministically, on a given input.

They can do (2) because the interpreter is deterministic. The spec is, in principle, a function:

```
spec : (Program, Input) → Output
```

This function exists, is total, and can be checked exactly. A C program either prints `42` or it doesn't. If two C compilers disagree, at least one is non-conformant.

You cannot write that spec for an agent language. The interpreter is stochastic. The function is not from program × input to output — it is from program × input to a *distribution* over outputs:

```
spec : (Program, Input) → Distribution(Output)
```

This is the same shift that happens when you go from deterministic algorithms to randomized ones, or from a Turing machine to a probabilistic Turing machine. You don't lose the ability to reason about programs. You reason at a different level: about *properties that hold over the distribution* rather than about exact outputs.

The constant we're looking for is **constant in distribution**, not constant in execution. Once you accept that, the spec becomes possible — and the four specimens turn out to already be probing its shape.

## 3. The five-layer spec

A spec for an agent language has five layers, in order of decreasing determinism. The deterministic layers are non-negotiable; the probabilistic layers are deliberately under-specified.

### Layer 1 — The substrate assumption

The spec assumes a particular kind of interpreter and refuses to say anything about programs running on a different one.

> **Substrate assumption.** The interpreter is a context-windowed probabilistic next-token predictor with attention-based recall, no built-in control flow, no persistent memory across processes, no guaranteed name resolution, and a finite context window. Every operation the interpreter performs is conditioned on the entire context, sampled from a learned distribution, and non-replicable.

This is the equivalent of "C assumes a von Neumann machine with bytes, pointers, and sequenced execution." Get this wrong and the rest of the spec is meaningless. State it explicitly so future readers know what they're getting.

### Layer 2 — Harness primitives (the deterministic foundation)

These are the things the spec requires the **harness**, not the model, to provide. The harness is the part of the runtime that lives outside the model and can be made deterministic. Layer 2 is where all the actual guarantees come from.

The harness must implement:

- **A loader** that respects the five visibility tiers from [agent-language-vs-code.md §2.1](agent-language-vs-code.md):
  1. Always-loaded (CLAUDE.md, rules/)
  2. Headers-only (skill frontmatter)
  3. Lazy / on-demand (skill bodies, reference/)
  4. Process-isolated (sub-agent contexts, mandatorily fresh)
  5. Hidden-from-model (hooks/, harness-only)

- **Tool-use join points.** Every tool invocation by the model passes through harness-level pre/post advice points where hooks can fire, inspect, modify, or block the call.

- **Sub-agent spawning** with the guarantee that the child gets a fresh context that does not inherit the parent's working memory. Communication is restricted to the launch prompt and the return value.

- **Deterministic verification.** A `verify.sh` (or equivalent) primitive whose semantics are: run a script, read its exit code or output string, treat the result as ground truth. The model's opinion about whether the work is correct is not consulted.

- **Token accounting.** Per-call and per-run counters of input + output tokens (never cache reads), exposed to the harness for budget enforcement and metric aggregation.

- **Capability enforcement.** Filesystem and process scopes declared in `.claude/` are enforced by the harness — a level cannot reach paths outside its declared scope, regardless of what the model attempts.

These are the deterministic primitives. **The model cannot violate them because they happen outside the model.** Everything reliable about an agent language is built on top of Layer 2; everything probabilistic is built underneath.

### Layer 3 — Grammar

The well-formedness rules for `.claude/` itself. This is the part that looks most like a normal language spec, and is the easiest to write down formally.

A spec-conformant `.claude/` directory has:

- **An identity statement** in `CLAUDE.md` — a top-level declaration of what the agent is for.
- **`rules/`** — always-loaded preludes. Each rule is a markdown file with a declared token weight (computable as `wc -c`) and a declared kind annotation (see Layer 4).
- **`skills/`** — named procedures. Each skill is a directory containing `SKILL.md` with frontmatter declaring `name`, `description`, optional `preconditions`, optional `postconditions`, and a declared `cost_estimate`. The body is hidden until invoked.
- **`agents/`** — spawnable sub-processes. Each agent file declares `name`, `description`, a mandatory `fuel` budget (max tool calls), `read_paths`, `write_paths`, and the rules it inherits.
- **`hooks/`** — harness-enforced advice. Each hook declares the join point it advises (`PreToolUse`, `PostToolUse`, `SubagentStop`, `WorktreeCreate`, …) and the matcher (which tools/operations it applies to).
- **`reference/`** — lazy stdlib. Files referenced by name from rules/skills/agents but never auto-loaded.

This grammar can be expressed as a JSON Schema in roughly 50 lines. It can be checked by a tool that doesn't need to know anything about agents or models — it just walks the directory and validates structure.

### Layer 4 — Semantic invariants (the heart of the spec)

For each construct in Layer 3, the property that must hold *regardless of how the model behaves*. This is where the spec stops being a grammar and starts being a *specification*. These invariants are checkable either statically (linter) or dynamically (harness enforcement at run time).

**Verifier invariant.** A postcondition is satisfied if and only if `verify.sh` exits 0. The model's output, claims, summaries, and self-reports are not part of the truth condition.

**Hook invariant.** A hook fires on every tool call matching its declared join point and matcher. The model cannot skip a hook by phrasing a request differently.

**Sub-agent invariant.** When a sub-agent is spawned, its context is empty except for the launch prompt and its own declared `.claude/` files. The parent's context is inaccessible. The child's context is inaccessible to the parent except via the explicit return value.

**Capability invariant.** A construct at level *L* can read only paths in its declared `read_paths` and write only paths in its declared `write_paths`. The harness rejects all other accesses, regardless of what the model attempts.

**Generalization (kind) invariant.** A rule is well-typed if and only if its body does not contain identifiers from a registered specificity-domain set (library names, error codes, project names, file paths to specific files, framework versions). A rule that names `numpy`, `axios`, or `fooproject` is rejected as kind-violating. The annotation on each rule is its quantifier domain — `∀task`, `∀http_call`, etc.

**Cost invariant.** The total weight of always-loaded files (CLAUDE.md + rules/) does not exceed the declared budget. The estimated cost of any single skill invocation does not exceed its declared `cost_estimate` plus tolerance.

**Termination invariant.** Every iteration loop in any skill or agent declares a measurable stop condition: a max-depth, a verifier-PASS, a fuel-exhaustion event, or a convergence flag computed by a deterministic check. Loops without a stop condition are rejected at lint time.

**Failure-visibility invariant.** Every iteration emits a per-run signal containing at minimum: outcome (PASS/FAIL/ERROR), token count (input + output, no cache), elapsed time, and a unique run identifier. Aggregations over multiple runs must preserve the per-run signal — they cannot collapse into pass rates without listing every failure.

These are the type rules of the agent language. They can be statically checked by a linter (the one proposed in [agent-language-vs-code.md §5](agent-language-vs-code.md)) and partially enforced at runtime by the harness.

### Layer 5 — Program-level guarantees (probabilistic)

What you can claim about any spec-conformant program, *averaged over runs*. This is the layer that has no analog in code-language specs. It's also the layer that makes the whole thing actually useful.

For any spec-conformant `.claude/` program *P* and input *I*, the spec guarantees:

**Termination in expectation.** *P* halts with probability 1 within its declared cost budget, because the harness will force termination at the budget boundary even if the model is still running.

**Bounded cost.** Total tokens consumed by *P* on *I* are ≤ declared budget, with high probability. The harness enforces hard caps; the spec does not promise that the model will be efficient, only that it will be terminated.

**Reproducibility of distribution.** Two runs of *P* on *I* yield outputs drawn from the *same distribution*. Individual outputs differ; the distribution is invariant. This is the agent-language equivalent of referential transparency, and it is what makes regression testing possible.

**Failure visibility.** Every run produces a signal that the harness can record. No failure is silent. No success is silent. The empirical distribution of runs is observable.

**Distributional comparability.** Two spec-conformant programs *P₁* and *P₂* on the same input *I* produce two distributions over outputs that can be compared along measurable axes: pass rate, mean tokens, variance, tail behavior. Improvements are statements about *distributional* differences, not individual runs.

**Convergence under iteration.** A spec-conformant self-reflective loop (one that uses the iteration primitives in Layer 2 and the verifier invariant in Layer 4) is guaranteed to terminate with one of: PASS within max-depth, FAIL with declared diagnostic output, or fuel-exhaustion with a structured signal. No "still running, status unclear" outcome is permitted.

These are the *useful* guarantees. They are the things you can rely on when you write a program in this language. They are weaker than code-language guarantees in the obvious way (no exact output) and stronger in a non-obvious way (they hold over distributions, which means they survive the resolver being stochastic).

## 4. What the spec deliberately does NOT pin down

This is the part that distinguishes an agent-language spec from a code-language spec, and it's the part that makes some people resist calling it a spec at all. Worth being explicit.

The spec does **not** specify:

- Which token the model emits next.
- Which skill the model chooses to invoke at any given step.
- The exact sequence of tool calls in any run.
- Whether a run will pass on the first try, the third, or never.
- How a particular rule is "interpreted" by the model.
- The exact prose the model uses in any output.

These are all *under-determined by design*. The spec only constrains the envelope. Inside the envelope, the resolver is free to be probabilistic, creative, adaptive, surprising — which is the whole reason we use a model instead of a script. If you wanted determinism for these things, you would not use an agent.

This is the answer to the open question from [agent-language-vs-code.md §7](agent-language-vs-code.md): Position A (fight the fuzziness) and Position B (lean into it) are not in conflict. They operate at different layers. **Position A is the rule for Layers 1–4. Position B is the rule for Layer 5 inside the envelope.** The spec is strict about the boundary and loose about the interior. That's how you get consistent behavior out of an inconsistent substrate.

A good agent-language program is **strict on its skin and soft on its inside.** The skin — verifiers, hooks, capabilities, fuel meters — is non-negotiable. The inside — the actual sequence of thoughts and tool calls and re-readings — is allowed to vary run to run, because variance is where the value is.

## 5. The novel piece: statistical conformance testing

Here is the one part of this spec that has no precedent in code-language specs, and that I think would be genuinely new work to build.

A C language spec ships with a conformance test suite. Each test is a small C program with an expected output. A conformant compiler runs the program and compares the output exactly. `printf("hello\n")` prints `hello\n` or your compiler is non-conformant.

An agent language spec cannot do this, because no conformant runtime produces the same output twice. So the conformance test has to be **statistical**:

- A test is a `.claude/` program plus an input plus a *declared distribution envelope*.
- A conformance check runs the program N times (N=20, 50, 100 — depending on tolerance) and computes the empirical distribution of outputs.
- The check passes if the empirical distribution falls inside the declared envelope: pass rate within bounds, mean tokens within bounds, variance within bounds, no failures of declared invariants.

**Example conformance test:**

```yaml
test: minimum-self-reflective-loop
program: ./test-programs/min-iterate/.claude/
input: ./test-programs/min-iterate/prompt.md
envelope:
  pass_rate: ">= 0.95"
  mean_tokens: "<= 8000 (± 1500)"
  max_tokens: "<= 12000"
  failure_modes_observed:
    fuel_exhaustion: "<= 0.05"
    verify_fail_persistent: "== 0"
  invariants_violated: "== 0"
runs: 50
```

Run the program 50 times. Compute pass rate, mean tokens, max tokens, observed failure modes. Compare to the envelope. The runtime is conformant if and only if the empirical distribution falls inside.

This is a real artifact you can build. It uses standard statistical machinery (confidence intervals, power analysis) applied to a setting that has not historically used them. It is also the thing that turns "spec" from a piece of prose into something you can *check*.

The deeper claim: **the conformance suite is the spec.** The five layers above are the prose explanation, but the actual definition of "what an agent language is" is the set of programs in the conformance suite plus the envelopes they're declared to satisfy. Just as ECMA-262 is technically prose but is operationally defined by the test262 suite, an agent language spec would be technically the five layers but operationally defined by its statistical conformance suite.

## 6. Building the first version

Concretely, the smallest thing that would count as "an agent language spec exists":

1. **A schema file** (~50 lines) defining the Layer 3 grammar.
2. **A linter** (~500 lines) that checks the Layer 4 invariants statically. Catches contradictions, missing references, overfit terms, capability leaks, cost-budget violations, missing termination conditions, missing failure visibility.
3. **A reference harness** that implements Layer 2 — loader with five tiers, hook dispatch, sub-agent fork-with-fresh-context, verifier execution, token accounting, capability enforcement.
4. **A conformance test suite** of ~10 small `.claude/` programs paired with declared envelopes, plus a runner that executes each N times and checks the empirical distribution against the envelope.
5. **A document** that explains the substrate assumption, the layer model, and how to write a conformant `.claude/`.

That is the K&R C of agent languages. It is opinionated, informal, written by a few people with strong taste, and useful precisely because it gives everyone else a fixed point to reason against.

It is also the smallest thing that would let us answer questions like:

- "Is intercept's `.claude/` conformant to the spec?" (Run the linter; check the invariants; declare or reject.)
- "Does Sonnet 4.6 produce the same distribution on this program as Opus 4.6?" (Run the conformance test on each; compare empirical distributions.)
- "Did this instruction patch improve the program?" (Run the conformance test before and after; check whether the new envelope dominates the old one along every axis.)
- "Is this `.claude/` overfit to its domain?" (Run the linter's kind-system check; reject any rule whose body names a registered specificity-domain term.)
- "Are these two `.claude/` programs equivalent?" (Run both N times; compare the distributions; if they fall in the same envelope, they're observationally equivalent regardless of the prose.)

None of these questions can be asked precisely today. All of them become askable as soon as the spec exists.

## 7. Why this matters

The four specimens prove that consistent behavior on a probabilistic substrate is possible. The convergence proves that there's a narrow set of patterns that produce it. What's missing is the *fixed point* — the written-down thing that future builders can target instead of rediscovering the patterns from scratch.

Right now, building a self-reflective agent is folklore. You read four `.claude/` directories, you internalize the patterns, you make your own. The patterns aren't named, the invariants aren't checked, the conformance isn't testable. Every new agent is an act of taste.

A spec is what turns folklore into engineering. It doesn't take the taste away — the same way K&R C didn't take the taste out of writing C — but it gives you a floor. Below the floor, your program is broken. Above the floor, your program might still be bad, but at least it's well-formed and the failures are visible.

The four specimens have given us enough convergent evidence to identify the floor. The work now is to write it down precisely enough that someone can implement it.

## 8. Open questions for the spec

Even with the layer model, there are real unknowns. Worth listing so we don't pretend the spec is closer than it is.

- **Where is the boundary between Layer 4 invariants that can be checked statically and those that must be checked at runtime?** The kind invariant looks static-checkable. The cost invariant is borderline (you can statically check declared budgets but not actual run cost). The termination invariant is static for declared loop bounds but dynamic for "did the loop actually terminate." A real spec needs to draw this line precisely.

- **What's the registered specificity-domain set for the kind system?** If overfit means "names a specific library or error code," someone has to maintain the list. Is it part of the spec? Is it project-local? Is it discovered automatically?

- **How big does N need to be for statistical conformance?** Power analysis on Bernoulli distributions says you need ~50–100 samples to distinguish a 90% pass rate from a 95% one with high confidence. Across a suite of 20 tests, that's 1000–2000 model runs per spec check. That's expensive but tractable. The question is whether expensive-but-tractable is enough.

- **How do you handle interpreter drift?** Model versions change. A program conformant to the spec under Opus 4.6 may not be conformant under Opus 5. Is the conformance test "this program produces this distribution on *some* compliant interpreter" or "on *every* compliant interpreter"? Code specs can require both because compilers are deterministic. Agent specs can't.

- **Is there a notion of "undefined behavior"?** C's most powerful spec construct is "undefined behavior" — things the spec deliberately leaves unspecified so compilers can optimize. An agent language probably needs an analog: things the model is allowed to do however it wants, as long as the invariants hold. What goes in that bucket?

- **Does the spec need a formal semantics, or is the conformance suite enough?** Code language specs increasingly come with formal operational semantics (Coq, K framework). Could an agent language have a formal probabilistic semantics, or is empirical conformance the most precision the substrate allows?

These are real open questions. None of them block writing the first version of the spec. All of them will need answering by version two.

---

*Last updated 2026-04-06. Third in a series. The first three documents — paradigm, language analogy, spec — are working notes, not doctrine. The next move is to start building: the linter is the smallest concrete artifact that would prove the spec is more than a metaphor.*
