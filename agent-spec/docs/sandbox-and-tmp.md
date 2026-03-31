# Sandbox and Temp Directories

## Decision

Use `/tmp/claude/agent-spec-{uuid}/` for sandbox copies, not a local `tmp/` folder.

## Why

A tested agent runs as a Claude Code process with a working directory. If the sandbox lives inside agent-spec, the agent can see the harness, configs, and other targets. `/tmp` provides real isolation.

## Claude Code Sandbox Behavior

- Sandbox mode sets `TMPDIR=/tmp/claude` and allowlists it for writes
- `/tmp/claude` is not auto-created on startup (bug #36759) — create it before running evals
- Outside sandbox mode, `/tmp` is freely accessible
- The working directory is always readable/writable

## Workaround

```bash
mkdir -p /tmp/claude
```

Run this before any evaluation. The harness scripts should do it automatically.
