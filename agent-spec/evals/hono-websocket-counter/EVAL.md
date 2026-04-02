---
name: hono-websocket-counter
description: Test agent's ability to build a real-time WebSocket server with Hono/Bun
source: ../../../hono-websocket-counter
model: claude-haiku-4-5-20251001
budget: 1.00
port: 3100
delete:
  - server.ts
setup:
  - bun install
reference:
  type: test-file
  file: test.js
  pass_pattern: "tests passed"
---

Write server.ts — a Hono app on Bun (port __PORT__) that:

1. Serves an HTML page at GET / with a counter display and +/- buttons
2. Accepts WebSocket connections at /ws
3. Handles "inc" and "dec" string messages to increment/decrement a shared counter
4. Broadcasts the updated count to ALL connected clients as JSON: {"count": N}

Run bun test.js to verify your work passes all tests.
