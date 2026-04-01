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
#   --delete <files>   Comma-separated files to delete before agent runs
#   --setup <cmds>     Semicolon-separated commands to run in sandbox before agent
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SANDBOX_DIR="$SCRIPT_DIR/../sandbox"
MONITOR_DIR="$SCRIPT_DIR/../monitor"
INJECT_DIR="$SCRIPT_DIR/../inject"
source "$SCRIPT_DIR/lib.sh"

# Parse arguments
SOURCE="${1:?Usage: invoke.sh <source_repo> <config_dir> <prompt_file>}"
CONFIG="${2:?Usage: invoke.sh <source_repo> <config_dir> <prompt_file>}"
PROMPT_FILE="${3:?Usage: invoke.sh <source_repo> <config_dir> <prompt_file>}"

# Validate inputs
if [[ ! -d "$SOURCE" ]]; then
  echo "Source repo not found: $SOURCE" >&2
  exit 1
fi
if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "Prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi
shift 3

BUDGET="2.00"
MODEL="claude-sonnet-4-6"
VERIFY=""
KEEP=false
DELETE_FILES=""
SETUP_CMDS=""
INJECT_FROM=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --budget) BUDGET="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --verify) VERIFY="$2"; shift 2 ;;
    --inject) INJECT_FROM="$2"; shift 2 ;;
    --keep) KEEP=true; shift ;;
    --delete) DELETE_FILES="$2"; shift 2 ;;
    --setup) SETUP_CMDS="$2"; shift 2 ;;
    --port) PORT_OVERRIDE="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# Generate run ID and allocate port
export AGENT_SPEC_RUN_ID
AGENT_SPEC_RUN_ID=$(uuidgen | tr '[:upper:]' '[:lower:]' | head -c 8)
RUN_DIR="/tmp/agent-spec/${AGENT_SPEC_RUN_ID}"
RESULTS_DIR="$PROJECT_DIR/results/$AGENT_SPEC_RUN_ID"
mkdir -p "$RUN_DIR" "$RESULTS_DIR"

# Allocate unique port from reserved range (3100-3110)
# If --port was given, use that directly (parallel-invoke pre-assigns ports)
export PORT
if [[ -n "${PORT_OVERRIDE:-}" ]]; then
  PORT="$PORT_OVERRIDE"
else
  PORT=3100
  for p in $(seq 3100 3110); do
    if ! lsof -ti:"$p" >/dev/null 2>&1; then
      PORT=$p
      break
    fi
  done
fi

TARGET_NAME=$(basename "$SOURCE")
CONFIG_NAME=$(basename "$CONFIG")

echo "=== agent-spec run: $AGENT_SPEC_RUN_ID ==="
echo "  Target: $TARGET_NAME"
echo "  Config: $CONFIG_NAME"
echo "  Model:  $MODEL"
echo "  Budget: \$$BUDGET"
echo "  Port:   $PORT"
echo "  Log:    $RUN_DIR/events.jsonl"
echo ""

# 1. Clear ports used by previous runs
bash "$SCRIPT_DIR/../sandbox/clear-ports.sh" 2>/dev/null || true

# 2. Copy repo into sandbox
SANDBOX=$(bash "$SANDBOX_DIR/copy-repo.sh" "$SOURCE" "$AGENT_SPEC_RUN_ID")

# Cleanup trap: stop sidecar and remove sandbox on any exit
SIDECAR_PID=""
TERMINATED_BY_SIGNAL=""
handle_signal() {
  TERMINATED_BY_SIGNAL="$1"
  apc_log "ERROR" "run_terminated" "Run terminated by signal" \
    "{\"signal\":\"$1\",\"run_id\":\"$AGENT_SPEC_RUN_ID\"}"
  exit 1
}
cleanup() {
  [[ -n "$SIDECAR_PID" ]] && kill "$SIDECAR_PID" 2>/dev/null || true
  bash "$SCRIPT_DIR/../sandbox/clear-ports.sh" 2>/dev/null || true
  if [[ "$KEEP" = false ]] && [[ -n "${SANDBOX:-}" ]]; then
    rm -rf "$SANDBOX"
  fi
}
trap cleanup EXIT
trap 'handle_signal SIGTERM' TERM
trap 'handle_signal SIGINT' INT
trap 'handle_signal SIGHUP' HUP

