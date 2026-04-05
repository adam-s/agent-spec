const PORT = process.env.PORT || 3100;
const BASE = `http://localhost:${PORT}`;
let passed = 0;
let failed = 0;

function check(name, condition) {
  if (condition) {
    console.log(`  PASS: ${name}`);
    passed++;
  } else {
    console.log(`  FAIL: ${name}`);
    failed++;
  }
}

// Test 1: HTTP serves HTML with counter
const res = await fetch(BASE);
check("GET / returns 200", res.status === 200);
const html = await res.text();
check("HTML has counter and buttons", html.includes("count") && html.includes("button"));

// Test 2: WebSocket inc/dec/broadcast
const timeout = setTimeout(() => {
  console.log("\n  FAIL: WebSocket tests timed out");
  process.exit(1);
}, 5000);

await new Promise((resolve) => {
  const ws1 = new WebSocket(`ws://localhost:${PORT}/ws`);
  const ws2 = new WebSocket(`ws://localhost:${PORT}/ws`);
  let ws1_msgs = 0;
  let ws2_msgs = 0;

  ws1.onmessage = (e) => {
    const data = JSON.parse(e.data);
    ws1_msgs++;
    if (ws1_msgs === 1) {
      // Initial state
      if (ws2_msgs >= 1) ws1.send("inc");
    } else if (ws1_msgs === 2) {
      // ws1 sent inc, this is the sender response
      check("inc command increments count", data.count === 1);
    } else if (ws1_msgs === 3) {
      // ws2 sent dec, this is broadcast to ws1
      check("dec broadcast reaches other client", data.count === 0);
      ws1.close();
      ws2.close();
      resolve();
    }
  };

  ws2.onmessage = (e) => {
    const data = JSON.parse(e.data);
    ws2_msgs++;
    if (ws2_msgs === 1) {
      // Initial state
      if (ws1_msgs >= 1) ws1.send("inc");
    } else if (ws2_msgs === 2) {
      // ws1 sent inc, this is broadcast to ws2
      check("broadcast reaches other client", data.count === 1);
      ws2.send("dec");
    } else if (ws2_msgs === 3) {
      // ws2 sent dec, this is sender response
      check("dec command decrements count", data.count === 0);
    }
  };
});

clearTimeout(timeout);
console.log(`\n${passed}/${passed + failed} tests passed`);
if (failed > 0) process.exit(1);
