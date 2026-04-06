# `.claude/` as a Programming Language

> Working notes on the question: what is the relationship between `.claude/` instructions and code, from a computer-science point of view, and could we build a consistent "agent language" by inheriting from the patterns programming languages have already evolved?

## 1. The framing is wrong: it's not "natural language vs code"

The instinct is to contrast natural-language instructions with formal programming languages along a syntax axis: English is fuzzy, Python is precise. This framing is misleading. The real distinction is sharper, and once you see it the rest of the analysis follows almost mechanically.

A C compiler and a Python interpreter execute code with a **deterministic resolver**. When you write `foo()`, the runtime has an unambiguous algorithm — symbol table lookup, vtable dispatch, classpath resolution — that finds `foo` and dispatches to it. Names resolve. Types check. Control flow is honored. Errors raise.

`.claude/` instructions are executed by a **probabilistic resolver** (the model) over a **content-addressed memory** (the context window) where **attention is the dispatch mechanism**. When CLAUDE.md says "use the iterate skill," nothing guarantees the model will surface it, find it, or honor it. The "function call" is *a suggestion the resolver may take with some probability conditioned on the rest of context*.

That single change cascades into almost every difference you'd otherwise list. The vocabulary differences (English vs. syntax) are downstream of the resolver difference, not the other way around.

## 2. Cascading consequences

| Code property | Why code has it | What replaces it in agent instructions |
|---|---|---|
| **Lexical scope** | Compiler resolves names by static algorithm | Scope exists, but it's coarser than lexical and operates at the *process/file* boundary instead of the variable boundary. See §2.1 below. |
| **Type checking** | Catches errors before runtime when they're cheap | No compile time exists. `verify.sh` at runtime is the only type system. |
| **Function calls** | Stack frame, return address, deterministic dispatch | "Skill invocation" is a probabilistic re-read of a markdown file when the model decides to do it |
| **`import` / module resolution** | Deterministic algorithm over module path | Lazy attention over filenames + frontmatter descriptions |
| **Exceptions** | Explicit error path with stack unwinding | Silent drift. The rule is "ignored" with no signal. |
| **Encapsulation** | Private fields, modules, closures | File/process-level only — no encapsulation *within* a single loaded context. See §2.1. |
| **Composition** | Pure functions compose by typed interfaces | Rules compose by accretion. Contradictions are silent. |
| **Versioning** | Semver, lockfiles, package managers | Instructions silently drift as model versions change. No lockfile. |
| **Static analysis** | AST is canonical and inspectable | No canonical AST. The "program" is interpreted differently each run. |
| **Idempotence / purity** | First-class concepts; can be enforced | No notion of side effects vs. reads in the rule itself |

The interesting inversion: programming languages evolved to make a *fast, literal, forgetful, deterministic* machine usable by *slow, contextual humans*. Agent languages need to do the opposite — make a *fast, contextual, forgetful, stochastic* machine usable by humans who write vague instructions. So some patterns flip:

- Code uses **explicit names** because the resolver is dumb. Skills can use **descriptions** because the resolver is smart enough to fuzzy-match.
- Code needs **types** because runtime errors are expensive. Agents need **verifiers** because there is no compile time at all.
- Code uses **comments** for humans reading the source. In agent instructions, *the comments are the program*.

### 2.1 What about scope and encapsulation?

The first version of this document claimed "no scope, everything is visible to everything, encapsulation is impossible." That's wrong. The correct picture is more interesting: Claude Code has **five visibility tiers**, and the right analog isn't "one global namespace" — it's a **Unix process model with explicit module loading**.

| Tier | What's in it | When it enters context |
|---|---|---|
| **1. Always-loaded** | `CLAUDE.md`, `rules/` | At the start of every turn. Truly global. |
| **2. Headers-only** | `skills/*/SKILL.md` frontmatter (name + description) | Listed in a system reminder. The model sees that the skill *exists* and what it claims to do, but **not its body**. |
| **3. Lazy / on-demand** | Skill bodies, `reference/*.md` files | Only when explicitly invoked (`Skill` tool) or `Read`. Until then, they don't exist as far as the model is concerned. |
| **4. Process-isolated** | Sub-agent contexts (`agents/*.md`) | When launched, the sub-agent gets a **fresh context** that does *not* inherit the parent's working memory. Parent and child are mutually invisible except via the launch prompt and the return value. |
| **5. Hidden from the model entirely** | `hooks/*.sh` | Never enter the model's context at all. The harness runs them; the model only sees their output if they print to stderr/stdout on a tool call. |

