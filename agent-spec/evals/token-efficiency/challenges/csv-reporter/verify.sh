#!/bin/bash
python3 test.py 2>&1
EXIT=$?
if [ $EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
