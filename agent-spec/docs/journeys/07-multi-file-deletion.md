# Journey 7: Multi-File Deletion Stress Test

**Goal:** Delete MORE files from targets before the agent runs — forcing it to reconstruct not just the deliverable but supporting infrastructure too.

**What this exercises:** Agent resilience when context is stripped away. Can it infer schema from tests? Can it recreate build files? How much can you delete before it breaks?

## Escalation Ladder

Run each level. When the agent starts failing, you've found the capability boundary.

### Level 1: Delete deliverable only (current default)

This is what targets already do. Baseline — should pass.

```bash
python3 scripts/run_eval.py csv-reporter baseline --model claude-haiku-4-5-20251001 --budget 0.50
```

### Level 2: Delete deliverable + test file

The agent must infer what to build from the prompt alone, without seeing test expectations.

Temporarily edit `targets/csv-reporter/target.yaml`:
```yaml
delete_before_run:
  - report.py
  - test.py
```

```bash
python3 scripts/run_eval.py csv-reporter baseline --model claude-haiku-4-5-20251001 --budget 0.50
```

### Level 3: Delete deliverable + test + data

The agent must generate both the code AND understand what data format to expect.

```yaml
delete_before_run:
  - report.py
  - test.py
  - data/sales.csv
```

### Level 4: Delete everything except prompt

Nuclear option — only the prompt and verify.sh survive.

```yaml
delete_before_run:
  - report.py
  - test.py
  - data/
```

### For hono-websocket-counter

```yaml
# Level 2
delete_before_run:
  - server.ts
  - test.js

# Level 3
delete_before_run:
  - server.ts
  - test.js
  - package.json
```

### For sqlite-window-queries

```yaml
# Level 2
delete_before_run:
  - queries.js
  - test.js

# Level 3
delete_before_run:
  - queries.js
  - test.js
  - seed.sql
```

## Known Results (2026-04, haiku + baseline)

| Target | Level 1 (deliverable) | Level 2 (+test) | Level 3 (+data/config) |
|--------|----------------------|-----------------|----------------------|
| csv-reporter | PASS | FAIL (test.py output format mismatch) | untested |
| sqlite-window-queries | PASS | N/A (verify.sh crashes) | untested |
| hono-websocket-counter | PASS | untested | untested |

**Key insight:** Level 2 fails because the agent recreates test files with different output format than verify.sh expects. The coupling between test.py/test.js output format and verify.sh's grep patterns is the weak point.

## What to Watch For

- At what level does each target start failing?
- Does the agent try to recreate deleted files or work around them?
- Do instruction improvements (Level 2 fixes) help survive higher deletion levels?
- Is there a config that makes agents more resilient to missing context?

## Success Criteria

- [ ] Found the deletion level where each target breaks
- [ ] Documented what the agent gets wrong at each failure level
- [ ] Attempted iteration to push the boundary one level higher
- [ ] Updated target.yaml with the hardest deletion level that reliably passes
