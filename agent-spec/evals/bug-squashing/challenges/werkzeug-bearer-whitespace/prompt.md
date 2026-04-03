This workspace contains Werkzeug — a comprehensive WSGI web application library for Python.

A user reported the following bug:

> As per RFC 9110 (challenge and response), the `WWW-Authenticate` header may omit the realm and other parameters — i.e., the header can contain a single word: the auth-scheme.
>
> For those parameter-less `WWW-Authenticate` headers, Werkzeug leaves a trailing whitespace: `"Bearer "` instead of `"Bearer"`. Some libraries, namely h11, rightfully reject those headers as malformed.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest tests/test_http.py -x -q` to verify your fix.

Do not modify any test files.
