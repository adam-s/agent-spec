import Database from "better-sqlite3";
import { readFileSync } from "fs";

const db = new Database(":memory:");
db.exec(readFileSync("seed.sql", "utf8"));

const results = {};

// 1. Running total per customer
results.running_total = db
  .prepare(
    `SELECT id, customer_id, order_date, amount,
            SUM(amount) OVER (PARTITION BY customer_id ORDER BY order_date, id
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
     FROM orders ORDER BY customer_id, order_date, id`
  )
  .all();

// 2. Rank customers by total spend
results.rank_customers = db
  .prepare(
    `SELECT customer_id, SUM(amount) AS total_spend,
            DENSE_RANK() OVER (ORDER BY SUM(amount) DESC) AS rank
     FROM orders GROUP BY customer_id ORDER BY rank`
  )
  .all();

// 3. Previous order amount (LAG)
results.prev_order = db
  .prepare(
    `SELECT id, customer_id, order_date, amount,
            LAG(amount) OVER (PARTITION BY customer_id ORDER BY order_date, id) AS prev_amount
     FROM orders ORDER BY customer_id, order_date, id`
  )
  .all();

// 4. Moving average (3-order window)
results.moving_avg = db
  .prepare(
    `SELECT id, customer_id, order_date, amount,
            ROUND(AVG(amount) OVER (PARTITION BY customer_id ORDER BY order_date, id
                                    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS moving_avg
     FROM orders ORDER BY customer_id, order_date, id`
  )
  .all();

// 5. Percent of customer total
results.pct_of_total = db
  .prepare(
    `SELECT id, customer_id, order_date, amount,
            ROUND(amount * 100.0 / SUM(amount) OVER (PARTITION BY customer_id), 2) AS pct_of_total
     FROM orders ORDER BY customer_id, order_date, id`
  )
  .all();

db.close();
console.log(JSON.stringify(results, null, 2));
