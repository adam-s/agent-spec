#!/usr/bin/env bash
set -euo pipefail

# Check that the agent created a valid target structure
PASS=true

check() {
  if [ "$1" = "true" ]; then
    echo "PASS: $2"
  else
    echo "FAIL: $2"
    PASS=false
  fi
}

# 1. target.yaml exists and has required fields
if [ -f targets/sample-app/target.yaml ]; then
  check true "target.yaml exists"
  grep -q "source:" targets/sample-app/target.yaml && check true "target.yaml has source field" || check false "target.yaml missing source field"
  grep -q "verify:" targets/sample-app/target.yaml && check true "target.yaml has verify field" || check false "target.yaml missing verify field"
else
  check false "target.yaml exists"
fi

# 2. prompt.md exists and is non-empty
if [ -f targets/sample-app/prompt.md ] && [ -s targets/sample-app/prompt.md ]; then
  check true "prompt.md exists and is non-empty"
else
  check false "prompt.md exists and is non-empty"
fi

# 3. verify.sh exists and is executable
if [ -f targets/sample-app/verify.sh ]; then
  check true "verify.sh exists"
  if [ -x targets/sample-app/verify.sh ]; then
    check true "verify.sh is executable"
  else
    check false "verify.sh is executable"
  fi
  # Check it references the test output pattern
  grep -q "4/4 tests passed" targets/sample-app/verify.sh && check true "verify.sh checks for test output" || check false "verify.sh checks for test output"
  # Check it prints RESULT
  grep -q "RESULT:" targets/sample-app/verify.sh && check true "verify.sh prints RESULT" || check false "verify.sh prints RESULT"
else
  check false "verify.sh exists"
fi

# 4. Baseline config exists
if [ -f targets/sample-app/configs/baseline/CLAUDE.md ]; then
  check true "configs/baseline/CLAUDE.md exists"
else
  check false "configs/baseline/CLAUDE.md exists"
fi

# 5. cli.py list shows sample-app
OUTPUT=$(python3 scripts/cli.py list 2>&1)
if echo "$OUTPUT" | grep -q "sample-app"; then
  check true "agent-spec list shows sample-app"
else
  check false "agent-spec list shows sample-app"
fi

if [ "$PASS" = true ]; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
