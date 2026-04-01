# Journey 2: Improve Instructions

**Capabilities tested:** /iterate, parallel execution, fix classification (Level 0 vs Level 2), convergence, scoring, monitoring, handoff

## Scenario

You have a target that passes with bare instructions, but you want to reduce cost, improve reliability, or add new capabilities to its `.claude/`. You use `/iterate` to systematically improve the instructions.

## Steps

### 1. Establish the starting point

```bash
scripts/run-eval.sh my-project baseline --model claude-haiku-4-5-20251001
scripts/save-baseline.sh <run_id>
```

### 2. Create a tuned config to iterate on

```bash
mkdir -p targets/my-project/configs/tuned
cp targets/my-project/configs/baseline/CLAUDE.md targets/my-project/configs/tuned/CLAUDE.md
```

Edit `configs/tuned/CLAUDE.md` with initial instructions.

### 3. Run /iterate

`/iterate my-project` — the skill asks target, instances, max depth, cleanup mode.

### 4. The iteration loop

Each pass: clean → launch → monitor → score → check regression → diagnose → fix → recurse.

```bash
scripts/cleanup.sh
scripts/parallel.sh my-project tuned --instances 3 \
  --model claude-haiku-4-5-20251001
```

Monitor:

```bash
scripts/dashboard.sh <run_id> --summary
```

Score and compare:

```bash
scripts/score.sh <run_id>
scripts/check-regression.sh <run_id>
python3 scripts/report.py <id1> <id2> <id3> --group-by config
```

## Verification Checklist

### Parallel launch

- [ ] 3 instances launched simultaneously (not sequentially)
- [ ] Each instance gets a unique port (3100, 3101, 3102)
- [ ] Each instance gets a unique run_id (8-char hex)
- [ ] Each instance gets its own sandbox in `/tmp/claude/agent-spec-{uuid}/`
- [ ] No sandbox directory name collisions across instances
- [ ] All 3 instances use the same config (tuned)
- [ ] All 3 instances use the same model
- [ ] `parallel.sh` stdout prints exactly N run_ids (one per line)
- [ ] `parallel.sh` stderr shows instance progress
- [ ] Manifest file created at `/tmp/agent-spec-parallel-{ts}.txt`
- [ ] Manifest contains all run_ids
- [ ] Exit code = number of failed instances (0 if all succeed)

### Port isolation under load

- [ ] With 3 simultaneous runs, no port collision occurs
- [ ] If port 3100 is already occupied before launch, instances start at 3101
- [ ] Each verify.sh receives the correct PORT for its instance
- [ ] Agents produce code using their assigned port (not hardcoded 3100)
- [ ] After all complete, ports 3100-3102 are freed (no orphaned processes)
- [ ] `lsof -ti:3100 -ti:3101 -ti:3102` returns nothing after cleanup

### Scoring independence

- [ ] Each instance scores independently (one can PASS while another FAILs)
- [ ] A FAIL in instance 2 does not affect instance 1 or 3
- [ ] Each instance has its own events.jsonl with its own score event
- [ ] `score.sh <run_id>` works for each individual run
- [ ] Aggregate pass rate = count(PASS) / count(instances)

### Monitoring during execution

- [ ] `dashboard.sh <run_id> --summary` works while agent is still running
- [ ] Resource snapshots appear every 30s in events.jsonl
- [ ] Dashboard shows partial data (events so far) before agent completes
- [ ] Dashboard does not crash if agent hasn't produced token_update yet

### Fix classification

- [ ] Every finding is classified as Level 0 or Level 2 before applying
- [ ] Level 0 fixes are generalized (work for any target, not just this one)
- [ ] Level 2 fixes don't reference agent-spec paths or concepts
- [ ] `grep -r "agent-spec" target/.claude/` returns nothing after Level 2 fixes
- [ ] Level 0 fixes committed separately from Level 2 fixes
- [ ] Ambiguous findings escalated to user (not guessed)

### Convergence

- [ ] Loop terminates when all N instances PASS in the same depth
- [ ] Loop terminates when depth reaches max_depth (even if still failing)
- [ ] At max_depth, summary shows best results and remaining failures
- [ ] Each depth re-runs from clean state (no leaked state between depths)
- [ ] Sandboxes from depth N are cleaned before depth N+1 starts
- [ ] Ports are freed between depths

### Iteration state isolation

- [ ] Depth N+1 agents read updated `.claude/` from disk (not stale cache)
- [ ] Edits to `configs/tuned/CLAUDE.md` between depths are picked up
- [ ] No events from depth N leak into depth N+1 event logs
- [ ] Run IDs from different depths are distinct (no reuse)
- [ ] Results from all depths are archived (not just final depth)

### Cost tracking across iterations

- [ ] Total cost across all depths is trackable via report.py --all
- [ ] Cost per depth is visible via report.py with run_ids from that depth
- [ ] `--compare` between depth 0 run and final depth run shows cost delta
- [ ] Cost should decrease (or stay flat) as instructions improve
- [ ] If cost increases between depths, that's a signal to investigate

### Handoff

- [ ] Handoff doc includes: depth reached, results table, fixes applied, remaining gaps
- [ ] Handoff doc includes run_ids for every depth (not just final)
- [ ] Handoff doc states whether converged or hit max_depth
- [ ] Fresh session can pick up from handoff without reading prior conversation

### Edge cases

- [ ] `/iterate` with max_depth=1 runs exactly one pass then stops
- [ ] `/iterate` with instances=1 runs one instance per pass (still works)
- [ ] All instances FAIL at depth 0 — loop continues to depth 1 (not crash)
- [ ] One instance hangs (budget exhausted) — other instances still complete
- [ ] Agent produces no files — verify.sh runs but FAIL, archiving handles empty produced/
- [ ] Config file edited to invalid syntax — agent gets invalid instructions but doesn't crash harness
- [ ] Running `/iterate` twice concurrently on same target — port allocation handles it (or rejects)
