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

# ── 1. Diagnosis exists and is substantial ──────────────────────
if [ -f diagnosis.md ]; then
  check true "diagnosis.md exists"
  CHARS=$(wc -c < diagnosis.md)
  [ "$CHARS" -gt 200 ] && check true "diagnosis.md is substantial (${CHARS} chars)" || check false "diagnosis.md too short (${CHARS} chars)"
else
  check false "diagnosis.md exists"
fi

# ── 2. Diagnosis identifies the output format mismatch ──────────
if [ -f diagnosis.md ]; then
  grep -qi "format" diagnosis.md && check true "diagnosis mentions format" || check false "diagnosis missing format discussion"
  grep -qiE "comma|separator|\\\$.*,|1,247" diagnosis.md && check true "diagnosis identifies number formatting issue" || check false "diagnosis missing number formatting specifics"
  grep -qiE "parenthes|units.*\(|Widget.*\(" diagnosis.md && check true "diagnosis identifies parenthetical format" || check false "diagnosis missing parenthetical format issue"
fi

# ── 3. Diagnosis identifies the general pattern ─────────────────
if [ -f diagnosis.md ]; then
  grep -qiE "hidden contract|output.*contract|format.*contract|test.*expect|specification" diagnosis.md && check true "diagnosis names the general pattern" || check false "diagnosis does not generalize the bug pattern"
fi

# ── 4. Improved config exists ───────────────────────────────────
if [ -f workspace/improved-config/CLAUDE.md ]; then
  check true "improved config exists"
  CHARS=$(wc -c < workspace/improved-config/CLAUDE.md)
  [ "$CHARS" -gt 100 ] && check true "improved config is substantial (${CHARS} chars)" || check false "improved config too short (${CHARS} chars)"
else
  check false "improved config exists"
fi

# ── 5. Improved config addresses the root cause ─────────────────
if [ -f workspace/improved-config/CLAUDE.md ]; then
  # Must tell the agent to read existing test files first
  grep -qiE "read.*test|existing.*test|test.*exist|check.*test" workspace/improved-config/CLAUDE.md && check true "improved config tells agent to read existing tests" || check false "improved config doesn't mention reading existing tests"

  # Must mention output format expectations
  grep -qiE "format|comma.*separat|\\\$.*\.|parenthes" workspace/improved-config/CLAUDE.md && check true "improved config addresses output format" || check false "improved config doesn't mention output format"

  # Should be meaningfully different from the weak config
  WEAK_CHARS=$(wc -c < workspace/weak-config/CLAUDE.md)
  [ "$CHARS" -gt "$WEAK_CHARS" ] && check true "improved config is more detailed than weak config" || check false "improved config is not more detailed"
fi

# ── 6. Improved config does NOT over-specify ────────────────────
if [ -f workspace/improved-config/CLAUDE.md ]; then
  # Should not contain exact dollar amounts from the test data (that would be overfitting)
  if grep -q "1,247,890" workspace/improved-config/CLAUDE.md; then
    check false "improved config does not hardcode test answers (found exact revenue figure)"
  else
    check true "improved config does not hardcode test answers"
  fi
fi

if [ "$PASS" = true ]; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
