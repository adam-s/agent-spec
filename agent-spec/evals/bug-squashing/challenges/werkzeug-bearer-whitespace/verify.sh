#!/bin/bash
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -e ".[dev]" --quiet 2>/dev/null

# Run the relevant test file
.venv/bin/python3 -m pytest tests/test_http.py -x -q 2>&1
TESTS_EXIT=$?

# Reproduction check
REPRO=$(.venv/bin/python3 -c "
from werkzeug.datastructures import WWWAuthenticate

# Bearer with no params should not have trailing whitespace
auth = WWWAuthenticate('bearer')
header = auth.to_header()
print(f'Header: [{header}]')

if header != header.strip():
    print('BUG: trailing whitespace in header')
    exit(1)
if header.lower() != 'bearer':
    print(f'BUG: unexpected header value: {header}')
    exit(1)
print('Reproduction checks passed')
" 2>&1)
REPRO_EXIT=$?

echo "$REPRO"

if [ $TESTS_EXIT -eq 0 ] && [ $REPRO_EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
