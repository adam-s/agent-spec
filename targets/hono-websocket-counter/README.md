# Hono WebSocket Counter

A real-time counter app built with Hono and Bun. Clients connect via WebSocket, send inc/dec commands, and all connected clients receive the updated count.

## Setup

```bash
bun install
```

## Usage

```bash
bun run server.ts
```

Open http://localhost:3100 in multiple browser tabs. Click +/- buttons and watch all tabs update in real-time.

## Testing

```bash
bun test.js
```
