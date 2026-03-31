#!/usr/bin/env bash
# run-eval.sh — Run an evaluation by target name.
#
# Usage:
#   scripts/run-eval.sh <target> [config]           # default config: baseline
#   scripts/run-eval.sh <target> [config] [options]
#
# Options:
#   --model <name>     Override model
#   --budget <usd>     Override budget
#   --keep             Keep sandbox after completion
#
# Examples:
#   scripts/run-eval.sh csv-reporter
#   scripts/run-eval.sh csv-reporter token-efficient
#   scripts/run-eval.sh hono-websocket-counter baseline --model claude-haiku-4-5-20251001
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET_NAME="${1:?Usage: run-eval.sh <target> [config] [options]}"
shift

# Config name (default: baseline) — grab it if it doesn't start with --
CONFIG_NAME="baseline"
if [[ $# -gt 0 ]] && [[ "$1" != --* ]]; then
  CONFIG_NAME="$1"
  shift
fi

TARGET_DIR="$PROJECT_DIR/targets/$TARGET_NAME"
if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Target not found: $TARGET_DIR" >&2
  echo "Available targets:" >&2
  ls "$PROJECT_DIR/targets/" 2>/dev/null | sed 's/^/  /' >&2
  exit 1
fi

CONFIG_DIR="$TARGET_DIR/configs/$CONFIG_NAME"
if [[ ! -d "$CONFIG_DIR" ]]; then
  echo "Config not found: $CONFIG_DIR" >&2
  echo "Available configs for $TARGET_NAME:" >&2
  ls "$TARGET_DIR/configs/" 2>/dev/null | sed 's/^/  /' >&2
  exit 1
fi

# Parse target.yaml with python (handles YAML properly, no deps beyond stdlib on 3.x)
YAML_FILE="$TARGET_DIR/target.yaml"
if [[ ! -f "$YAML_FILE" ]]; then
  echo "No target.yaml found in $TARGET_DIR" >&2
  exit 1
fi

# Extract fields from target.yaml using Python
eval "$(YAML_PATH="$YAML_FILE" python3 << 'PYEOF'
import re, os

text = open(os.environ["YAML_PATH"]).read()

def get(key, default=""):
    m = re.search(r"^" + key + r":\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else default

def get_list(key):
    m = re.search(r"^" + key + r":\s*\n((?:\s+-\s+.+\n)*)", text, re.MULTILINE)
    if not m: return []
    return [line.strip().lstrip("- ") for line in m.group(1).strip().split("\n") if line.strip()]

def get_nested(parent, key, default=""):
    m = re.search(r"^" + parent + r":\s*\n(?:.*\n)*?\s+" + key + r":\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else default

source = get("source")
verify = get("verify", "verify.sh")
model = get_nested("agent", "model", "claude-sonnet-4-6")
budget = get_nested("agent", "budget", "2.00")
delete_files = get_list("delete_before_run")
setup_cmds = get_list("setup")

print('YAML_SOURCE="' + source + '"')
print('YAML_VERIFY="' + verify + '"')
print('YAML_MODEL="' + model + '"')
print('YAML_BUDGET="' + budget + '"')
print('YAML_DELETE="' + ",".join(delete_files) + '"')
print('YAML_SETUP="' + ";".join(setup_cmds) + '"')
PYEOF
)"

# Resolve source path relative to target directory
SOURCE_PATH="$(cd "$TARGET_DIR" && cd "$YAML_SOURCE" 2>/dev/null && pwd)" || {
  echo "Source repo not found: $YAML_SOURCE (resolved from $TARGET_DIR)" >&2
  exit 1
}

# CLI overrides
MODEL="$YAML_MODEL"
BUDGET="$YAML_BUDGET"
EXTRA_FLAGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model) MODEL="$2"; shift 2 ;;
    --budget) BUDGET="$2"; shift 2 ;;
    --keep) EXTRA_FLAGS+=(--keep); shift ;;
    --inject) EXTRA_FLAGS+=(--inject "$2"); shift 2 ;;
    --port) EXTRA_FLAGS+=(--port "$2"); shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# Build invoke.sh command
INVOKE_ARGS=(
  "$SOURCE_PATH"
  "$CONFIG_DIR"
  "$TARGET_DIR/prompt.md"
  --model "$MODEL"
  --budget "$BUDGET"
  --verify "$TARGET_DIR/$YAML_VERIFY"
)

if [[ -n "$YAML_DELETE" ]]; then
  INVOKE_ARGS+=(--delete "$YAML_DELETE")
fi

if [[ -n "$YAML_SETUP" ]]; then
  INVOKE_ARGS+=(--setup "$YAML_SETUP")
fi

if [[ ${#EXTRA_FLAGS[@]} -gt 0 ]]; then
  INVOKE_ARGS+=("${EXTRA_FLAGS[@]}")
fi

# Run
exec bash "$SCRIPT_DIR/apc/invoke.sh" "${INVOKE_ARGS[@]}"
