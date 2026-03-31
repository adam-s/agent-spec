#!/usr/bin/env bash
# invoke.sh — Main entry point: sandbox a repo, run a claude agent, score results.
#
# Usage: scripts/apc/invoke.sh <source_repo> <config_dir> <prompt_file> [options]
#
# Options:
#   --budget <usd>     Max budget (default: 2.00)
#   --model <name>     Model name (default: claude-sonnet-4-6)
#   --verify <script>  Verification script to run after agent completes
#   --keep             Don't remove sandbox after completion
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SANDBOX_DIR="$SCRIPT_DIR/../sandbox"
MONITOR_DIR="$SCRIPT_DIR/../monitor"
INJECT_DIR="$SCRIPT_DIR/../inject"
source "$SCRIPT_DIR/lib.sh"

# Parse arguments
SOURCE="${1:?Usage: invoke.sh <source_repo> <config_dir> <prompt_file>}"
CONFIG="${2:?Usage: invoke.sh <source_repo> <config_dir> <prompt_file>}"
PROMPT_FILE="${3:?Usage: invoke.sh <source_repo> <config_dir> <prompt_file>}"
shift 3

BUDGET="2.00"
MODEL="claude-sonnet-4-6"
VERIFY=""
KEEP=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --budget) BUDGET="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --verify) VERIFY="$2"; shift 2 ;;
    --keep) KEEP=true; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# Generate run ID
export AGENT_SPEC_RUN_ID
AGENT_SPEC_RUN_ID=$(uuidgen | tr '[:upper:]' '[:lower:]' | head -c 8)
RUN_DIR="/tmp/agent-spec/${AGENT_SPEC_RUN_ID}"
mkdir -p "$RUN_DIR"

TARGET_NAME=$(basename "$SOURCE")
CONFIG_NAME=$(basename "$CONFIG")

echo "=== agent-spec run: $AGENT_SPEC_RUN_ID ==="
echo "  Target: $TARGET_NAME"
echo "  Config: $CONFIG_NAME"
echo "  Model:  $MODEL"
echo "  Budget: \$$BUDGET"
echo "  Log:    $RUN_DIR/events.jsonl"
echo ""

# 1. Copy repo into sandbox
SANDBOX=$(bash "$SANDBOX_DIR/copy-repo.sh" "$SOURCE" "$AGENT_SPEC_RUN_ID")

# 2. Swap .claude/ with test config
bash "$SANDBOX_DIR/swap-claude-dir.sh" "$SANDBOX" "$CONFIG"

# 3. Inject emitter libraries
cp "$INJECT_DIR/_apc.py" "$SANDBOX/" 2>/dev/null || true
cp "$INJECT_DIR/_apc.ts" "$SANDBOX/" 2>/dev/null || true

# 4. Start resource monitor sidecar
bash "$MONITOR_DIR/sidecar.sh" 30 &
SIDECAR_PID=$!

# 5. Log start
PROMPT=$(cat "$PROMPT_FILE")
apc_log "INFO" "agent_started" "Agent invoked" \
  "{\"target\":\"$TARGET_NAME\",\"config\":\"$CONFIG_NAME\",\"model\":\"$MODEL\",\"budget\":$BUDGET}"

# 6. Run claude agent (from inside the sandbox for CWD isolation)
START_MS=$(date +%s%3N 2>/dev/null || echo 0)

set +e
(cd "$SANDBOX" && claude -p "$PROMPT" \
  --output-format json \
  --dangerously-skip-permissions \
  --max-budget-usd "$BUDGET" \
  --model "$MODEL") \
  > "$RUN_DIR/output.json" \
  2> "$RUN_DIR/stderr.log"
EXIT_CODE=$?
set -e

END_MS=$(date +%s%3N 2>/dev/null || echo 0)
DURATION_MS=$((END_MS - START_MS))

# 7. Log completion
if [[ $EXIT_CODE -eq 0 ]]; then
  apc_log "INFO" "agent_complete" "Agent finished successfully" \
    "{\"exit_code\":$EXIT_CODE,\"duration_ms\":$DURATION_MS}"
else
  STDERR_TAIL=$(tail -5 "$RUN_DIR/stderr.log" 2>/dev/null | tr '\n' ' ' | head -c 200)
  apc_log "ERROR" "agent_error" "Agent failed" \
    "{\"exit_code\":$EXIT_CODE,\"duration_ms\":$DURATION_MS,\"stderr_tail\":\"$STDERR_TAIL\"}"
fi

# 8. Parse token metrics
if [[ -f "$RUN_DIR/output.json" ]] && [[ -s "$RUN_DIR/output.json" ]]; then
  TOKENS=$(bash "$SCRIPT_DIR/parse-output.sh" "$RUN_DIR/output.json" 2>/dev/null || echo '{}')
  apc_log "METRIC" "token_update" "Token usage" "$TOKENS"
  echo "  Tokens: $TOKENS"
fi

# 9. Run verification
if [[ -n "$VERIFY" ]] && [[ -f "$VERIFY" ]]; then
  echo ""
  echo "=== Verification ==="
  cp "$VERIFY" "$SANDBOX/verify.sh"
  set +e
  SCORE_OUTPUT=$(cd "$SANDBOX" && bash verify.sh 2>&1)
  VERIFY_EXIT=$?
  set -e
  echo "$SCORE_OUTPUT"

  if echo "$SCORE_OUTPUT" | grep -q "RESULT: PASS"; then
    apc_log "INFO" "score" "Verification passed" '{"result":"PASS"}'
  else
    apc_log "ERROR" "score" "Verification failed" '{"result":"FAIL"}'
  fi
fi

# 10. Stop sidecar
kill "$SIDECAR_PID" 2>/dev/null || true

# 11. Summary
echo ""
echo "=== Run $AGENT_SPEC_RUN_ID complete ==="
echo "  Events: $RUN_DIR/events.jsonl"
echo "  Output: $RUN_DIR/output.json"
echo "  Sandbox: $SANDBOX"

# 12. Cleanup sandbox (unless --keep)
if [[ "$KEEP" = false ]]; then
  rm -rf "$SANDBOX"
  echo "  Sandbox removed."
fi
