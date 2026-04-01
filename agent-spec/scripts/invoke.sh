#!/usr/bin/env bash
# invoke.sh — Run one agent in a sandbox and score the result.
#
# Usage: scripts/invoke.sh <source_repo> <config_dir> <prompt_file> [options]
#
# Options:
#   --budget <usd>     Max budget (default: from config.sh)
#   --model <name>     Model name (default: from config.sh)
#   --verify <script>  Verification script path
#   --keep             Preserve sandbox after completion
#   --delete <files>   Comma-separated files to delete before agent runs
#   --setup <cmds>     Semicolon-separated setup commands
#   --inject <dir>     Directory of files to inject into sandbox
#   --port <port>      Use specific port (default: auto-allocate)
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

# ── Parse arguments ──────────────────────────────────────────────

SOURCE="${1:?Usage: invoke.sh <source_repo> <config_dir> <prompt_file>}"
CONFIG="${2:?Usage: invoke.sh <source_repo> <config_dir> <prompt_file>}"
PROMPT_FILE="${3:?Usage: invoke.sh <source_repo> <config_dir> <prompt_file>}"
shift 3

BUDGET="$DEFAULT_BUDGET"
MODEL="$DEFAULT_MODEL"
VERIFY=""
KEEP=false
DELETE_FILES=""
SETUP_CMDS=""
INJECT_FROM=""
PORT_REQUEST=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --budget)  BUDGET="$2"; shift 2 ;;
    --model)   MODEL="$2"; shift 2 ;;
    --verify)  VERIFY="$2"; shift 2 ;;
    --inject)  INJECT_FROM="$2"; shift 2 ;;
    --keep)    KEEP=true; shift ;;
    --delete)  DELETE_FILES="$2"; shift 2 ;;
    --setup)   SETUP_CMDS="$2"; shift 2 ;;
    --port)    PORT_REQUEST="$2"; shift 2 ;;
    *) die "Unknown option: $1" ;;
  esac
done

# ── Phase 1: VALIDATE ───────────────────────────────────────────

require_dir "$SOURCE" "Source repo not found"
require_dir "$CONFIG" "Config directory not found"
require_file "$PROMPT_FILE" "Prompt file not found"
[[ -n "$VERIFY" ]] && require_file "$VERIFY" "Verify script not found"
[[ -n "$INJECT_FROM" ]] && require_dir "$INJECT_FROM" "Inject directory not found"

# ── Generate run ID and allocate port ────────────────────────────

export AGENT_SPEC_RUN_ID
AGENT_SPEC_RUN_ID=$(uuidgen | tr '[:upper:]' '[:lower:]' | head -c 8)
RUN_DIR="$RUN_ROOT/$AGENT_SPEC_RUN_ID"
RESULTS_DIR="$PROJECT_DIR/results/$AGENT_SPEC_RUN_ID"
mkdir -p "$RUN_DIR" "$RESULTS_DIR"

export PORT
PORT=$(allocate_port "${PORT_REQUEST:-}")

TARGET_NAME=$(basename "$SOURCE")
CONFIG_NAME=$(basename "$CONFIG")

echo "=== agent-spec run: $AGENT_SPEC_RUN_ID ==="
echo "  Target: $TARGET_NAME"
echo "  Config: $CONFIG_NAME"
echo "  Model:  $MODEL"
echo "  Budget: \$$BUDGET"
echo "  Port:   $PORT"
echo "  Log:    $RUN_DIR/events.jsonl"
echo "  Watch:  tail -f $RUN_DIR/events.jsonl | jq ."
echo ""

# ── Phase 2: SANDBOX ────────────────────────────────────────────

mkdir -p "$SANDBOX_ROOT"
SANDBOX="$SANDBOX_ROOT-$AGENT_SPEC_RUN_ID"
[[ -d "$SANDBOX" ]] && die "Sandbox already exists: $SANDBOX"
cp -aL "$SOURCE" "$SANDBOX" 2>/dev/null || cp -a "$SOURCE" "$SANDBOX"

setup_cleanup "$SANDBOX" "$KEEP"

