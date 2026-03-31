#!/usr/bin/env bash
# parallel-invoke.sh — Launch N parallel invoke.sh instances for the same target.
#
# Usage:
#   scripts/tuning/parallel-invoke.sh <target> [config] [options]
#
# Options:
#   --instances N          Number of parallel runs (default: 3)
#   --stimuli-dir <path>   Directory of per-instance files to inject (wireframe-1.png, wireframe-2.png, ...)
#   --keep                 Preserve sandboxes after completion
#   --model <name>         Override model
#   --budget <usd>         Override budget
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

INSTANCES=3
STIMULI_DIR=""
EXTRA_FLAGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --instances) INSTANCES="$2"; shift 2 ;;
    --stimuli-dir) STIMULI_DIR="$2"; shift 2 ;;
    --keep) EXTRA_FLAGS+=(--keep); shift ;;
    --model) EXTRA_FLAGS+=(--model "$2"); shift 2 ;;
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

# Collect stimuli files if provided (sorted: wireframe-1.png, wireframe-2.png, ...)
STIMULI_FILES=()
if [[ -n "$STIMULI_DIR" ]] && [[ -d "$STIMULI_DIR" ]]; then
  while IFS= read -r f; do
    STIMULI_FILES+=("$f")
  done < <(ls "$STIMULI_DIR"/* 2>/dev/null | sort)
fi

# Launch N instances
PIDS=()
RUN_IDS=()
MANIFEST="/tmp/agent-spec-parallel-$(date +%s).txt"
: > "$MANIFEST"

echo "Launching $INSTANCES parallel instances of $TARGET_NAME/$CONFIG_NAME" >&2

for i in $(seq 1 "$INSTANCES"); do
  # Build per-instance inject directory if stimuli exist
  INJECT_ARGS=()
  if [[ ${#STIMULI_FILES[@]} -gt 0 ]]; then
    INSTANCE_INJECT="/tmp/agent-spec-inject-$$-$i"
    mkdir -p "$INSTANCE_INJECT"
    # Assign stimulus round-robin
    IDX=$(( (i - 1) % ${#STIMULI_FILES[@]} ))
    STIMULUS="${STIMULI_FILES[$IDX]}"
    # Copy as wireframe.png (generic name the prompt can reference)
    cp "$STIMULUS" "$INSTANCE_INJECT/wireframe.png"
    INJECT_ARGS=(--inject "$INSTANCE_INJECT")
    echo "  Instance $i: injecting $(basename "$STIMULUS")" >&2
  fi

  # Pre-assign port to avoid race condition (3100 + instance index)
  INSTANCE_PORT=$((3099 + i))

  # Launch run-eval.sh in background, capture its output for run_id
  bash "$PROJECT_DIR/scripts/run-eval.sh" "$TARGET_NAME" "$CONFIG_NAME" \
    --port "$INSTANCE_PORT" \
    "${EXTRA_FLAGS[@]}" \
    "${INJECT_ARGS[@]}" \
    > "/tmp/agent-spec-parallel-out-$$-$i.log" 2>&1 &
  PIDS+=($!)
  echo "  Instance $i: PID $!" >&2
done

echo "" >&2
echo "Waiting for all instances to complete..." >&2

# Wait and collect results
FAILURES=0
for i in $(seq 1 "$INSTANCES"); do
  IDX=$((i - 1))
  PID="${PIDS[$IDX]}"
  LOG="/tmp/agent-spec-parallel-out-$$-$i.log"

  set +e
  wait "$PID"
  EXIT=$?
  set -e

  # Extract run_id from log (invoke.sh prints "=== agent-spec run: XXXXXXXX ===")
  RUN_ID=$(grep -o 'agent-spec run: [a-f0-9]\{8\}' "$LOG" 2>/dev/null | head -1 | awk '{print $NF}')

  if [[ -n "$RUN_ID" ]]; then
    RUN_IDS+=("$RUN_ID")
    echo "$RUN_ID" >> "$MANIFEST"

    # Extract result
    RESULT=$(grep -o 'RESULT: [A-Z]*' "$LOG" 2>/dev/null | tail -1 || echo "RESULT: UNKNOWN")
    echo "  Instance $i: run=$RUN_ID exit=$EXIT $RESULT" >&2
  else
    echo "  Instance $i: exit=$EXIT (no run_id found)" >&2
    FAILURES=$((FAILURES + 1))
  fi
done

# Clean up inject dirs
rm -rf /tmp/agent-spec-inject-$$-* 2>/dev/null || true

echo "" >&2
echo "Manifest: $MANIFEST" >&2
echo "Run IDs:" >&2

# Print run_ids to stdout (the parseable output)
for rid in "${RUN_IDS[@]}"; do
  echo "$rid"
done

exit $FAILURES
