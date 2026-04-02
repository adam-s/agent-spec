# Testing Framework Concepts → Agent Testing

Mapping traditional testing concepts to agent testing analogues. Where agent-spec already has an equivalent, it's noted. Where there's a gap, it's marked for future work.

## Test Structure

| Traditional | Agent Testing | agent-spec today |
| ----------- | ------------- | ---------------- |
| Test suite | **Target** — a project + task + scoring script | `targets/<name>/` |
| Test case | **Run** — one agent attempt in a sandbox | `invoke.py` |
| `describe` / `it` blocks | **prompt.md + verify.sh** — the task and the assertion | Per target |
| Assertions (`expect`, `assert`) | **`RESULT: PASS/FAIL`** — binary outcome from verify.sh | `score.py` |
| Parameterized tests | **Configs, models, stimuli** — same task, different instructions or inputs | `parallel.py --configs a,b` |
| Test tags / filtering | Group targets by category, run subsets | **Gap** |
| `describe.skip` / `it.only` | Skip or focus specific targets | **Gap** |

### Where the analogy breaks

Traditional assertions check return values. Agent assertions check produced artifacts — files, running servers, test output. The agent's "return value" is the entire state of the sandbox after it finishes.

**Opportunity:** Richer assertions beyond pass/fail. Partial scores, graded rubrics (0-100), multi-dimensional scoring (correctness, style, efficiency).

## Setup and Isolation

| Traditional | Agent Testing | agent-spec today |
| ----------- | ------------- | ---------------- |
| `beforeAll` / `beforeEach` | **target.yaml `setup`** — npm install, db seed, etc. | Setup commands in target.yaml |
| `afterAll` / `afterEach` | **EXIT trap** — sandbox cleanup, process termination | invoke.py EXIT trap |
| Test isolation (fresh state) | **Sandbox** — disposable copy in `/tmp/claude/agent-spec-{uuid}/` | Every run gets a fresh copy |
| Docker / containers | **Sandboxes + port allocation** — lighter weight, same isolation idea | Port range 3100-3110 |
| Shared fixtures across tests | **Multiple configs per eval** — each eval has its own configs | `evals/<name>/configs/` |

### Where the analogy breaks

Traditional setup is deterministic — install deps, seed data, done. Agent setup includes **cordyceps** — actively manipulating the environment to create the test condition. You don't just set up the world; you reshape it to test a specific gap in the agent's instructions.

## Mocking and Injection (Cordyceps)

This is where agent testing is fundamentally more powerful than traditional testing.

| Traditional | Agent Testing | agent-spec today |
| ----------- | ------------- | ---------------- |
| Mocks / stubs | **Cordyceps** — rewrite ANY file in the sandbox | `delete_before_run`, `inject/`, config swap |
| Fixture data | **`inject/` directory** — pre-built files copied into sandbox | Per-target inject dirs |
| Dependency injection | **Swapping `.claude/`** — the instructions ARE the dependency | Config variants |
| Environment variables | **`env` in settings.json** — controlled environment | Settings injection |
| Fake servers / test doubles | **Rewrite server code, inject fake APIs** — anything in the sandbox | Full file replacement |

### The cordyceps advantage

Traditional mocking replaces one function or class. Cordyceps can:

- **Delete source files** so the agent must produce them from scratch
- **Swap `.claude/`** to test entirely different instruction sets
- **Inject emitter libraries** (`_apc.py`, `_apc.ts`) for telemetry the project doesn't have
- **Rewrite config files** (Docker, package.json, tsconfig) to test different environments
- **Plant bugs** to test whether instructions catch them
- **Inject fake test output** to test whether the agent reads it correctly

The original project is never modified. The agent doesn't know it's in a sandbox. This is the testing equivalent of a controlled experiment — manipulate one variable, observe the effect.

## Execution

| Traditional | Agent Testing | agent-spec today |
| ----------- | ------------- | ---------------- |
| Test runner (jest, pytest) | **cli.py** — orchestrates sandbox → agent → verify | `scripts/cli.py run` |
| Parallel execution | **parallel.py** — multiple agents simultaneously | `--instances N`, `--configs a,b` |
| Timeout | **TIMEOUT env var** — default 10 minutes | Per-run timeout |
| Watch mode / `--watch` | **`/iterate`** — diagnose failures and fix instructions, not just re-run | Recursive convergence loop |
| CI integration | **Headless `claude -p`** — can run without interaction | **Gap:** no formal CI pipeline |
| Test retries | **Multiple instances** — run N times, check consistency | `--instances 3` |

### Where the analogy breaks

Traditional watch mode re-runs tests when code changes. `/iterate` is fundamentally different — it doesn't just re-run, it **diagnoses why the test failed and fixes the instructions**. It's as if Jest could read your failing test, figure out the bug in your code, patch it, and re-run — automatically.

## Reporting and Analysis

| Traditional | Agent Testing | agent-spec today |
| ----------- | ------------- | ---------------- |
| Test reporter (HTML, JUnit XML) | **report.py, dashboard.py** — pass/fail with cost metrics | `scripts/report.py --all` |
| Code coverage | **Agent coverage** — did the agent read the right files? Use the right tools? | **Gap** (Layer 3 behavior testing) |
| Snapshot testing | **save_baseline.py** — compare against known-good run | Baseline comparison |
| Regression detection | **check_regression.py** — did a change break passing runs? | Per-iteration regression check |
| Flaky test detection | **Consistency across N instances** — all must pass, not just one | Multiple instances |
| Performance benchmarks | **Token/cost metrics** — cost per run, model comparison | `tokens.py`, `--models` flag |
| Test diff (what changed) | **Config diff** — compare instruction sets between runs | `dashboard.py --diff` |

