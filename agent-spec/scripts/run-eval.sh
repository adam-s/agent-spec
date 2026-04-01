#!/usr/bin/env bash
# run-eval.sh — Run an evaluation by target name.
#
# Usage:
#   scripts/run-eval.sh <target> [config] [options]
#
# Options:
#   --model <name>     Override model
#   --budget <usd>     Override budget
#   --keep             Keep sandbox
#   --inject <dir>     Inject files
#   --port <port>      Use specific port
#
# Config resolution: targets/<target>/configs/<config>/ first,
#                    then targets/_shared/configs/<config>/.
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

TARGET_NAME="${1:?Usage: run-eval.sh <target> [config] [options]}"
shift

CONFIG_NAME="baseline"
if [[ $# -gt 0 ]] && [[ "$1" != --* ]]; then
  CONFIG_NAME="$1"; shift
fi

TARGET_DIR="$PROJECT_DIR/targets/$TARGET_NAME"
require_dir "$TARGET_DIR" "Target not found"

# Resolve config: target-specific first, then _shared
CONFIG_DIR="$TARGET_DIR/configs/$CONFIG_NAME"
if [[ ! -d "$CONFIG_DIR" ]]; then
  CONFIG_DIR="$PROJECT_DIR/targets/_shared/configs/$CONFIG_NAME"
  require_dir "$CONFIG_DIR" "Config '$CONFIG_NAME' not found in target or _shared"
fi

# Parse target.yaml
YAML_FILE="$TARGET_DIR/target.yaml"
require_file "$YAML_FILE" "No target.yaml"
eval "$(parse_target_yaml "$YAML_FILE")"

# Resolve source path
SOURCE_PATH="$(cd "$TARGET_DIR" && cd "$YAML_SOURCE" 2>/dev/null && pwd)" || \
  die "Source repo not found: $YAML_SOURCE (from $TARGET_DIR)"

# Lint: warn on hardcoded ports in prompt.md
if grep -qE '\b3[01][0-9]{2}\b' "$TARGET_DIR/prompt.md" 2>/dev/null; then
  echo "WARNING: prompt.md may contain hardcoded port — use __PORT__" >&2
fi

# Defaults from yaml, overridable by CLI
MODEL="${YAML_MODEL:-$DEFAULT_MODEL}"
BUDGET="${YAML_BUDGET:-$DEFAULT_BUDGET}"
EXTRA_FLAGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)   MODEL="$2"; shift 2 ;;
    --budget)  BUDGET="$2"; shift 2 ;;
    --keep)    EXTRA_FLAGS+=(--keep); shift ;;
    --inject)  EXTRA_FLAGS+=(--inject "$2"); shift 2 ;;
    --port)    EXTRA_FLAGS+=(--port "$2"); shift 2 ;;
    *) die "Unknown option: $1" ;;
  esac
done

# Build invoke args
INVOKE_ARGS=(
  "$SOURCE_PATH"
  "$CONFIG_DIR"
  "$TARGET_DIR/prompt.md"
  --model "$MODEL"
  --budget "$BUDGET"
  --verify "$TARGET_DIR/$YAML_VERIFY"
)

[[ -n "$YAML_DELETE" ]] && INVOKE_ARGS+=(--delete "$YAML_DELETE")
[[ -n "$YAML_SETUP" ]] && INVOKE_ARGS+=(--setup "$YAML_SETUP")
[[ ${#EXTRA_FLAGS[@]} -gt 0 ]] && INVOKE_ARGS+=("${EXTRA_FLAGS[@]}")

exec bash "$SCRIPT_DIR/invoke.sh" "${INVOKE_ARGS[@]}"
