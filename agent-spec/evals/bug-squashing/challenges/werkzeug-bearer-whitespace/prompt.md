This workspace contains Werkzeug — a comprehensive WSGI web application library for Python.

There is a bug in how the `WWW-Authenticate` header is generated. When a `WWW-Authenticate` header has no parameters (just the auth scheme, e.g. `Bearer` with no realm or other params), Werkzeug produces `"Bearer "` with a trailing space instead of `"Bearer"`. Some HTTP libraries (like h11) reject headers with trailing whitespace as malformed.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest tests/test_http.py -x -q` to verify your fix.

Do not modify any test files.