apc_log "DEBUG" "sandbox_created" "Sandbox ready" \
  "{\"sandbox\":\"$SANDBOX\",\"source\":\"$SOURCE\"}"

# 3. Delete files the agent must produce (comma-separated)
if [[ -n "$DELETE_FILES" ]]; then
  IFS=',' read -ra DEL_LIST <<< "$DELETE_FILES"
  for f in "${DEL_LIST[@]}"; do
    rm -rf "$SANDBOX/$f" && echo "  Deleted: $f (agent must produce this)"
  done
  apc_log "DEBUG" "files_deleted" "Deleted files for agent to produce" \
    "{\"files\":\"$DELETE_FILES\"}"
fi

# 4. Inject files from target's inject/ directory (cordyceps — AFTER delete)
if [[ -n "$INJECT_FROM" ]]; then
  if [[ -d "$INJECT_FROM" ]]; then
    echo "  Injecting files from $INJECT_FROM"
    cp -a "$INJECT_FROM"/* "$SANDBOX/" 2>/dev/null || true
  else
    echo "  WARNING: Inject directory not found: $INJECT_FROM" >&2
  fi
fi

# 4. Run setup commands in sandbox
if [[ -n "$SETUP_CMDS" ]]; then
  echo "  Running setup..."
  IFS=';' read -ra CMDS <<< "$SETUP_CMDS"
  for cmd in "${CMDS[@]}"; do
    cmd=$(echo "$cmd" | xargs)  # trim whitespace
    [[ -z "$cmd" ]] && continue
    echo "    $ $cmd"
    (cd "$SANDBOX" && eval "$cmd") || {
      echo "    WARNING: setup command failed: $cmd"
      apc_log "WARN" "setup_failed" "Setup command failed" "{\"cmd\":\"$cmd\"}"
    }
  done
  apc_log "DEBUG" "setup_complete" "Setup commands finished" '{}'
fi

# 5. Swap .claude/ with test config
bash "$SANDBOX_DIR/swap-claude-dir.sh" "$SANDBOX" "$CONFIG"

# 6. Inject emitter libraries
cp "$INJECT_DIR/_apc.py" "$SANDBOX/" 2>/dev/null || true
cp "$INJECT_DIR/_apc.ts" "$SANDBOX/" 2>/dev/null || true

# 7. Start resource monitor sidecar
bash "$MONITOR_DIR/sidecar.sh" 30 &
SIDECAR_PID=$!

# 8. Log start
PROMPT=$(cat "$PROMPT_FILE")
# Substitute __PORT__ in prompt with allocated port
PROMPT="${PROMPT//__PORT__/$PORT}"
apc_log "INFO" "agent_started" "Agent invoked" \
  "{\"target\":\"$TARGET_NAME\",\"config\":\"$CONFIG_NAME\",\"model\":\"$MODEL\",\"budget\":$BUDGET,\"port\":$PORT}"

# 9. Run claude agent (from inside the sandbox for CWD isolation)
START_MS=$(python3 -c "import time; print(int(time.time()*1000))")

TIMEOUT="${TIMEOUT:-600}"  # 10 minute default, override with TIMEOUT env var
set +e
(cd "$SANDBOX" && timeout "$TIMEOUT" claude -p "$PROMPT" \
  --output-format json \
  --dangerously-skip-permissions \
  --max-budget-usd "$BUDGET" \
  --model "$MODEL") \
  > "$RUN_DIR/output.json" \
  2> "$RUN_DIR/stderr.log"
EXIT_CODE=$?
set -e

if [[ $EXIT_CODE -eq 124 ]]; then
  apc_log "ERROR" "agent_timeout" "Agent timed out after ${TIMEOUT}s" '{}'
fi

END_MS=$(python3 -c "import time; print(int(time.time()*1000))")
DURATION_MS=$(( END_MS - START_MS ))

# 10. Log completion
if [[ $EXIT_CODE -eq 0 ]]; then
  apc_log "INFO" "agent_complete" "Agent finished successfully" \
    "{\"exit_code\":$EXIT_CODE,\"duration_ms\":$DURATION_MS}"
else
  STDERR_TAIL=$(tail -5 "$RUN_DIR/stderr.log" 2>/dev/null | tr '\n' ' ' | head -c 200)
  apc_log "ERROR" "agent_error" "Agent failed" \
    "{\"exit_code\":$EXIT_CODE,\"duration_ms\":$DURATION_MS,\"stderr_tail\":\"$STDERR_TAIL\"}"
fi

# 11. Parse token metrics
if [[ -f "$RUN_DIR/output.json" ]] && [[ -s "$RUN_DIR/output.json" ]]; then
  TOKENS=$(bash "$SCRIPT_DIR/parse-output.sh" "$RUN_DIR/output.json" 2>/dev/null || echo '{}')
  apc_log "METRIC" "token_update" "Token usage" "$TOKENS"
  echo "  Tokens: $TOKENS"
fi

# 12. Run verification
if [[ -n "$VERIFY" ]] && [[ -f "$VERIFY" ]]; then
  echo ""
  echo "=== Verification ==="
  # Inject APC lib into verify context
  cp "$VERIFY" "$SANDBOX/verify.sh"
  cp "$SCRIPT_DIR/lib.sh" "$SANDBOX/_apc_lib.sh" 2>/dev/null || true
  set +e
  SCORE_OUTPUT=$(cd "$SANDBOX" && AGENT_SPEC_RUN_ID="$AGENT_SPEC_RUN_ID" PORT="$PORT" bash verify.sh 2>&1)
  VERIFY_EXIT=$?
  set -e
  echo "$SCORE_OUTPUT"

  # Parse test results from output and emit events
  while IFS= read -r line; do
    if [[ "$line" == *"PASS:"* ]]; then
      TEST_NAME=$(echo "$line" | sed 's/.*PASS: //')
      apc_log "INFO" "test_passed" "Test passed" "{\"test_name\":\"$TEST_NAME\"}"
    elif [[ "$line" == *"FAIL:"* ]] && [[ "$line" != *"RESULT:"* ]]; then
      TEST_NAME=$(echo "$line" | sed 's/.*FAIL: //')
      apc_log "ERROR" "test_failed" "Test failed" "{\"test_name\":\"$TEST_NAME\"}"
    fi
  done <<< "$SCORE_OUTPUT"

  if echo "$SCORE_OUTPUT" | grep -q "RESULT: PASS"; then
    apc_log "INFO" "score" "Verification passed" '{"result":"PASS"}'
  elif echo "$SCORE_OUTPUT" | grep -q "RESULT: FAIL"; then
    apc_log "ERROR" "score" "Verification failed" '{"result":"FAIL"}'
  else
    apc_log "WARN" "score" "No RESULT line in verify output" '{"result":"N/A"}'
  fi
fi

# 13. Save produced code to results
echo ""
echo "=== Archiving ==="
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  mkdir -p "$RESULTS_DIR/produced/$(dirname "$f")"
  cp "$SANDBOX/$f" "$RESULTS_DIR/produced/$f" 2>/dev/null && echo "  Saved: $f"
done < <(cd "$SANDBOX" && find . -maxdepth 2 \( -name '*.py' -o -name '*.js' -o -name '*.ts' \) 2>/dev/null | grep -v node_modules | grep -v '_apc')

# 14. Persist events and output to results/
cp "$RUN_DIR/events.jsonl" "$RESULTS_DIR/" 2>/dev/null || true
cp "$RUN_DIR/output.json" "$RESULTS_DIR/" 2>/dev/null || true
cp "$RUN_DIR/stderr.log" "$RESULTS_DIR/" 2>/dev/null || true
echo "  Results: $RESULTS_DIR/"

# 15. Summary (sidecar stop, port cleanup, and sandbox removal handled by EXIT trap)
echo ""
echo "=== Run $AGENT_SPEC_RUN_ID complete ==="
bash "$SCRIPT_DIR/../cli/dashboard.sh" "$AGENT_SPEC_RUN_ID" --summary 2>/dev/null || true
