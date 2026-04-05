---
name: token-efficiency
description: Do .claude/ instruction strategies affect tokens-to-correctness?
model: claude-sonnet-4-6
budget: 2.00
port: 3100
---

Six .claude/ instruction strategies tested across three coding challenges of increasing
difficulty. The question: does the content and structure of .claude/ affect how many
tokens an agent needs to produce correct code?

Configs range from a 1-line baseline to multi-file .claude/ directories with rules,
agents, hooks, and skills. Challenges range from trivial single-file tasks (csv-reporter,
sqlite-window-queries) to a multi-step server with WebSockets (hono-websocket-counter).

The easy challenges establish a floor -- all configs should pass, and token differences
reflect instruction overhead. The hard challenge is the discriminator -- where instruction
quality can affect agent decisions, retries, and total token consumption.

Adapted from https://github.com/adam-s/testing-claude-agent with increased repetitions
for statistical confidence.
