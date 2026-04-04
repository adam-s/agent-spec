This workspace contains marshmallow — a Python library for object serialization and deserialization.

A user reported the following bug:

> The `Email` validator rejects valid email addresses that use Internationalized Domain Names (IDNs). For example, `user@münchen.de` and `user@例え.jp` are valid email addresses but marshmallow's `Email` validator rejects them.
>
> The `URL` validator was recently updated to accept IDNs, but the `Email` validator still doesn't support them.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest tests/test_validate.py -x -q` to verify your fix.

Do not modify any test files.
