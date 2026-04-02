# agent-spec — System Health Check

You are inside agent-spec, a test harness for `.claude/` agents. Your task is to check system health and write a report.

## Tools available

- `python3 scripts/system_monitor.py` — prints a status table with disk, memory, CPU, and agent-spec process info
- Status levels: OK, WARNING, CRITICAL
- Thresholds: disk <15GB = CRITICAL, <30GB = WARNING; memory >95% = CRITICAL, >85% = WARNING; CPU >80% = WARNING

## Output format

Write `health-report.md` with sections for Disk, Memory, CPU, and Agent Safety. Include the actual numbers from the monitor output. State whether it is safe to launch agents based on the overall status.