The PL analog map:

- `rules/` ≈ kernel globals / language prelude
- `skills/` frontmatter ≈ **header files** — interfaces declared, implementations hidden until linked
- `Skill` invocation ≈ `dlopen()` — load a module's body into the current process at runtime
- `reference/` ≈ a lazy stdlib — `import` it when you need it
- Sub-agent launch ≈ `fork()` + `exec()` — new process, new address space, communication only via arguments and return value
- Hooks ≈ **kernel signal handlers** or **eBPF programs** — run by the system in response to events, never in the user-process address space

That's a real encapsulation system. Coarser than lexical scope, but it's how the entire operating system is built.

**Three asymmetries with proper PL scope still hold, though:**

1. **Scope is monotonic — no unload.** Once a reference doc is `Read` into context, it's in there for the rest of the turn. You can't `del` it. Python can; a Claude turn cannot. Context-as-scope is **append-only**. The closest PL analog would be a language where every variable, once introduced, is in scope until end-of-program.

2. **No encapsulation *within* a single context.** Once a rule, a skill body, and three reference docs are all loaded into the same turn, they're in one flat namespace. They can contradict each other and there's no scope rule that says which wins. Boundaries exist at the *file* level (loaded or not loaded) and at the *process* level (parent vs sub-agent), but **never at the statement level**.

3. **The model can't un-see things even when "ignoring" them.** A function in Python can be in scope and never called. A rule in context is *attended to* with some weight on every token generated. There's no equivalent of "in scope but not invoked" — being in context is being active. This is the most alien thing about the resolver, and it's why rules carry token cost just by *existing* in CLAUDE.md.

**The load-bearing implication:** the most powerful encapsulation tool an agent language has is **spawning a sub-agent**, because that's the only way to get a *fresh* context. Skills, references, and rules can only ever *add* to scope. Sub-agents are the only construct that can *create* a new scope. This is why the self-reflective agent paradigm leans so heavily on bounded sub-agents — they're not just for parallelism or budget control, they're the **only encapsulation primitive that resets state**. See §4.9.

## 3. The self-reflective patterns are recognizable PL constructs

Re-read [the self-reflective agent paradigm](self-reflective-agent-paradigm.md) with the resolver framing in mind, and the twelve patterns map cleanly onto programming-language constructs that already exist. The mapping is so clean it suggests the agent-spec/alphadidactic/intercept authors are *re-deriving programming-language design under different constraints*, without naming it that way.

| `.claude/` construct | Programming language analog |
|---|---|
| `rules/` (always loaded) | Global constants / language prelude (like Haskell `Prelude` or Python builtins) |
| `skills/` (metadata + lazy body) | Functions with type signatures and lazy bodies; or modules with header files |
| `agents/` (isolated context) | Processes with isolated address spaces — Erlang/Unix model, *not* threads |
| `hooks/` (PreToolUse / SubagentStop) | Aspect-oriented programming: advice on tool-use join points |
| `reference/` (loaded on demand) | Lazy-loaded standard library |
| `CLAUDE.md` | Main module / entry point |
| `verify.sh` → `RESULT: PASS/FAIL` | The type system, except it runs *after* execution rather than before |
| Worktrees / disposable workspaces | Pure functions by construction — no shared state means no side effects to reason about |
| Generalization guards (`GENERALIZED=yes/no`) | Polymorphism / kind system: a rule whose domain is a specific value (a library, an error code) is "underspecified" the way a non-polymorphic function is |
| Tokens-to-correctness | Static cost analysis / complexity bounds |
| Bounded sub-agents (call budgets) | Resource quotas / fuel in a metered interpreter (think Ethereum gas, or Erlang reductions) |
| Level separation | Capability-based security / sandboxing rings |
| Reviewer / adversary agents | Dual interpreters; or runtime contracts checked by an independent verifier |

