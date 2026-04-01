#!/usr/bin/env bash
# lib.sh — Shared functions for agent-spec. Source this after config.sh.
#
# Provides: apc_log, allocate_port, release_port, track_pid, cleanup,
#           require_file, require_dir, die

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# --- Validation ---

die() {
  echo "ERROR: $*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || die "$2: $1"
}

require_dir() {
  [[ -d "$1" ]] || die "$2: $1"
}

# --- Logging ---

apc_log() {
  local level="$1" event="$2" msg="$3" data="${4:-"{}"}"
  local log_dir="$RUN_ROOT/${AGENT_SPEC_RUN_ID:-unknown}"
  mkdir -p "$log_dir"
  _APC_LEVEL="$level" _APC_EVENT="$event" _APC_MSG="$msg" _APC_DATA="$data" \
    _APC_SRC="$(basename "$0")" \
    python3 -c '
import json, os
from datetime import datetime, timezone
ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
entry = {"ts": ts, "level": os.environ["_APC_LEVEL"], "src": os.environ["_APC_SRC"],
         "event": os.environ["_APC_EVENT"], "msg": os.environ["_APC_MSG"],
         "data": json.loads(os.environ["_APC_DATA"])}
print(json.dumps(entry))
' >> "$log_dir/events.jsonl"
}

# --- Port Management ---

allocate_port() {
  # Returns the first free port in [PORT_MIN, PORT_MAX]. Prints port to stdout.
  # If a specific port is requested as $1, validates and returns it.
  if [[ -n "${1:-}" ]]; then
    echo "$1"
    return 0
  fi
  for p in $(seq "$PORT_MIN" "$PORT_MAX"); do
    if ! lsof -ti:"$p" >/dev/null 2>&1; then
      echo "$p"
      return 0
    fi
  done
  die "No free port in range $PORT_MIN-$PORT_MAX"
}

release_port() {
  local port="$1"
  local pids
  pids=$(lsof -ti:"$port" 2>/dev/null) || true
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill -9 2>/dev/null || true
  fi
}

# --- Process Management ---

track_pid() {
  local pid="$1" port="${2:-0}" purpose="${3:-unknown}"
  echo "$pid|$port|$purpose" >> "$PID_FILE"
}

stop_tracked_pids() {
  [[ -f "$PID_FILE" ]] || return 0
  while IFS='|' read -r pid port purpose; do
    [[ -z "$pid" ]] && continue
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      echo "  Stopped: PID $pid ($purpose) port $port"
    fi
  done < "$PID_FILE"
  : > "$PID_FILE"
}

# --- Cleanup ---

# Call setup_cleanup after setting SANDBOX and SIDECAR_PID variables.
# This installs an EXIT trap that cleans up everything.
_CLEANUP_KEEP=false
_CLEANUP_SANDBOX=""
_CLEANUP_SIDECAR_PID=""

setup_cleanup() {
  _CLEANUP_SANDBOX="${1:-}"
  _CLEANUP_KEEP="${2:-false}"
  trap '_do_cleanup' EXIT
  trap '_handle_signal SIGTERM' TERM
  trap '_handle_signal SIGINT' INT
  trap '_handle_signal SIGHUP' HUP
}

set_sidecar_pid() {
  _CLEANUP_SIDECAR_PID="$1"
}

_handle_signal() {
  apc_log "ERROR" "run_terminated" "Run terminated by $1" \
    "{\"signal\":\"$1\",\"run_id\":\"${AGENT_SPEC_RUN_ID:-unknown}\"}"
  exit 1
}

_archive_run() {
  # Archive logs from /tmp to results/ — runs on ANY exit so data survives.
  # Globals: RUN_DIR, RESULTS_DIR, _CLEANUP_SANDBOX (set by invoke.sh)
  local run_dir="${RUN_DIR:-}"
  local results_dir="${RESULTS_DIR:-}"
  local sandbox="${_CLEANUP_SANDBOX:-}"

  [[ -z "$results_dir" ]] && return 0
  mkdir -p "$results_dir"

  # Archive run logs
  for artifact in events.jsonl output.json stderr.log; do
    [[ -f "$run_dir/$artifact" ]] && cp "$run_dir/$artifact" "$results_dir/" 2>/dev/null
  done

  # Archive produced files from sandbox (if it still exists)
  if [[ -n "$sandbox" ]] && [[ -d "$sandbox" ]]; then
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      mkdir -p "$results_dir/produced/$(dirname "$f")"
      cp "$sandbox/$f" "$results_dir/produced/$f" 2>/dev/null
    done < <(cd "$sandbox" && find . -maxdepth 3 \( -name '*.py' -o -name '*.js' -o -name '*.ts' \) \
      ! -path '*/node_modules/*' ! -name '_apc.*' 2>/dev/null)
  fi
}

_do_cleanup() {
  # Archive first, then clean up
  _archive_run

  # Stop sidecar
  if [[ -n "$_CLEANUP_SIDECAR_PID" ]]; then
    kill "$_CLEANUP_SIDECAR_PID" 2>/dev/null || true
    wait "$_CLEANUP_SIDECAR_PID" 2>/dev/null || true
  fi
  # Remove sandbox
  if [[ "$_CLEANUP_KEEP" = false ]] && [[ -n "$_CLEANUP_SANDBOX" ]]; then
    rm -rf "$_CLEANUP_SANDBOX"
  fi
}

# --- YAML Parsing ---

parse_target_yaml() {
  # Parse target.yaml robustly using Python. Sets variables via eval.
  # Usage: eval "$(parse_target_yaml path/to/target.yaml)"
  local yaml_file="$1"
  YAML_PATH="$yaml_file" python3 << 'PYEOF'
import re, os, sys

try:
    text = open(os.environ["YAML_PATH"]).read()
except FileNotFoundError:
    print('echo "ERROR: target.yaml not found" >&2; exit 1')
    sys.exit(0)

def get(key, default=""):
    m = re.search(r"^" + key + r":\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip().strip('"').strip("'") if m else default

def get_list(key):
    m = re.search(r"^" + key + r":\s*\n((?:\s+-\s+.+\n)*)", text, re.MULTILINE)
    if not m: return []
    return [line.strip().lstrip("- ") for line in m.group(1).strip().split("\n") if line.strip()]

def get_nested(parent, key, default=""):
    m = re.search(r"^" + parent + r":\s*\n(?:.*\n)*?\s+" + key + r":\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip().strip('"').strip("'") if m else default

source = get("source")
verify = get("verify", "verify.sh")
model = get_nested("agent", "model", "")
budget = get_nested("agent", "budget", "")
delete_files = get_list("delete_before_run")
setup_cmds = get_list("setup")

# Shell-safe output
print(f'YAML_SOURCE="{source}"')
print(f'YAML_VERIFY="{verify}"')
print(f'YAML_MODEL="{model}"')
print(f'YAML_BUDGET="{budget}"')
print(f'YAML_DELETE="{",".join(delete_files)}"')
print(f'YAML_SETUP="{";".join(setup_cmds)}"')
PYEOF
}

# --- Timing ---

now_ms() {
  python3 -c "import time; print(int(time.time()*1000))"
}