apc_log "INFO" "sandbox_created" "Sandbox ready" \
  "{\"sandbox\":\"$SANDBOX\",\"source\":\"$SOURCE\"}"

# ── Phase 3: PREPARE ────────────────────────────────────────────

# 3a. Delete files the agent must produce
if [[ -n "$DELETE_FILES" ]]; then
  IFS=',' read -ra DEL_LIST <<< "$DELETE_FILES"
  for f in "${DEL_LIST[@]}"; do
    rm -rf "$SANDBOX/$f"
    echo "  Deleted: $f"
  done
  apc_log "DEBUG" "files_deleted" "Deleted files for agent to produce" \
    "{\"files\":\"$DELETE_FILES\"}"
fi

# 3b. Inject files (cordyceps — AFTER delete)
if [[ -n "$INJECT_FROM" ]]; then
  cp -a "$INJECT_FROM"/* "$SANDBOX/"
  apc_log "DEBUG" "files_injected" "Injected files" "{\"from\":\"$INJECT_FROM\"}"
fi

# 3c. Run setup commands
if [[ -n "$SETUP_CMDS" ]]; then
  IFS=';' read -ra CMDS <<< "$SETUP_CMDS"
  for cmd in "${CMDS[@]}"; do
    cmd=$(echo "$cmd" | xargs)
    [[ -z "$cmd" ]] && continue
    echo "  Setup: $cmd"
    if ! (cd "$SANDBOX" && eval "$cmd"); then
      apc_log "WARN" "setup_failed" "Setup command failed" "{\"cmd\":\"$cmd\"}"
      echo "  WARNING: setup failed: $cmd" >&2
    fi
  done
  apc_log "DEBUG" "setup_complete" "Setup finished" '{}'
fi

# 3d. Swap .claude/ with test config
rm -rf "$SANDBOX/.claude"
if [[ -n "$(ls -A "$CONFIG" 2>/dev/null)" ]]; then
  cp -a "$CONFIG" "$SANDBOX/.claude"
else
  mkdir -p "$SANDBOX/.claude"
  echo "  WARNING: Empty config — agent has no instructions" >&2
fi
apc_log "INFO" "config_swapped" "Config applied" \
  "{\"config\":\"$CONFIG_NAME\"}"

# 3e. Inject emitter libraries
for emitter in "$SCRIPT_DIR/_apc.py" "$SCRIPT_DIR/_apc.ts"; do
  [[ -f "$emitter" ]] && cp "$emitter" "$SANDBOX/"
done

# 3f. Start resource monitor
bash "$SCRIPT_DIR/sidecar.sh" 30 &
set_sidecar_pid $!

# ── Phase 4: EXECUTE ────────────────────────────────────────────

PROMPT=$(cat "$PROMPT_FILE")
PROMPT="${PROMPT//__PORT__/$PORT}"

apc_log "INFO" "agent_started" "Agent invoked" \
  "{\"target\":\"$TARGET_NAME\",\"config\":\"$CONFIG_NAME\",\"model\":\"$MODEL\",\"budget\":$BUDGET,\"port\":$PORT}"

START_MS=$(now_ms)
TIMEOUT="${TIMEOUT:-$TIMEOUT_DEFAULT}"

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

END_MS=$(now_ms)
DURATION_MS=$(( END_MS - START_MS ))

# Log outcome
if [[ $EXIT_CODE -eq 124 ]]; then
  apc_log "ERROR" "agent_timeout" "Agent timed out after ${TIMEOUT}s" \
    "{\"timeout\":$TIMEOUT}"
elif [[ $EXIT_CODE -eq 0 ]]; then
  apc_log "INFO" "agent_complete" "Agent finished" \
    "{\"exit_code\":0,\"duration_ms\":$DURATION_MS}"
else
  STDERR_TAIL=$(tail -5 "$RUN_DIR/stderr.log" 2>/dev/null | tr '\n' ' ' | head -c 200)
  apc_log "ERROR" "agent_error" "Agent failed (exit $EXIT_CODE)" \
    "{\"exit_code\":$EXIT_CODE,\"duration_ms\":$DURATION_MS,\"stderr\":\"$STDERR_TAIL\"}"
fi

# ── Phase 5: METRICS ────────────────────────────────────────────

if [[ -f "$RUN_DIR/output.json" ]] && [[ -s "$RUN_DIR/output.json" ]]; then
  TOKENS=$(OFILE="$RUN_DIR/output.json" python3 -c '
import json, os
try:
    data = json.load(open(os.environ["OFILE"]))
    u = data.get("result", {}).get("modelUsage", data.get("modelUsage", {}))
    if not u:
        for key in data:
            if isinstance(data[key], dict) and "inputTokens" in data[key]:
                u = data[key]; break
    inp = u.get("inputTokens", 0)
    out = u.get("outputTokens", 0)
    cache_c = u.get("cacheCreationInputTokens", 0)
    cache_r = u.get("cacheReadInputTokens", 0)
    cost = data.get("result", {}).get("costUSD", data.get("costUSD", 0))
    turns = data.get("result", {}).get("numTurns", data.get("numTurns", 0))
    print(json.dumps({"input": inp, "output": out, "cache_create": cache_c,
                       "cache_read": cache_r, "cost_usd": round(cost, 4), "turns": turns}))
except Exception as e:
    print("{}")
' 2>/dev/null || echo '{}')
  if [[ "$TOKENS" != '{}' ]]; then
    apc_log "METRIC" "token_update" "Token usage" "$TOKENS"
    echo "  Tokens: $TOKENS"
  fi
fi

# ── Phase 6: VERIFY ─────────────────────────────────────────────

if [[ -n "$VERIFY" ]]; then
  echo ""
  echo "=== Verification ==="
  cp "$VERIFY" "$SANDBOX/verify.sh"

  set +e
  SCORE_OUTPUT=$(cd "$SANDBOX" && PORT="$PORT" AGENT_SPEC_RUN_ID="$AGENT_SPEC_RUN_ID" bash verify.sh 2>&1)
  VERIFY_EXIT=$?
  set -e

  echo "$SCORE_OUTPUT"

  # Parse individual test results
  while IFS= read -r line; do
    if [[ "$line" == *"PASS:"* ]] && [[ "$line" != *"RESULT:"* ]]; then
      apc_log "INFO" "test_passed" "Test passed" "{\"test_name\":\"${line##*PASS: }\"}"
    elif [[ "$line" == *"FAIL:"* ]] && [[ "$line" != *"RESULT:"* ]]; then
      apc_log "ERROR" "test_failed" "Test failed" "{\"test_name\":\"${line##*FAIL: }\"}"
    fi
  done <<< "$SCORE_OUTPUT"

  # Parse final result
  if echo "$SCORE_OUTPUT" | grep -q "RESULT: PASS"; then
    apc_log "INFO" "score" "PASS" '{"result":"PASS"}'
  elif echo "$SCORE_OUTPUT" | grep -q "RESULT: FAIL"; then
    apc_log "ERROR" "score" "FAIL" '{"result":"FAIL"}'
  else
    apc_log "WARN" "score" "No RESULT line" '{"result":"N/A"}'
  fi
fi

# ── Phase 7: ARCHIVE ────────────────────────────────────────────

echo ""
echo "=== Archiving ==="
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  mkdir -p "$RESULTS_DIR/produced/$(dirname "$f")"
  cp "$SANDBOX/$f" "$RESULTS_DIR/produced/$f" && echo "  Saved: $f"
done < <(cd "$SANDBOX" && find . -maxdepth 3 \( -name '*.py' -o -name '*.js' -o -name '*.ts' \) \
  ! -path '*/node_modules/*' ! -name '_apc.*' 2>/dev/null)

for artifact in events.jsonl output.json stderr.log; do
  [[ -f "$RUN_DIR/$artifact" ]] && cp "$RUN_DIR/$artifact" "$RESULTS_DIR/"
done
echo "  Results: $RESULTS_DIR/"

# ── Summary ──────────────────────────────────────────────────────

echo ""
echo "=== Run $AGENT_SPEC_RUN_ID complete ==="
bash "$SCRIPT_DIR/dashboard.sh" "$AGENT_SPEC_RUN_ID" --summary 2>/dev/null || true