The most accurate single analogy: **`.claude/` is most like aspect-oriented declarative logic programming executed by a probabilistic theorem prover, where deterministic verifiers play the role of the type system.** Rules are facts and constraints. Skills are inference procedures. The agent searches for a proof — a sequence of tool calls that reaches `RESULT: PASS`. The verifier accepts or rejects the proof.

This is closer to Prolog or the guarded-command languages than to C or Python. But Prolog has a deterministic search strategy; here the search is stochastic. So the closest *exact* analog might be: **Datalog with a learned heuristic search and an external oracle as the type system.**

## 4. A consistent agent language (sketch)

If we wanted to make `.claude/` a *real* language — one where constructs compose, errors are loud, and you can reason about programs — here are the primitives I'd want. Most of them already exist in proto form in the four specimens; what's missing is making them strict and uniform.

### 4.1 Typed skills

Every skill declares preconditions (verifiable predicates) and postconditions (checkable by a verifier). Calling a skill is gated on the precondition; the postcondition must hold or the "call" is rejected and the work doesn't count.

```yaml
---
name: run-eval
preconditions:
  - "workspace exists at /tmp/{{run_id}}"
  - "config CLAUDE.md is readable"
postconditions:
  - "events.jsonl exists and is non-empty"
  - "verify.sh exit code is 0 or 1 (not crash)"
cost_estimate: 8000  # tokens
---
```

This is recognizable as **design-by-contract** (Eiffel, Ada) — but enforced by the harness, not the language runtime, because there is no language runtime.

### 4.2 Deterministic verifiers as the type system

No skill can claim "done" until its postcondition verifier returns PASS. This is the only honest type check available, because it runs against actual execution traces. It's *runtime* type checking, but enforced *before* the work is allowed to count toward progress.

Conceptually: `verify.sh` is to agent code what a SAT-solving type checker is to dependent types. It's expensive, it runs late, but it's the only thing that catches the errors that matter.

### 4.3 Hooks as advice with explicit join points

Tool-use is the join point. Hooks are before / after / around advice. The harness — not the model — runs them, so they're *actually enforced*, unlike prose rules.

This is the cleanest existing analog. agent-spec, alphadidactic, and intercept all have hook directories doing exactly this. What's missing is treating hooks as a *first-class language construct* with documented semantics: every hook declares what join point it advises, what it can read, what it can block, and what it returns.

### 4.4 Levels as capability rings

Filesystem scopes, branch scopes, context scopes — *declared*, not just described in prose. Crossing a ring requires a capability token the harness checks. This is the alphadidactic worktree-outside-the-repo trick generalized: "the agent literally cannot access X" is stronger than "the agent must not access X."

Mapping to existing CS: Plessey 250, Hydra, KeyKOS, modern WebAssembly component model. Capability-based security has been re-derived many times because it works.

### 4.5 Generalization as a kind system

Every rule is annotated with its quantifier domain. "Applies to any task" is `∀task`. "Applies when working with numpy" is `task = numpy` and gets rejected by the kind checker as overfit.

intercept's `GENERALIZED=yes/no` reviewer field is a primitive type tag. agent-spec's "if you can name the library, it's overfit" is an informal kind rule. A real agent language would make this a static, machine-checkable annotation.

```yaml
---
rule: "Always check the response status before parsing"
applies_to: ∀(http_call)  # not "fetch()" or "axios"
---
```

A linter could scan rules/ and reject any rule whose body grep'd against a registry of known tools, libraries, or error codes — flagging the kind violation before any agent ever reads it.

### 4.6 Cost as a first-class type

Every rule and skill has a token weight (loaded weight for rules, called weight for skills). The compiler — i.e. the orchestrator — optimizes for total weight under correctness constraints. testing-claude-agent is doing this empirically; a real agent language would track it statically.

Closest existing concept: **effect systems** (Koka, Eff). Tokens are an effect. A skill that costs 8000 tokens has an `<8000>` effect annotation. The orchestrator type-checks total cost against a budget the same way an effect system checks IO purity.

