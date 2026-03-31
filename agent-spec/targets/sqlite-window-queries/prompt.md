Write queries.js that creates an in-memory SQLite database from seed.sql and runs 5 window function queries, printing the results as JSON:

1. running_total — SUM(amount) OVER (PARTITION BY customer_id ORDER BY order_date) with running total per customer
2. rank_customers — DENSE_RANK customers by total spend descending
3. prev_order — LAG(amount) to get each customer's previous order amount
4. moving_avg — 3-order moving average per customer (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
5. pct_of_total — Each order as percentage of customer's total spend

Output format: JSON.stringify({running_total: [...], rank_customers: [...], prev_order: [...], moving_avg: [...], pct_of_total: [...]})

Run node test.js to verify your work passes all tests.
