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

# 1. health-report.md exists and is substantial
if [ -f health-report.md ]; then
  check true "health-report.md exists"
  CHARS=$(wc -c < health-report.md)
  [ "$CHARS" -gt 100 ] && check true "health-report.md is substantial (${CHARS} chars)" || check false "health-report.md too short (${CHARS} chars)"
else
  check false "health-report.md exists"
fi

# 2. Contains disk, memory, CPU sections
if [ -f health-report.md ]; then
  grep -qi "disk" health-report.md && check true "mentions disk" || check false "missing disk section"
  grep -qi "memory\|mem\|ram" health-report.md && check true "mentions memory" || check false "missing memory section"
  grep -qi "cpu" health-report.md && check true "mentions CPU" || check false "missing CPU section"
fi

# 3. Contains actual numbers (GB, %, cores)
if [ -f health-report.md ]; then
  grep -qE "[0-9]+.*GB|[0-9]+%" health-report.md && check true "contains actual metrics" || check false "missing actual metrics (no GB or % values)"
fi

# 4. Makes a safety assessment
if [ -f health-report.md ]; then
  grep -qi "safe\|ok\|warning\|critical\|proceed\|launch" health-report.md && check true "includes safety assessment" || check false "missing safety assessment"
fi

if [ "$PASS" = true ]; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