### 4.7 Fuel-metered processes

Sub-agents have explicit budgets. Hitting the budget is a *typed event*, not a failure — the parent can pattern-match on it and decide what to do. This is exactly Erlang reductions or Ethereum gas.

```
result = run_agent(builder, fuel=200)
match result:
  case Done(output): ...
  case OutOfFuel(progress, last_state): retry_with(fuel=300, hint=last_state)
  case Failed(reason): patch_instructions(reason)
```

### 4.8 Workspaces as monads (or: pure computation by isolation)

Every iteration is a pure computation in a fresh worktree. No I/O escapes except via the verifier's PASS/FAIL signal. This gives you **referential transparency at the iteration level** even though individual model calls are stochastic.

You can't make the model deterministic, but you can make the iteration deterministic in its *interface*: same inputs (workspace + instructions + prompt) → same *type* of output (PASS or FAIL with token cost). Run the same iteration ten times, get a distribution; that distribution is now itself a measurable, comparable thing.

This is closer to **probabilistic programming** (Pyro, Stan) than to deterministic FP. The unit of reasoning isn't a value but a distribution over values.

### 4.9 Sub-agent spawning is the only encapsulation primitive

Of all the constructs in §4, this one deserves to be singled out because §2.1 establishes it as load-bearing in a way that isn't obvious from the other primitives.

In every other tier of the visibility model — rules, skills, references — scope is **monotonic**. You can add things to context but you cannot remove them. There is no `del`, no end-of-block, no closing brace. Once a doc is `Read`, it's there for the rest of the turn, attended to on every token, costing tokens just by existing.

Spawning a sub-agent is the *only* construct in the entire system that creates a fresh context. It is the only operation that **resets state**. Everything else is append.

This makes sub-agents do triple duty in a consistent agent language:

