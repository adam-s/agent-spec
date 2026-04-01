# Journey 4: Onboard a New Project

**Goal:** Take a real project you haven't touched and develop its `.claude/` from scratch using the full iteration loop.

**What this exercises:** The complete agent-spec workflow end-to-end — scaffolding, first eval, diagnosis of a genuinely unknown project, fix development, and the handoff to the project's own `.claude/`.

## Why This Journey Matters

The other journeys use the existing fixture targets (csv-reporter, sqlite-window-queries, hono-websocket-counter). Those are known quantities. This journey is the real test — can agent-spec sit down with a project it's never seen and develop working instructions?

## Find a Project

Good candidates:
- A repo you own with existing tests
- Small enough for Haiku to attempt (~500 lines)
- Has a clear "build this thing" task
- Has a way to verify success (test suite, expected output, running server)

Bad candidates:
- Repos with no tests or verification method
- Repos that need external services (databases, APIs) unless you can mock them
- Repos larger than ~2000 lines (start small)

## Scaffold

```bash
/new-target
```

The skill walks you through creating:
- `targets/<name>/target.yaml`
- `targets/<name>/prompt.md`
- `targets/<name>/verify.sh`
- `targets/<name>/configs/baseline/CLAUDE.md`

Key decisions:
- **What to delete:** Which files should the agent recreate? Start with the main deliverable.
- **What to verify:** Write a verify.sh that checks the actual behavior, not just "file exists."
- **Port usage:** If the project runs a server, use `__PORT__` in prompt.md.

## First Eval (Expect Failure)

```bash
python3 scripts/run_eval.py <name> baseline --model claude-haiku-4-5-20251001
python3 scripts/dashboard.py --latest --summary
```

Read the failure output carefully:
```bash
cat results/<run_id>/produced/*.py   # or *.js, *.ts
python3 scripts/dashboard.py --latest --stream | grep -E "FAIL|ERROR|score"
```

Common first-run failures:
- Agent doesn't know the project structure
- Agent uses wrong libraries or APIs
- verify.sh has a bug (tests the wrong thing)
- Setup commands are incomplete (missing dependencies)

**Fix verify.sh first.** If verify.sh is wrong, the iteration loop optimizes for the wrong thing.

## Iterate

```bash
/iterate <name> --instances 3 --max-depth 5
```

Monitor in another terminal:
```bash
python3 scripts/dashboard.py --latest --stream
```

After each depth, check:
```bash
python3 scripts/tokens.py --session <session_id>
python3 scripts/dashboard.py --diff <prev_id> <curr_id>
```

## The Hard Part: Fix Classification

When onboarding a new project, most findings are Level 2 (target instructions):
- "Agent didn't know to use library X" → Add to target's CLAUDE.md
- "Agent wrote server on wrong port" → Clarify port in prompt.md
- "Agent forgot to handle edge case Y" → Add hint to CLAUDE.md

But some findings reveal Level 0 (harness) gaps:
- "verify.sh doesn't check error case" → Fix verify.sh
- "Setup didn't install required dependency" → Fix target.yaml setup
- "Agent's output format doesn't match what verify.sh expects" → Align both

## Graduate the Config

Once all instances pass, the tuned config IS the project's `.claude/`. Copy it out:

```bash
cp -r targets/<name>/configs/tuned /path/to/real-project/.claude
```

Run one more eval to confirm the graduated config works:
```bash
python3 scripts/run_eval.py <name> tuned --instances 3
```

## Success Criteria

- [ ] New target scaffolded with working verify.sh
- [ ] First eval run (even if it fails)
- [ ] At least 2 iteration depths
- [ ] Converged to all-pass OR documented remaining gaps
- [ ] Config diff shows meaningful instruction evolution
- [ ] Tuned config copied to real project
- [ ] Handoff doc written

## What to Improve After

1. **Was scaffolding smooth?** If `/new-target` missed something, improve the skill.
2. **Did verify.sh need multiple fixes?** Consider a "verify the verifier" step in the workflow.
3. **How many depths to convergence?** If >3 for a simple project, the diagnosis step might be weak.
4. **Did the graduated config actually help the real project?** Test it outside the sandbox.
