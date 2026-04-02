# Experiment Types

What experiments can a developer run with agent-spec? Each type answers a different question. Understanding these types is critical for the `/new-experiment` skill — the orchestrator must understand what the developer wants to know before setting up the harness.

## The Types

### 1. Performance Comparison

**Question:** Which `.claude/` config is most token-efficient?

**What varies:** Configs (different `.claude/` directories)
**What's fixed:** Task, model, source code
**Output:** Config ranking by cost-to-correctness

**Example:** "I have 6 different CLAUDE.md approaches. Which produces the cheapest passing run?"

**How it runs:** `parallel.py <target> --configs A,B,C,D,E,F`

---

### 2. Baseline Establishment

**Question:** How does my current setup perform?

**What varies:** Nothing — this is the control measurement
**What's fixed:** Everything
**Output:** Stored baseline (tokens, cost, turns, tool calls, pass/fail)

**Example:** "Record how my project performs today so I can detect regressions later."

**How it runs:** Single run (or N runs for variance), store result in target.

---

### 3. Regression Detection

**Question:** Did my change make things worse?

**What varies:** The `.claude/` or project code (developer made a change)
**What's fixed:** Task, model
**Output:** Delta from baseline — regression, improvement, or within threshold

**Example:** "I rewrote my CLAUDE.md. Did it help or hurt?"

**How it runs:** Run against stored baseline, compare. Requires a baseline to exist.

---

### 4. Iterative Optimization

**Question:** Make my `.claude/` as efficient as possible.

**What varies:** `.claude/` — auto-modified by the orchestrator between runs
**What's fixed:** Task, model, termination condition
**Output:** An improved `.claude/` that meets the termination condition at lower cost

**Example:** "Keep improving my instructions until the agent passes consistently under $0.30."

**How it runs:** `/iterate` — run, diagnose failures, modify `.claude/`, run again, repeat until convergence.

---

### 5. Capability Testing

**Question:** Can an agent do this at all?

**What varies:** Files deleted (cordyceps)
**What's fixed:** Config, model
**Output:** Pass/fail — is the task achievable?

**Example:** "If I delete server.ts, can Haiku rebuild it from test.js alone?"

**How it runs:** Single run with `delete_before_run`. Binary outcome.

---

### 6. Robustness Testing

**Question:** Does my `.claude/` work across models?

**What varies:** Model (haiku, sonnet, opus)
**What's fixed:** Config, task
**Output:** Model × pass rate × cost matrix

**Example:** "My CLAUDE.md works with Opus. Does it work with Haiku too?"

**How it runs:** `parallel.py <target> --models haiku,sonnet,opus`

---

### 7. Consistency Testing

**Question:** Are my results reliable or flaky?

**What varies:** Nothing — just temperature/randomness across runs
**What's fixed:** Everything
**Output:** Variance measurement — cost spread, pass rate across N runs

**Example:** "I got a PASS but was it luck? Run it 5 times."

**How it runs:** `parallel.py <target> --instances 5`

---

### 8. Stress Testing

**Question:** Do my instructions generalize to harder cases?

**What varies:** Input data/complexity (via cordyceps injection)
**What's fixed:** Config, model
**Output:** Pass rate under increasing difficulty

**Example:** "My CLAUDE.md works for a 50-row CSV. What about 5,000 rows? Missing values? Unicode?"

**How it runs:** Multiple targets with different injected data, same config.

---

### 9. Ablation Testing

**Question:** Which parts of my `.claude/` actually matter?

**What varies:** Components removed (one at a time)
**What's fixed:** Task, model
**Output:** Impact per component — which removals cause regression?

**Example:** "I have CLAUDE.md, 3 rules, a skill, and 2 hooks. Which ones are actually helping?"

**How it runs:** Generate N configs, each with one component removed. Run all. Compare to full config.

---

### 10. Component Audit

**Question:** Is my `.claude/` well-designed?

**What varies:** N/A — static analysis, no agent run
**What's fixed:** N/A
**Output:** Decision tree score — misplacements, token waste, missing enforcement

**Example:** "Score my `.claude/` directory before I run any experiments."

**How it runs:** Read `.claude/`, score against decision tree scoring rules (M1-M8, G1-G6, etc.)

---

## Commonalities

Looking across all types, the underlying operation is always:

```
prepare sandbox → (optionally modify it) → run agent → capture result → compare against something
```

The types differ in what gets modified and what gets compared:

| Type | What's modified (independent variable) | Compared against |
|------|---------------------------------------|-----------------|
| Performance comparison | Config | Other configs |
| Baseline establishment | Nothing | Nothing (first measurement) |
| Regression detection | Developer's change | Stored baseline |
| Iterative optimization | Auto-modified `.claude/` | Previous iteration |
| Capability testing | Deleted files | Pass/fail threshold |
| Robustness testing | Model | Other models |
| Consistency testing | Nothing (temperature) | Other runs of same config |
| Stress testing | Input data | Same config on normal data |
| Ablation testing | Components removed | Full config |
| Component audit | N/A | Decision tree rules |

## Possible Collapses

Some types might be the same underlying operation with different parameters:

- **Robustness testing = Performance comparison** where the variable is model instead of config
- **Consistency testing = Baseline establishment** with N instances instead of 1
- **Stress testing = Performance comparison** where the variable is injected data
- **Regression detection = Performance comparison** where one config is the baseline and the other is the change

