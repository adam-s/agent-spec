# Hono + Bun Project

Build web applications with Hono framework on Bun runtime.

## Critical Rules

- **NEVER** overwrite test.js — it contains the definitive test suite you must pass
- **NEVER** modify mock data JSON files — they are the source of truth
- **ALWAYS** read test.js FIRST before writing server.ts — understand what tests expect
- **ALWAYS** read any JSON data files to understand the data structure
- **ALWAYS** read the prompt FIRST to find the port number — parse it from the task description

## Implementation

- Write server.ts that serves HTML at GET / on the port specified in the task prompt
- Use inline CSS and inline JavaScript in the HTML response
- Embed data from JSON files directly in the served page
- Use Bun.serve() with a fetch handler that upgrades WebSocket at /ws if needed
- Run the tests after writing code: bun test.js
