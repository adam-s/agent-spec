# Journey 9: Parallel Stress Test

**Goal:** Push parallel execution to its limits — max instances, port exhaustion, concurrent targets, and cleanup reliability.

**What this exercises:** The harness infrastructure under load. Port allocation, sandbox isolation, cleanup, and monitoring at scale.

## Escalation

### Level 1: Max instances on one target (11 = port limit)

```bash
python3 scripts/parallel.py csv-reporter --configs baseline --instances 11 \
  --model claude-haiku-4-5-20251001 --budget 0.25
```

Watch for: port exhaustion, sandbox collisions, cleanup failures.

### Level 2: Exceed port limit (should fail gracefully)

```bash
python3 scripts/parallel.py csv-reporter --configs baseline --instances 12 \
  --model claude-haiku-4-5-20251001 --budget 0.25
```

Should error with a clear message, not crash.

### Level 3: Multiple targets simultaneously

In two terminals:

```bash
# Terminal 1
python3 scripts/parallel.py csv-reporter --configs baseline --instances 5 \
  --model claude-haiku-4-5-20251001 --budget 0.25

# Terminal 2
python3 scripts/parallel.py sqlite-window-queries --configs baseline --instances 5 \
  --model claude-haiku-4-5-20251001 --budget 0.25
```

Watch for: port collisions between the two runs.

### Level 4: Full config matrix

```bash
python3 scripts/parallel.py csv-reporter \
  --configs baseline,token-efficient,drona23 \
  --models claude-haiku-4-5-20251001,claude-sonnet-4-6 \
  --budget 0.50
```

This creates 3 configs x 2 models = 6 instances. All should get unique ports and sandboxes.

## After Each Level

```bash
# Check no orphaned processes
lsof -ti:3100-3110 2>/dev/null | wc -l   # should be 0

# Check no orphaned sandboxes
ls /tmp/claude/agent-spec-* 2>/dev/null   # should be empty

# Check parallel dashboard
python3 scripts/dashboard.py --parallel <parallel_id>
```

## Success Criteria

- [ ] 11 instances run successfully (max port range)
- [ ] 12 instances rejected with clear error
- [ ] Concurrent runs on different targets don't collide
- [ ] Full config x model matrix produces correct grouped report
- [ ] No orphaned processes or sandboxes after any level
- [ ] Parallel dashboard renders correctly at each scale