This might reduce to:

1. **Compare** — run multiple variants, rank them (covers performance, robustness, stress, regression, ablation)
2. **Measure** — run one config, store the result (covers baseline, consistency, capability)
3. **Optimize** — run, diagnose, fix, repeat (covers iterative optimization)
4. **Audit** — static analysis, no run (covers component audit)

## Reference Types

Every experiment needs a **reference** — the thing that defines success. The reference type determines how verification works. This is the missing abstraction that makes agent-spec work for any project, not just "delete file, grep for PASS."

### The taxonomy

| Reference type | What defines success | Verification method | Example |
|---|---|---|---|
| Test file | Test suite outputs pass/fail | Run tests, grep output | "5/5 tests passed" |
| Screenshot | Result visually matches reference image | Screenshot result, compare to reference | Match YouTube player layout |
| API response | Endpoint returns expected data | Curl endpoint, diff output | Route returns expected JSON |
| Performance threshold | Cost/tokens under a limit | Measure from event trace | "Complete under $0.30" |
| Baseline | No regression from stored result | Compare against stored baseline | "Same or better than last run" |
| Exit code | Command succeeds | Run command, check exit 0 | Build compiles, lint passes |
| Composite | Multiple conditions must all pass | Chain multiple checks | E2E passes AND screenshot matches AND cost < $0.50 |

### How reference type drives the target

The reference type changes everything about how the target is set up:

**Test file reference (what we have today):**
```yaml
reference:
  type: test-file
  file: test.js
  pass_pattern: "tests passed"
```
verify.sh: run test file, grep for pattern. Simple.

**Screenshot reference (intercept2 dashboard):**
```yaml
reference:
  type: screenshot
  file: youtube-player.png
```
verify.sh: start servers, navigate browser, screenshot result, compare to reference image. Complex — needs running services, browser automation, visual comparison.

**API response reference:**
```yaml
reference:
  type: api-response
  endpoint: /api/search?q=test
  expected: expected-response.json
```
verify.sh: start server, curl endpoint, diff against expected JSON.

**Exit code reference:**
```yaml
reference:
  type: exit-code
  command: "pnpm build && pnpm lint"
```
verify.sh: run command, check exit code. No output parsing needed.

**Composite reference:**
```yaml
reference:
  - type: test-file
    file: test.js
    pass_pattern: "tests passed"
  - type: screenshot
    file: youtube-player.png
  - type: performance
    max_cost: 0.50
```
verify.sh: chain all checks. All must pass.

### The abstract structure of any experiment

Every experiment, regardless of type, has these six parts:

1. **Source** — a folder (any folder, any state, with or without `.claude/`)
2. **Reference** — the thing that defines success (test file, screenshot, API response, threshold, baseline)
3. **Task** — what the agent must do (prompt.md)
4. **Setup** — how to get the environment running (inferred from project: package.json → npm install, etc.)
5. **Verification** — how to check the result against the reference (verify.sh, generated from reference type)
6. **Cordyceps plan** — what to modify in the sandbox (delete files, inject data, swap `.claude/`)

The orchestrator infers 4-6 from the source and reference. The developer provides 1-3 (and often the orchestrator can draft the task from the reference).

### Why this matters

Without reference types, agent-spec only works for projects with test suites that output "X/Y passed." That's a tiny fraction of real development.

With reference types, agent-spec handles:
- **Visual development** — "build a dashboard that matches this screenshot" (intercept2)
- **API development** — "build a route that returns this JSON"
- **Build/lint gates** — "make the build pass"
- **Performance optimization** — "solve this under $0.30"
- **Any combination** — composite references chain multiple conditions

The developer doesn't need to know about reference types. They show agent-spec a folder and say what they want. The orchestrator figures out which reference type fits and generates the target.

### The intercept2 example

Developer says: "I want to iterate on dashboard development. Here's a screenshot of the YouTube player. The agent should build it with shadcn."

The orchestrator:
1. **Source:** `/Projects/intercept2`
2. **Reference:** screenshot — `youtube-player.png`
3. **Task:** "Build a dashboard page that recreates the YouTube player using shadcn components"
4. **Setup:** `pnpm install`, start API server on 3001, start web on 3000
5. **Verification:** start servers, navigate to dashboard page, screenshot, compare to youtube-player.png
6. **Cordyceps:** delete the dashboard page files, keep everything else

But here's the Level 0 / Level 1 distinction: the agent inside the sandbox (Level 1) iterates on CODE to match the screenshot. agent-spec at Level 0 watches the trace and iterates on INSTRUCTIONS so the next fresh agent does it cheaper.

## Open Questions

- How does screenshot comparison work in verify.sh? LLM judgment? Pixel diff? Perceptual hash?
- Should the developer pick an experiment type explicitly, or should the orchestrator infer it from their question?
- How does the developer describe stress test variants? Do they provide the harder data, or does the orchestrator generate it?
- Ablation testing requires generating N configs automatically. Does agent-spec do this, or does the developer create them?
- Where do baselines get stored? `targets/<name>/baselines/`? In the events.jsonl? A separate file?
- How does setup work for complex projects (multiple servers, browser automation)? Template scripts per stack?
