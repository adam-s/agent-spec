Write server.ts — a Hono app on Bun (port 3100) that:

1. Serves an HTML page at GET / with a counter display and +/- buttons
2. Accepts WebSocket connections at /ws
3. Handles "inc" and "dec" string messages to increment/decrement a shared counter
4. Broadcasts the updated count to ALL connected clients as JSON: {"count": N}

Run bun test.js to verify your work passes all tests.
