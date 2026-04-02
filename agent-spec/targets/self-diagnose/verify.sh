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

# 1. diagnosis.md exists and is substantial
if [ -f diagnosis.md ]; then
  check true "diagnosis.md exists"
  CHARS=$(wc -c < diagnosis.md)
  [ "$CHARS" -gt 100 ] && check true "diagnosis.md is substantial (${CHARS} chars)" || check false "diagnosis.md too short (${CHARS} chars)"
else
  check false "diagnosis.md exists"
fi

# 2. Identifies the root cause: function name mismatch
if [ -f diagnosis.md ]; then
  grep -qi "generate_report\|function name\|import.*name\|named.*wrong\|mismatch" diagnosis.md && check true "identifies function name issue" || check false "does not identify function name issue"
  grep -qi "create_report" diagnosis.md && check true "mentions the incorrect name create_report" || check false "does not mention create_report"
fi

# 3. References evidence from the run
if [ -f diagnosis.md ]; then
  grep -qi "test.py\|verification\|ImportError\|0/5" diagnosis.md && check true "references verification evidence" || check false "no verification evidence cited"
fi

# 4. Suggests a fix
if [ -f diagnosis.md ]; then
  grep -qi "fix\|instruct\|config\|CLAUDE.md\|recommend\|should\|change" diagnosis.md && check true "suggests a fix" || check false "no fix suggested"
fi

if [ "$PASS" = true ]; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
