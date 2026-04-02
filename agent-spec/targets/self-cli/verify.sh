#!/usr/bin/env bash
set -euo pipefail

PASS=true

check() {
  if [ "$1" = "true" ]; then
    echo "PASS: $2"
  else
    echo "FAIL: $2"
    PASS=false
  fi
}

# 1. list output exists and contains target names
if [ -f cli-output/list.txt ]; then
  check true "list.txt exists"
  grep -q "csv-reporter" cli-output/list.txt && check true "list.txt contains csv-reporter" || check false "list.txt missing csv-reporter"
  grep -q "self-onboard" cli-output/list.txt && check true "list.txt contains self-onboard" || check false "list.txt missing self-onboard"
else
  check false "list.txt exists"
fi

# 2. monitor output exists and contains status table
if [ -f cli-output/monitor.txt ]; then
  check true "monitor.txt exists"
  grep -q "SYSTEM STATUS" cli-output/monitor.txt && check true "monitor.txt contains SYSTEM STATUS" || check false "monitor.txt missing SYSTEM STATUS"
  grep -qi "disk\|memory\|cpu" cli-output/monitor.txt && check true "monitor.txt contains resource metrics" || check false "monitor.txt missing resource metrics"
else
  check false "monitor.txt exists"
fi

# 3. run help output exists and contains expected flags
if [ -f cli-output/run-help.txt ]; then
  check true "run-help.txt exists"
  grep -q "target" cli-output/run-help.txt && check true "run-help.txt contains target" || check false "run-help.txt missing target"
  grep -q "\-\-model" cli-output/run-help.txt && check true "run-help.txt contains --model" || check false "run-help.txt missing --model"
else
  check false "run-help.txt exists"
fi

# 4. report help output exists
if [ -f cli-output/report-help.txt ]; then
  check true "report-help.txt exists"
  grep -q "\-\-all" cli-output/report-help.txt && check true "report-help.txt contains --all" || check false "report-help.txt missing --all"
else
  check false "report-help.txt exists"
fi

if [ "$PASS" = true ]; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
