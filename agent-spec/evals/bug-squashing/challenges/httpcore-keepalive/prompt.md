This workspace contains httpcore — a minimal HTTP client library for Python, used internally by httpx.

There is a bug in the connection pool implementation. Idle connections are being dropped from the pool even when the `max_keepalive_connections` limit has not been reached. This happens because the keepalive check incorrectly compares the setting against the total number of connections instead of only the idle ones.

The bug affects both sync and async connection pools.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest tests/ -x -q` to verify your fix.

Do not modify any test files.