### Where the analogy breaks

Traditional coverage measures "what lines of code were executed." Agent coverage would measure "what information did the agent consult before acting" and "did it use the right tool for the job." This is Layer 3 behavior testing — the event JSONL already captures tool calls, but we don't score them yet.

## Advanced Patterns

| Traditional | Agent Testing | agent-spec today |
| ----------- | ------------- | ---------------- |
| Property-based testing (Hypothesis, fast-check) | **Stimuli** — multiple inputs testing the same instructions | Wireframes, varied prompts |
| Mutation testing | **Cordyceps deletion** — systematically remove code/instructions | `delete_before_run` |
| Contract testing | **verify.sh output format contracts** — hidden contracts the agent must discover | Implicit in verify scripts |
| Benchmark testing | **Model comparison** — cost vs capability tradeoffs | `--models haiku,sonnet` |
| Integration testing | **End-to-end run** — agent builds, tests, and serves a working app | Full sandbox lifecycle |
| Acceptance testing (BDD) | **prompt.md as spec** — natural language description of desired outcome | prompt.md |
| Chaos testing | **Inject failures** — break deps, corrupt files, wrong versions | Cordyceps injection |

### The property-based testing parallel

In Hypothesis, you say "this function should work for ANY valid input" and the framework generates random inputs to find counterexamples. In agent-spec, stimuli serve the same purpose — "these instructions should work for ANY wireframe/dataset/scenario." If they only work for one stimulus, the instructions are overfitting.

## Baselines

In Jest, a snapshot captures what the output looked like when it was correct. In agent testing, the output (working code) is almost guaranteed — agents can fix anything given enough tokens. **The question isn't "can it pass?" but "at what cost?"**

A baseline is the stored result from a known-good run. It captures the agent's execution trace — not just pass/fail, but the cost of getting there:

```
Baseline: csv-reporter @ tuned config
Tokens: 12,400 in / 3,200 out
Turns: 4
Tool calls: Read(test.py), Read(data/sales.csv), Write(report.py), Bash(python3 test.py)
Attempts: 1 (tests passed first try)
Cost: $0.18
Time: 45s
Result: PASS
```

Baselines are stored in `targets/<name>/` — colocated with the target they measure.

### The experimental flow

```
1. Establish baseline
   Run the target with current .claude/ config → store result in targets/<name>/

2. Modify (the experiment)
   Change .claude/ config, delete files, inject code (cordyceps)
   Each change is an isolated experiment in a disposable sandbox

3. Run experiment
   Agent executes in sandbox with the modification applied

4. Compare against baseline
   Tokens: 12,400 → 28,900?  Regression.
   Turns:  4 → 4?             Same.
   Cost:   $0.18 → $0.52?     Regression.
   Cost:   $0.18 → $0.11?     Improvement — new baseline candidate.
```

### Thresholds, not exact matches

Agent temperature means every run varies. Baselines define a **nominal range**, not a fixed number. A baseline of $0.18 with a threshold of ±100% means anything under $0.36 is normal. $0.52 is a warning. $1.80 is a regression.

The threshold bands:

- **Tokens** — ±50-100% of baseline (most variable)
- **Turns** — ±2-3 of baseline
- **Attempts** — should be 1; >2 is a signal
- **Cost** — derived from tokens, same threshold
- **Tool call sequence** — order may vary, but the set should be similar

### Cost-to-correctness is the primary metric

This is the philosophical shift from traditional testing:

| | Traditional (Jest) | Agent testing |
| - | ------------------ | ------------- |
| PASS | Good | Incomplete — how much did it cost? |
| FAIL | Bad | Instructions are broken |
| Cost | Irrelevant (fixed) | **The primary signal** |
| Flaky | Pass/fail variance | **Cost variance** — 3 runs pass but one costs 5x |
| Optimization target | Correctness | Efficiency of instructions |

A `.claude/` that produces PASS at $0.20 is better than one that produces PASS at $2.00, even though both "pass."

### Deterministic termination

**Tests must terminate on deterministic, verifiable conditions — never on subjective judgment.** `verify.sh` outputs `RESULT: PASS` or `RESULT: FAIL`. The agent does not decide if it is done. The test decides. If you cannot write a deterministic verification, you do not have a test.

This is non-negotiable. Without it, you're measuring "does Claude think it did a good job?" which is not a test — it's an opinion.

### Terminology

| Term | Definition |
| ---- | ---------- |
| **Baseline** | Stored result from a known-good run. The control. |
| **Run** | A single agent execution in a sandbox. Produces a result. |
| **Result** | Measured outcome: tokens, cost, turns, tool calls, pass/fail. |
| **Experiment** | A run with a cordyceps modification. Compared against baseline. |
| **Regression** | A result worse than the baseline beyond threshold tolerance. |

## Identified Gaps

Concepts from traditional testing that agent-spec doesn't have yet:

| Concept | What it would mean for agent testing | Priority |
| ------- | ------------------------------------ | -------- |
| Richer assertions | Partial scores, graded rubrics, multi-dimensional (correctness + style + efficiency) | High |
| Agent coverage (Layer 3) | Score the process: did agent read right files, use right tools, follow rules? | High |
| Test tagging | Tag targets by category (`#fast`, `#full`, `#regression`), run subsets | Medium |
| Static analysis (Layer 2) | Score `.claude/` against decision tree without running an agent | High |
| Formal CI mode | GitHub Actions integration for automated regression on PR | Medium |
| Mutation testing | Systematically corrupt `.claude/` components, verify agent still works | Low |
| Watch mode (lightweight) | Re-run on file change without full `/iterate` diagnosis | Low |
| Test matrix | Cross-product of configs × models × stimuli in one command | Medium |
