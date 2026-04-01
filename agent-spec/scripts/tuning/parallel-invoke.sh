#!/usr/bin/env bash
# parallel-invoke.sh — Launch parallel invoke.sh instances for the same target.
#
# Usage:
#   scripts/tuning/parallel-invoke.sh <target> [config] [options]
#
# Options:
#   --instances N          Number of identical parallel runs (default: 1 per variant)
#   --configs c1,c2        Comma-separated configs to test (runs one per config)
#   --models m1,m2         Comma-separated models to test (runs one per model)
#   --stimuli-dir <path>   Directory of per-instance files to inject
#   --keep                 Preserve sandboxes after completion
#   --model <name>         Override model (single model for all runs)
#   --budget <usd>         Override budget
#
# Matrix: --configs a,b --models x,y produces 4 runs (a/x, a/y, b/x, b/y)
#
# Output: Prints one run_id per line to stdout. Waits for all to complete.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

TARGET_NAME="${1:?Usage: parallel-invoke.sh <target> [config] [options]}"
shift

# Config (default: baseline)
CONFIG_NAME="baseline"
if [[ $# -gt 0 ]] && [[ "$1" != --* ]]; then
  CONFIG_NAME="$1"
  shift
fi

INSTANCES=0  # 0 = auto (one per variant)
STIMULI_DIR=""
CONFIGS=""
MODELS=""
SINGLE_MODEL=""
EXTRA_FLAGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --instances) INSTANCES="$2"; shift 2 ;;
    --configs) CONFIGS="$2"; shift 2 ;;
    --models) MODELS="$2"; shift 2 ;;
    --stimuli-dir) STIMULI_DIR="$2"; shift 2 ;;
    --keep) EXTRA_FLAGS+=(--keep); shift ;;
    --model) SINGLE_MODEL="$2"; shift 2 ;;
    --budget) EXTRA_FLAGS+=(--budget "$2"); shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# Validate target
TARGET_DIR="$PROJECT_DIR/targets/$TARGET_NAME"
if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Target not found: $TARGET_DIR" >&2
  exit 1
fi

# Build variant matrix
# If --configs provided, split into array; otherwise use the positional config
IFS=',' read -ra CONFIG_LIST <<< "${CONFIGS:-$CONFIG_NAME}"

# If --models provided, split into array; otherwise use single model (or empty for default)
if [[ -n "$MODELS" ]]; then
  IFS=',' read -ra MODEL_LIST <<< "$MODELS"
elif [[ -n "$SINGLE_MODEL" ]]; then
  MODEL_LIST=("$SINGLE_MODEL")
else
  MODEL_LIST=("")  # empty = use target.yaml default
fi

# Build the run plan: each (config, model) pair is a variant
VARIANTS=()
for c in "${CONFIG_LIST[@]}"; do
  for m in "${MODEL_LIST[@]}"; do
    VARIANTS+=("$c|$m")
  done
done

# If --instances > 0, replicate each variant that many times
if [[ "$INSTANCES" -gt 0 ]]; then
  EXPANDED=()
  for v in "${VARIANTS[@]}"; do
    for _ in $(seq 1 "$INSTANCES"); do
      EXPANDED+=("$v")
    done
  done
  VARIANTS=("${EXPANDED[@]}")
fi

