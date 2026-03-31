#!/usr/bin/env bash
set -euo pipefail
npm install --silent 2>/dev/null || true
OUTPUT=$(node test.js 2>&1)
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "10/10 tests passed"; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
