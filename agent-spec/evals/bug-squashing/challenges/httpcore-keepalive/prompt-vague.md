This workspace contains httpcore — a minimal HTTP client library for Python, used internally by httpx.

Users report that connections in the connection pool are being dropped unexpectedly. The issue seems to affect keep-alive behavior.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest tests/ -x -q` to verify your fix.

Do not modify any test files.
