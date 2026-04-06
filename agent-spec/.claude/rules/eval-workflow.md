# Eval Workflow

## Save baselines after every run

After every eval run completes, save the results as a baseline:

```bash
python3 scripts/report.py --baseline save <run-id>
```

Do this for each run in the batch. Baselines enable regression detection on future runs — without them, there's nothing to compare against.

When re-running an eval after changes (e.g., editing a skill, modifying a config), check against the saved baseline:

```bash
python3 scripts/report.py --baseline check <new-run-id>
```

## A new skill eval is not done until it catches a regression

Building the directory structure, writing prompts, and writing verify.sh that *could* detect failures is not enough. You must prove the eval works end-to-end:

1. Run the eval with the original skill — expect PASS, save baselines
2. Make a deliberate breaking change to the skill in the config (remove guidance the verify script depends on)
3. Re-run the eval
4. Check against baseline — at least one challenge must report a regression (PASS→FAIL)
5. Restore the original skill from `submodules/skills/`

If step 4 doesn't produce a regression, the eval doesn't work. The skill is being ignored, the prompt gives away the answer, or verify.sh doesn't actually depend on what the skill teaches. Diagnose before claiming the eval is ready.

The agent that builds the eval is the agent that proves it. Do not hand the proof off to a future chat — without proof, the eval is unverified scaffolding.

See @.claude/reference/operational-workflow.md for the full set of workflow patterns.
