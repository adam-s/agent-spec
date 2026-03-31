#!/usr/bin/env bash
set -euo pipefail

# Find and start the server
SERVER_FILE=""
for f in server.ts index.ts server.js index.js; do
  [[ -f "$f" ]] && SERVER_FILE="$f" && break
done

if [[ -z "$SERVER_FILE" ]]; then
  echo "No server file found"
  echo "RESULT: FAIL"
  exit 0
fi

# Stop anything on port 3100
lsof -ti:3100 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

# Start server in background
bun run "$SERVER_FILE" &
SERVER_PID=$!
sleep 3

# Run tests
set +e
OUTPUT=$(bun test.js 2>&1)
TEST_EXIT=$?
set -e

# Stop server
kill "$SERVER_PID" 2>/dev/null || true
lsof -ti:3100 2>/dev/null | xargs kill -9 2>/dev/null || true

echo "$OUTPUT"
if [[ $TEST_EXIT -eq 0 ]] && echo "$OUTPUT" | grep -q "tests passed"; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
