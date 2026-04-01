#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-3100}"

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

# Stop anything on assigned port
lsof -ti:"$PORT" 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

# Start server in background
PORT="$PORT" bun run "$SERVER_FILE" &
SERVER_PID=$!

# Wait for server to be ready (up to 10 seconds)
for attempt in $(seq 1 20); do
  if curl -sf "http://localhost:$PORT/" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

# Run tests
set +e
OUTPUT=$(PORT="$PORT" bun test.js 2>&1)
TEST_EXIT=$?
set -e

# Stop server
kill "$SERVER_PID" 2>/dev/null || true
lsof -ti:"$PORT" 2>/dev/null | xargs kill -9 2>/dev/null || true

echo "$OUTPUT"
if [[ $TEST_EXIT -eq 0 ]] && echo "$OUTPUT" | grep -q "tests passed"; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
