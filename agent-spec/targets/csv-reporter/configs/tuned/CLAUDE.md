# Python Data Analysis Project

## What to Build

You need to create two files:
1. `report.py` — reads CSV data and prints statistics to stdout
2. `test.py` — validates report.py output

## Rules

- If test.py already exists, read it first and match its expectations exactly
- If test.py does NOT exist, create it using this exact format:
  - Run `report.py` via subprocess and capture stdout
  - For each check, print `  PASS: <description>` or `  FAIL: <description>`
  - Final line must be exactly: `{passed}/{total} tests passed`
  - This output format is required by the verification harness
- Use only Python standard library (csv, collections, etc.)
- Read data/sales.csv to understand column names and data types
- Run python3 test.py after writing both files