TOTAL=${#VARIANTS[@]}

# Collect stimuli files if provided
STIMULI_FILES=()
if [[ -n "$STIMULI_DIR" ]] && [[ -d "$STIMULI_DIR" ]]; then
  while IFS= read -r f; do
    STIMULI_FILES+=("$f")
  done < <(ls "$STIMULI_DIR"/* 2>/dev/null | sort)
fi

# Launch all variants
PIDS=()
RUN_IDS=()
MANIFEST="/tmp/agent-spec-parallel-$(date +%s)-$$.txt"
: > "$MANIFEST"

echo "Launching $TOTAL parallel instance(s) of $TARGET_NAME" >&2
echo "  Logs: /tmp/agent-spec-parallel-out-$$-{1..$TOTAL}.log" >&2
echo "  Watch: tail -f /tmp/agent-spec-parallel-out-$$-*.log" >&2
echo "" >&2

for i in $(seq 1 "$TOTAL"); do
  IDX=$((i - 1))
  VARIANT="${VARIANTS[$IDX]}"
  IFS='|' read -r V_CONFIG V_MODEL <<< "$VARIANT"

  # Build per-instance flags
  INSTANCE_FLAGS=("${EXTRA_FLAGS[@]}")
  if [[ -n "$V_MODEL" ]]; then
    INSTANCE_FLAGS+=(--model "$V_MODEL")
  fi

  # Build per-instance inject directory if stimuli exist
  INJECT_ARGS=()
  if [[ ${#STIMULI_FILES[@]} -gt 0 ]]; then
    INSTANCE_INJECT="/tmp/agent-spec-inject-$$-$i"
    mkdir -p "$INSTANCE_INJECT"
    STIM_IDX=$(( (i - 1) % ${#STIMULI_FILES[@]} ))
    STIMULUS="${STIMULI_FILES[$STIM_IDX]}"
    cp "$STIMULUS" "$INSTANCE_INJECT/wireframe.png"
    INJECT_ARGS=(--inject "$INSTANCE_INJECT")
  fi

  # Pre-assign port (3100 + instance - 1). Max 11 parallel (3100-3110).
  INSTANCE_PORT=$((3099 + i))
  if [[ $INSTANCE_PORT -gt 3110 ]]; then
    echo "  ERROR: Port pool exhausted (max 11 parallel instances, got $TOTAL)" >&2
    # Stop already-launched instances
    for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
    exit 1
  fi

  # Describe the variant
  DESC="$V_CONFIG"
  [[ -n "$V_MODEL" ]] && DESC="$DESC / $(basename "$V_MODEL")"
  echo "  Instance $i: $DESC (port $INSTANCE_PORT)" >&2

  # Launch
  LAUNCH_ARGS=("$TARGET_NAME" "$V_CONFIG" --port "$INSTANCE_PORT")
  if [[ ${#INSTANCE_FLAGS[@]} -gt 0 ]]; then
    LAUNCH_ARGS+=("${INSTANCE_FLAGS[@]}")
  fi
  if [[ ${#INJECT_ARGS[@]} -gt 0 ]]; then
    LAUNCH_ARGS+=("${INJECT_ARGS[@]}")
  fi
  bash "$PROJECT_DIR/scripts/run-eval.sh" "${LAUNCH_ARGS[@]}" \
    > "/tmp/agent-spec-parallel-out-$$-$i.log" 2>&1 &
  PIDS+=($!)
done

echo "" >&2
echo "Waiting for all instances to complete..." >&2

# Wait and collect results
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
    RESULT=$(grep -o 'RESULT: [A-Z]*' "$LOG" 2>/dev/null | tail -1 || echo "RESULT: UNKNOWN")
    echo "  Instance $i: run=$RUN_ID exit=$EXIT $RESULT" >&2
    if [[ "$RESULT" != *"PASS"* ]]; then
      FAILURES=$((FAILURES + 1))
      # Dump last 15 lines of failed instance log for diagnosis
      echo "  --- Instance $i failure log (last 15 lines) ---" >&2
      tail -15 "$LOG" 2>/dev/null | sed 's/^/    /' >&2
      echo "  --- end ---" >&2
    fi
    # Archive instance log to results
    INSTANCE_RESULTS="$PROJECT_DIR/results/$RUN_ID"
    if [[ -d "$INSTANCE_RESULTS" ]]; then
      cp "$LOG" "$INSTANCE_RESULTS/parallel-instance.log" 2>/dev/null || true
    fi
  else
    echo "  Instance $i: exit=$EXIT (no run_id found)" >&2
    echo "  --- Instance $i failure log (last 15 lines) ---" >&2
    tail -15 "$LOG" 2>/dev/null | sed 's/^/    /' >&2
    echo "  --- end ---" >&2
    FAILURES=$((FAILURES + 1))
  fi
done

# Clean up inject dirs
rm -rf /tmp/agent-spec-inject-$$-* 2>/dev/null || true

echo "" >&2
echo "Manifest: $MANIFEST" >&2
echo "Run IDs:" >&2

for rid in "${RUN_IDS[@]}"; do
  echo "$rid"
done

exit $FAILURES
