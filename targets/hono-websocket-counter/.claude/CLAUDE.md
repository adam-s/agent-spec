# Hono + Bun Project

Build web applications with Hono framework on Bun runtime.

## Rules

- Read test.js FIRST before writing server.ts — understand what tests expect
- Read any JSON data files to understand the data structure
- Read the prompt FIRST to find the port number — parse it from the task description
- If a `wireframe.png` exists in the project root, read it and match its visual style
- test.js and data files are protected by permissions — you cannot overwrite them

## Implementation

- Write server.ts that serves HTML at GET / on the port specified in the task prompt
- Use inline CSS and inline JavaScript in the HTML response
- Embed data from JSON files directly in the served page
- Use Bun.serve() with a fetch handler that upgrades WebSocket at /ws if needed
- Run the tests after writing code: bun test.js

## Skills

See @.claude/skills/build/SKILL.md for the full test-driven development process.