1. **Parallelism** (the obvious one — do two things at once)
2. **Budget control** (a sub-agent has a fuel meter independent of the parent)
3. **Encapsulation** (a sub-agent gives you a clean room to think in, free of whatever cruft has accumulated in the parent's context)

The third use is the one we tend to undersell. When you launch an Explore sub-agent to investigate something, you're not just delegating work — you're opening a fresh scope that your parent context will never have to pay the token cost of. The sub-agent loads what it needs, finishes, and returns a small structured summary. The intermediate noise — the file reads, the false leads, the unused reference docs — never enters the parent context. The encapsulation is the *whole point*, and parallelism is a side benefit.

A real agent language should treat sub-agent spawning the way C treats `{` — as the canonical way to introduce a new scope. The operation should be cheap, common, and idiomatic, not reserved for "tasks complex enough to delegate." The right mental rule is closer to: **if a unit of work would dirty the parent's context with state the parent doesn't need afterward, it belongs in a sub-agent.**

This also explains a pattern in the four specimens that otherwise looks like over-engineering: agent-spec, alphadidactic, and intercept all have read-only reviewer agents whose entire job is to inspect work the parent already did. Why not just have the parent review its own work? Because the parent's context is already polluted with the implementation details of what it built, and those details bias the review. The reviewer needs a clean room — and "clean room" is just another name for "fresh context," which is just another name for "sub-agent." The reviewer pattern is encapsulation by another name.

## 5. The piece we're missing

Here's the thing I keep coming back to: **what's the analog of a compile-time error?**

The biggest gift code gives you is that bad programs fail *before they run*. Type errors, name errors, syntax errors — all caught for free, in milliseconds, before any compute is spent on execution. The cost of fixing an error scales with how late it's caught; compile-time errors are nearly free.

The closest agent analog right now is:
- Generalization guards (catch overfit rules) — but they fire after you've already iterated and produced findings
- Deterministic verifiers (`verify.sh`) — but they fire after the agent has spent tokens
- Reviewer rubrics — fire after the run completes

All three are *runtime* checks. None of them prevent a bad rule from costing tokens before being detected. A real agent language would want a **static linter for `.claude/` itself**, run before any agent sees it, that catches:

- **Contradictions.** Two rules whose preconditions overlap but whose actions disagree.
- **Missing references.** A rule that says "see reference/foo.md" where foo.md doesn't exist.
- **Overfit terms.** Rules that name a specific library, error code, or tool — kind-system violations.
- **Dead rules.** Rules no skill or agent ever reaches.
- **Cost-budget violations.** Total always-loaded rule weight exceeds the configured budget.
- **Capability leaks.** A rule references a level it shouldn't be able to see (e.g., Level 2 referencing agent-spec).
- **Semantic shadow.** Two rules that mean the same thing in different words — duplication that drifts.

This linter would be the agent-language equivalent of `mypy` or `tsc --noEmit`. It runs in milliseconds. It catches the errors that would otherwise be discovered after a 10-minute eval run. And as far as I know, *nobody has built it yet.*

That's the most concrete next thing. If we wanted to demonstrate that "consistent agent language" is more than a metaphor, building this linter is the proof.

## 6. Where the analogy breaks

Three places the programming-language framing genuinely fails. Worth naming honestly so we don't over-extend.

**1. The interpreter learns.** A C compiler doesn't get better at compiling C between releases (well, it does, but not by reading your code). The agent interpreter — the model — actually adapts to context. A rule that fails in one context might succeed in another not because of any change to the rule but because the surrounding context shifted the model's interpretation. There is no PL analog for this. The closest is JIT specialization, but JIT doesn't change the *semantics* of a program; the model can.

**2. The semantics are a moving target.** Model versions change. A `.claude/` directory that worked perfectly against Sonnet 4.5 may behave differently against Opus 4.6. There is no compiler version you can pin. Lockfiles don't help because the lockable artifact (the model) is not in your repo. This is *worse* than dependency hell — it's interpreter hell.

**3. Stochasticity is sometimes the feature.** A C function that returned different values on different invocations would be a bug. An agent that interprets "build me a dashboard for this API" differently each time is doing what we *want* — the flexibility is the point. We can't push toward full determinism without throwing away the reason to use an agent at all. Some level of fuzziness is load-bearing.

This third point is the hardest one and it leads directly to the open question.

## 7. The open question

**Is the probabilistic resolver a feature or a bug?**

There are two coherent positions and I genuinely don't know which is right.

**Position A: fight the fuzziness.** Push toward more determinism, more typed gates, more hooks, more capability rings, until `.claude/` behaves as much like a strict programming language as the model will tolerate. The agent is a stochastic CPU; our job is to wrap it in enough scaffolding that the *system* is deterministic even though the *substrate* isn't. The agent-spec and alphadidactic patterns lean strongly this way: deterministic verifiers, hooks-not-prose, generalization guards, level separation.

**Position B: lean into the fuzziness.** The fuzzy resolver is *the whole point*. It's why an agent can handle "build me a dashboard for this random API" without you specifying every detail. The patterns we're discovering are just the right amount of structure to add *without* killing that flexibility. The intercept patterns lean this way: skills give general principles, prompts give domain tasks, the agent fuzzy-matches between them, and the looseness is what lets the same skill apply to a thousand different sites.

The two positions disagree on what the right primitive is. Position A wants to make the resolver more like a CPU. Position B wants to make the language better at exploiting a non-CPU resolver. They imply different agent-language designs.

My current bet, weakly held: **the answer is a layered system.** The *outer* layer is strict — capability rings, deterministic verifiers, fuel meters, hooks. The *inner* layer, where the agent actually does work, is fuzzy and flexible. You use Position A for the things that are about safety, cost, and convergence (you can't afford fuzz here). You use Position B for the things that are about creativity, judgment, and adaptation (you can't afford rigidity here). The whole `.claude/` design becomes the question: *which decisions belong in which layer?*

That's the question I'd want to spend the next few iterations of this exploration on. It's also, I think, the deepest substantive question about agent language design that we can ask right now. Programming languages don't have an analog because programming languages don't have a creative interpreter. We're in new territory the minute we admit the interpreter is the smartest thing in the room.

---

*Last updated 2026-04-06. Companion to [self-reflective-agent-paradigm.md](self-reflective-agent-paradigm.md). Working notes, not doctrine.*
