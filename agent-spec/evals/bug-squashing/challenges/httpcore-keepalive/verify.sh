#!/bin/bash
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -e ".[trio,anyio]" --quiet 2>/dev/null
.venv/bin/pip install pytest pytest-httpbin trustme --quiet 2>/dev/null

.venv/bin/python3 -m pytest tests/ -x -q 2>&1
EXIT=$?

if [ $EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
