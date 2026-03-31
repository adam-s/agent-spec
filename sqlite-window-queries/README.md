# SQLite Window Queries

A Node.js app that creates an orders database and runs 5 SQL window function queries.

## Setup

```bash
npm install
```

## Usage

```bash
node queries.js
```

## Queries

1. **Running Total** — Cumulative sum per customer ordered by date
2. **Rank Customers** — DENSE_RANK by total spend descending
3. **Previous Order** — LAG to get each customer's prior order amount
4. **Moving Average** — 3-order moving average per customer
5. **Percent of Total** — Each order as percentage of customer's total spend

## Testing

```bash
node test.js
```
