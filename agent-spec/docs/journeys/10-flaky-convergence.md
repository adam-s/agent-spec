# Journey 10: Flaky Convergence

**Goal:** Test how the iteration loop handles non-deterministic results — targets that sometimes pass and sometimes fail with the same config.

**What this exercises:** Statistical robustness of the iteration loop. Does it converge, oscillate, or give up? Does it waste iterations "fixing" things that were just flaky?

## Create Flakiness

### Option A: Budget-edge flakiness

Set the budget just above the cliff found in Journey 8. The agent will sometimes finish in time and sometimes not:

```bash
# If the cliff is at $0.05, set budget to $0.06
python3 scripts/parallel.py csv-reporter --configs baseline --instances 5 \
  --model claude-haiku-4-5-20251001 --budget 0.06
```

Run 5+ instances. If you get a mix of PASS and FAIL, you've found a flaky configuration.

### Option B: Nondeterministic verify.sh

Create a verify.sh that randomly fails 30% of the time:

```bash
# In a target-specific verify.sh override
if [ $((RANDOM % 10)) -lt 3 ]; then
  echo "RESULT: FAIL"
else
  # run real tests
  ...
fi
```

### Option C: Model nondeterminism

Some tasks produce different valid solutions. If verify.sh is strict about format, valid-but-different outputs may fail.

## Run Iteration on a Flaky Target

```bash
/iterate csv-reporter --instances 5 --max-depth 3
```

## What to Watch For

- Does the iterate loop "fix" something that wasn't broken (false positive diagnosis)?
- Does it oscillate — add instruction at depth 1, remove it at depth 2?
- Does it correctly identify flakiness vs real failures?
- Does the pass rate improve, stay flat, or get worse?
- How much money is wasted on flaky runs?

## The Hard Question

The iterate loop's stop condition is "all instances PASS in the same depth." With flakiness, this may never happen. Should the stop condition be "pass rate above threshold" instead? This journey helps answer that.

## Success Criteria

- [ ] Created a reliably flaky configuration (mix of PASS/FAIL)
- [ ] Ran iteration loop against it for 2+ depths
- [ ] Documented whether the loop converges, oscillates, or gives up
- [ ] Identified false positive diagnoses (if any)
- [ ] Proposed changes to stop condition or diagnosis if needed
