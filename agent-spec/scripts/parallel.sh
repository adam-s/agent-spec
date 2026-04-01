#!/usr/bin/env bash
# parallel.sh — Launch parallel invoke.sh instances for a target.
#
# Usage:
#   scripts/parallel.sh <target> [config] [options]
#
# Options:
#   --instances N          Reps per variant (default: 1)
#   --configs c1,c2        Comma-separated configs (default: baseline)
#   --models m1,m2         Comma-separated models (creates matrix with configs)
#   --stimuli-dir <path>   Per-instance files to inject (round-robin)
#   --keep                 Preserve sandboxes
#   --model <name>         Single model override
#   --budget <usd>         Budget override
#
# Matrix: --configs a,b --models x,y → 4 variants (a/x, a/y, b/x, b/y)
# Output: Run IDs to stdout (one per line). Progress to stderr.
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

TARGET_NAME="${1:?Usage: parallel.sh <target> [config] [options]}"
shift

CONFIG_NAME="baseline"
if [[ $# -gt 0 ]] && [[ "$1" != --* ]]; then
  CONFIG_NAME="$1"; shift
fi

INSTANCES=1
STIMULI_DIR=""
CONFIGS=""
MODELS=""
SINGLE_MODEL=""
EXTRA_FLAGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --instances)    INSTANCES="$2"; shift 2 ;;
    --configs)      CONFIGS="$2"; shift 2 ;;
    --models)       MODELS="$2"; shift 2 ;;
    --stimuli-dir)  STIMULI_DIR="$2"; shift 2 ;;
    --keep)         EXTRA_FLAGS+=(--keep); shift ;;
    --model)        SINGLE_MODEL="$2"; shift 2 ;;
    --budget)       EXTRA_FLAGS+=(--budget "$2"); shift 2 ;;
    *) die "Unknown option: $1" ;;
  esac
done

# Validate target
TARGET_DIR="$PROJECT_DIR/targets/$TARGET_NAME"
require_dir "$TARGET_DIR" "Target not found"

# ── Build variant matrix ─────────────────────────────────────────

IFS=',' read -ra CONFIG_LIST <<< "${CONFIGS:-$CONFIG_NAME}"

if [[ -n "$MODELS" ]]; then
  IFS=',' read -ra MODEL_LIST <<< "$MODELS"
elif [[ -n "$SINGLE_MODEL" ]]; then
  MODEL_LIST=("$SINGLE_MODEL")
else
  MODEL_LIST=("")
fi

VARIANTS=()
for c in "${CONFIG_LIST[@]}"; do
  for m in "${MODEL_LIST[@]}"; do
    for _ in $(seq 1 "$INSTANCES"); do
      VARIANTS+=("$c|$m")
    done
  done
done

