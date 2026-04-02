---
name: csv-reporter
description: Test agent's ability to write a Python data analysis script from a test file
source: ../../../csv-reporter
model: claude-haiku-4-5-20251001
budget: 1.00
delete:
  - report.py
  - test.py
reference:
  type: test-file
  file: test.py
  pass_pattern: "5/5 tests passed"
task_context:
  output_contract: "{passed}/{total} tests passed"
  required_reads:
    - test.py
    - data/sales.csv
  protected_files:
    - data/*
---

Write report.py that reads data/sales.csv and prints these 5 statistics:

1. Total Revenue (format: $X.XX)
2. Top 3 Products by Units Sold (format: Name (units), Name (units), Name (units))
3. Revenue by Region in descending order (format: Region ($X.XX))
4. Highest Revenue Month (format: YYYY-MM ($X.XX))
5. Highest Average Order Value by Product (format: Name ($X.XX))

Run python3 test.py to verify your work passes all tests.
