import { Hono } from "hono";

const app = new Hono();
let count = 0;
const clients = new Set<any>();

const html = `<!DOCTYPE html>
<html><head><title>Counter</title></head>
<body>
  <h1 id="count">0</h1>
  <button onclick="ws.send('inc')">+</button>
  <button onclick="ws.send('dec')">-</button>
  <script>
    const ws = new WebSocket('ws://' + location.host + '/ws');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      document.getElementById('count').textContent = data.count;
    };
  </script>
</body></html>`;

app.get("/", (c) => c.html(html));

const server = Bun.serve({
  port: 3100,
  fetch(req, server) {
    const url = new URL(req.url);
    if (url.pathname === "/ws") {
      if (server.upgrade(req)) return;
      return new Response("Upgrade failed", { status: 400 });
    }
    return app.fetch(req);
  },
  websocket: {
    open(ws) {
      clients.add(ws);
      ws.send(JSON.stringify({ count }));
    },
    message(ws, message) {
      if (message === "inc") count++;
      else if (message === "dec") count--;
      ws.send(JSON.stringify({ count }));
      setTimeout(() => {
        for (const client of clients) {
          if (client !== ws) client.send(JSON.stringify({ count }));
        }
      }, 50);
    },
    close(ws) {
      clients.delete(ws);
    },
  },
});

console.log(`Started server: http://localhost:${server.port}`);
