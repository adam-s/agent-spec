# Node.js SQLite Project

## Critical Rules

- **NEVER** overwrite test.js — it contains the definitive test suite you must pass
- **NEVER** modify seed.sql — it is the source of truth for the database schema and data
- **ALWAYS** read test.js FIRST before writing queries.js — understand what tests expect
- **ALWAYS** read seed.sql to understand the table schema and sample data
- **ALWAYS** read the prompt to understand the exact JSON output format required

## Implementation

- Write queries.js that creates an in-memory SQLite database, seeds it, and runs window function queries
- Use the better-sqlite3 package (already in package.json)
- Output results as a single JSON.stringify() call matching the expected key names
- Run the tests after writing code: node test.js
