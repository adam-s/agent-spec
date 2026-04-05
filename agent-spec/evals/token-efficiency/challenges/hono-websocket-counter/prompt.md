Build a Hono server on Bun (port __PORT__) in server.ts. Serve a single HTML page at / with a counter display and +/- buttons. Use WebSockets: clicking a button sends 'inc' or 'dec', server maintains shared count, broadcasts current count to ALL connected clients as JSON {"count": N}. Counter starts at 0. WebSocket endpoint at /ws.

A test file is provided at test.js. Start your server, then run `PORT=__PORT__ bun test.js` in a separate process. All tests must pass. Keep fixing your code until all tests pass.
