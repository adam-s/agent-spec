This workspace contains the Arrow library — a Python library for working with dates, times, and timestamps.

There is a bug in the `humanize` method. When computing relative time descriptions, 16 days in the future is reported as "in a month" instead of "in 2 weeks." For example:

- January 9 to January 24 (15 days) → "in 2 weeks" (correct)
- January 9 to January 25 (16 days) → "in a month" (wrong — should be "in 2 weeks")

The bug is in how partial month rounding interacts with the weeks granularity. A 16-day difference within the same month should not be reported as a month.

However, actual calendar-month differences should still work correctly:
- February 8 to March 8 (28 days, `shift(months=1)`) → "in a month" (correct)

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the existing tests with `.venv/bin/python3 -m pytest tests/` to verify your fix doesn't break anything.

Do not modify any test files.
