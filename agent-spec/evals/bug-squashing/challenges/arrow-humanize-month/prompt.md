This workspace contains Arrow — a Python library for working with dates, times, and timestamps.

A user reported the following bug:

> It seems that the intervals being used for the various thresholds for `humanize` are a bit strange. As of today, January 9 2026, there are two events, one on January 24 which appears as "in two weeks" and one on January 25 which appears as "in a month."
>
> 15 days (the 24th) is indeed about two weeks away, but 16 days (the 25th) is certainly not a month away — if anything it's also closest to around two weeks. It isn't even closer to three weeks than two, let alone a month.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest tests/ -x -q` to verify your fix.

Do not modify any test files.
