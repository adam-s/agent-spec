import { execSync } from "child_process";

const output = execSync("node queries.js", { encoding: "utf8" });
const results = JSON.parse(output);
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

// 1. Running total: 100 rows, spot-check customer 1's last running total
check(
  "running_total has 100 rows",
  results.running_total.length === 100
);
const c1_last = results.running_total.filter((r) => r.customer_id === 1);
const c1_total = c1_last[c1_last.length - 1].running_total;
check(
  "customer 1 running total sums to 1523",
  c1_total === 1523
);

// 2. Rank: 10 customers, top customer ranked 1
check(
  "rank_customers has 10 rows",
  results.rank_customers.length === 10
);
check(
  "top-ranked customer total_spend is highest",
  results.rank_customers[0].rank === 1 &&
    results.rank_customers[0].total_spend >= results.rank_customers[1].total_spend
);

// 3. LAG: first order per customer has null prev_amount
const c1_first = results.prev_order.find((r) => r.customer_id === 1);
check(
  "first order has null prev_amount",
  c1_first.prev_amount === null
);
check(
  "prev_order has 100 rows",
  results.prev_order.length === 100
);

// 4. Moving average: 100 rows, values are numbers
check(
  "moving_avg has 100 rows",
  results.moving_avg.length === 100
);
check(
  "moving_avg values are numbers",
  results.moving_avg.every((r) => typeof r.moving_avg === "number")
);

// 5. Percent of total: 100 rows, each customer's percentages sum to ~100
check(
  "pct_of_total has 100 rows",
  results.pct_of_total.length === 100
);
const c1_pcts = results.pct_of_total
  .filter((r) => r.customer_id === 1)
  .reduce((sum, r) => sum + r.pct_of_total, 0);
check(
  "customer 1 percentages sum to ~100",
  Math.abs(c1_pcts - 100) < 1
);

console.log(`\n${passed}/${passed + failed} tests passed`);
if (failed > 0) process.exit(1);
