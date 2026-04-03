#!/bin/bash
# Verify csv-reporter: run the test suite the agent was given.
# Uses _apc.py (injected by invoke.py) to emit debug events into events.jsonl.

python3 -c "from _apc import debug; debug('verify', 'running csv-reporter test suite')" 2>/dev/null

python3 test.py 2>&1
EXIT=$?

python3 -c "from _apc import debug; debug('verify', 'tests complete', {'exit_code': $EXIT})" 2>/dev/null

if [ $EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
