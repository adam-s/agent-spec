#!/usr/bin/env bash
set -euo pipefail
OUTPUT=$(python3 test.py 2>&1)
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "5/5 tests passed"; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
