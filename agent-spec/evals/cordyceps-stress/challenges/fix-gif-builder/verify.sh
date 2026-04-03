#!/bin/bash
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -r requirements.txt --quiet 2>/dev/null

.venv/bin/python3 test_gif.py 2>&1
EXIT=$?

if [ $EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
