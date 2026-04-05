---
name: build
description: Test-driven development of a Hono/Bun WebSocket application. Read requirements, read tests, build server, verify, iterate until all tests pass.
---

# Build

## Process

1. **Read the task prompt** — understand what to build and which port to use
2. **Read test.js** — this is the definitive specification. Every test must pass. Do not modify test.js.
3. **Read wireframe.png** (if present) — this is the visual target. Match its layout, typography, and component patterns in your HTML/CSS.
4. **Read any data files** (JSON, etc.) — these are source-of-truth data. Do not modify them.
5. **Write server.ts** — implement the server using Bun.serve() with Hono
6. **Run tests** — `bun test.js` (start the server first if tests don't start it)
7. **If tests fail** — read the failure output, fix the specific issue, re-run. Do not rewrite from scratch unless the approach is fundamentally wrong.
8. **If wireframe provided** — after tests pass, compare your served HTML to the wireframe. Adjust inline CSS to match layout and visual style.

## Constraints

- Use `Bun.serve()` with a fetch handler
- Serve HTML at GET / with inline CSS and inline JavaScript
- Use the port from the task prompt (check `process.env.PORT` fallback)
- WebSocket upgrade at `/ws` if tests expect it
- Never overwrite test.js
- Never modify data files
