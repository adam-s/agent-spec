You are working inside agent-spec, a test harness that launches Claude agents in sandboxes, scores their output, then improves the `.claude/` instructions based on what went wrong.

A recent evaluation of the `csv-reporter` target **failed**. The run ID is `failed-csv-run`. Your job is to perform one iteration of the improvement loop:

1. **Investigate the failure.** Use the agent-spec dashboard to understand what happened:
   - Run `python3 scripts/dashboard.py failed-csv-run --summary` for an overview
   - Read the `verification_output` event carefully — it contains the test output showing exactly what went wrong

2. **Read the weak config.** The config that was used for this run is at `workspace/weak-config/CLAUDE.md`. Read it and understand why it was insufficient.

3. **Diagnose the root cause.** Write your diagnosis to `diagnosis.md` with these sections:
   - **What happened**: What did the agent produce vs what was expected?
   - **Root cause**: Why did the config fail to prevent this?
   - **General principle**: What category of bug is this? (Don't just describe this specific case — name the pattern.)

4. **Write an improved config.** Create `workspace/improved-config/CLAUDE.md` that fixes the root cause. The improved config should give the agent enough guidance to avoid the failure pattern you identified, without over-specifying (don't just paste the exact answers).

Do NOT run any evaluations or launch any agents. Only investigate, diagnose, and write the improved config.
