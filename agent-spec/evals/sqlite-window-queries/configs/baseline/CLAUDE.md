# Node.js SQLite Project

## Rules

- Read test.js FIRST before writing queries.js — understand what tests expect
- Read seed.sql to understand the table schema and sample data
- Read the prompt to understand the exact JSON output format required
- test.js and seed.sql are protected by permissions — you cannot overwrite them

## Implementation

- Write queries.js that creates an in-memory SQLite database, seeds it, and runs window function queries
- Use the better-sqlite3 package (already in package.json)
- Output results as a single JSON.stringify() call matching the expected key names
- Run the tests after writing code: node test.js