TOTAL=${#VARIANTS[@]}
MAX_PARALLEL=$(( PORT_MAX - PORT_MIN + 1 ))
if [[ $TOTAL -gt $MAX_PARALLEL ]]; then
  die "Too many parallel instances ($TOTAL). Max is $MAX_PARALLEL (ports $PORT_MIN-$PORT_MAX)."
fi

# ── Collect stimuli ──────────────────────────────────────────────

STIMULI_FILES=()
if [[ -n "$STIMULI_DIR" ]] && [[ -d "$STIMULI_DIR" ]]; then
  while IFS= read -r f; do
    STIMULI_FILES+=("$f")
  done < <(find "$STIMULI_DIR" -maxdepth 1 -type f | sort)
fi

# ── Launch ───────────────────────────────────────────────────────

PIDS=()
RUN_IDS=()
MANIFEST="/tmp/agent-spec-parallel-$$-$(date +%s).txt"
: > "$MANIFEST"

echo "Launching $TOTAL parallel instance(s) of $TARGET_NAME" >&2
echo "  Logs: /tmp/agent-spec-parallel-out-$$-{1..$TOTAL}.log" >&2
echo "  Watch: tail -f /tmp/agent-spec-parallel-out-$$-*.log" >&2
echo "" >&2

for i in $(seq 1 "$TOTAL"); do
  IDX=$((i - 1))
  IFS='|' read -r V_CONFIG V_MODEL <<< "${VARIANTS[$IDX]}"

  INSTANCE_FLAGS=("${EXTRA_FLAGS[@]}")
  [[ -n "$V_MODEL" ]] && INSTANCE_FLAGS+=(--model "$V_MODEL")

  # Port: PORT_MIN + (i-1)
  INSTANCE_PORT=$(( PORT_MIN + i - 1 ))

  # Stimuli injection
  INJECT_ARGS=()
  if [[ ${#STIMULI_FILES[@]} -gt 0 ]]; then
    INSTANCE_INJECT="/tmp/agent-spec-inject-$$-$i"
    mkdir -p "$INSTANCE_INJECT"
    STIM_IDX=$(( IDX % ${#STIMULI_FILES[@]} ))
    cp "${STIMULI_FILES[$STIM_IDX]}" "$INSTANCE_INJECT/wireframe.png"
    INJECT_ARGS=(--inject "$INSTANCE_INJECT")
  fi

  # Resolve config: target-specific first, then _shared
  CONFIG_DIR="$TARGET_DIR/configs/$V_CONFIG"
  if [[ ! -d "$CONFIG_DIR" ]]; then
    CONFIG_DIR="$PROJECT_DIR/targets/_shared/configs/$V_CONFIG"
    require_dir "$CONFIG_DIR" "Config '$V_CONFIG' not found in target or _shared"
  fi

  DESC="$V_CONFIG"
  [[ -n "$V_MODEL" ]] && DESC="$DESC / $(basename "$V_MODEL")"
  echo "  Instance $i: $DESC (port $INSTANCE_PORT)" >&2

  # Build run-eval args
  LAUNCH_ARGS=("$TARGET_NAME" "$V_CONFIG" --port "$INSTANCE_PORT")
  [[ ${#INSTANCE_FLAGS[@]} -gt 0 ]] && LAUNCH_ARGS+=("${INSTANCE_FLAGS[@]}")
  [[ ${#INJECT_ARGS[@]} -gt 0 ]] && LAUNCH_ARGS+=("${INJECT_ARGS[@]}")

  bash "$SCRIPT_DIR/run-eval.sh" "${LAUNCH_ARGS[@]}" \
    > "/tmp/agent-spec-parallel-out-$$-$i.log" 2>&1 &
  PIDS+=($!)
done

echo "" >&2
echo "Waiting for all instances..." >&2

# ── Collect results ──────────────────────────────────────────────

FAILURES=0
for i in $(seq 1 "$TOTAL"); do
  IDX=$((i - 1))
  PID="${PIDS[$IDX]}"
  LOG="/tmp/agent-spec-parallel-out-$$-$i.log"

  set +e
  wait "$PID"
  EXIT=$?
  set -e

  RUN_ID=$(grep -o 'agent-spec run: [a-f0-9]\{8\}' "$LOG" 2>/dev/null | head -1 | awk '{print $NF}')

  if [[ -n "$RUN_ID" ]]; then
    RUN_IDS+=("$RUN_ID")
    echo "$RUN_ID" >> "$MANIFEST"
    RESULT=$(grep -o 'RESULT: [A-Z/]*' "$LOG" 2>/dev/null | tail -1 || echo "RESULT: UNKNOWN")
    echo "  Instance $i: run=$RUN_ID exit=$EXIT $RESULT" >&2

    # Archive instance log
    [[ -d "$PROJECT_DIR/results/$RUN_ID" ]] && \
      cp "$LOG" "$PROJECT_DIR/results/$RUN_ID/parallel-instance.log" 2>/dev/null

    if [[ "$RESULT" != *"PASS"* ]]; then
      FAILURES=$((FAILURES + 1))
      echo "  --- Failure log (last 15 lines) ---" >&2
      tail -15 "$LOG" 2>/dev/null | sed 's/^/    /' >&2
      echo "  --- end ---" >&2
    fi
  else
    echo "  Instance $i: exit=$EXIT (no run_id)" >&2
    echo "  --- Failure log (last 15 lines) ---" >&2
    tail -15 "$LOG" 2>/dev/null | sed 's/^/    /' >&2
    echo "  --- end ---" >&2
    FAILURES=$((FAILURES + 1))
  fi
done

# Clean up temp inject dirs
rm -rf /tmp/agent-spec-inject-$$-* 2>/dev/null || true

echo "" >&2
echo "Manifest: $MANIFEST" >&2
echo "Run IDs:" >&2
for rid in "${RUN_IDS[@]}"; do
  echo "$rid"
done

exit $FAILURES
