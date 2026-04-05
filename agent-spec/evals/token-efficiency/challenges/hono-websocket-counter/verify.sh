#!/bin/bash
PORT=${VERIFY_PORT:-${PORT:-3100}}

# Find the server file
SERVER=""
for f in server.ts index.ts server.js index.js src/index.ts src/server.ts; do
    if [ -f "$f" ]; then
        SERVER="$f"
        break
    fi
done

if [ -z "$SERVER" ]; then
    echo "No server file found"
    echo "RESULT: FAIL"
    exit 0
fi

# Stop anything on our port
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
sleep 1

# Start server in background
bun run "$SERVER" &
SERVER_PID=$!
sleep 3

# Check server is running
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "Server failed to start"
    echo "RESULT: FAIL"
    exit 0
fi

# Run tests
PORT=$PORT bun test.js 2>&1
EXIT=$?

# Cleanup
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true

if [ $EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
