You are working inside agent-spec, a test harness for `.claude/` agents.

Your task: check the system health and write a report.

1. Run `python3 scripts/system_monitor.py` to get the current system status
2. Write a health report to `health-report.md` with these sections:
   - **Disk**: current usage, free space, status (OK/WARNING/CRITICAL)
   - **Memory**: current usage, free space, status
   - **CPU**: current usage, core count, status
   - **Agent Safety**: based on the resource status, is it safe to launch agents? Why or why not?

Include the actual numbers from the monitor output in your report.
