This workspace contains the Arrow library — a Python library for working with dates, times, and timestamps.

Users are reporting that the `humanize` method sometimes produces incorrect relative time descriptions. The intervals seem wrong — differences that should show one granularity are being reported at a different one.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the existing tests with `.venv/bin/python3 -m pytest tests/ -x -q` to verify your fix doesn't break anything.

Do not modify any test files.
