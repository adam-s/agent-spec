#!/usr/bin/env bash
# lib.sh — Shared APC logging function for all agent-spec scripts.
# Source this file: source "$(dirname "$0")/../apc/lib.sh"

apc_log() {
  local level="$1" event="$2" msg="$3"
  local data
  data="${4:-"{}"}"
  local log_dir="/tmp/agent-spec/${AGENT_SPEC_RUN_ID:-unknown}"
  mkdir -p "$log_dir"
  _APC_LEVEL="$level" _APC_EVENT="$event" _APC_MSG="$msg" _APC_DATA="$data" \
    _APC_SRC="$(basename "$0")" \
    python3 -c '
import json, os, sys
from datetime import datetime, timezone
ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
entry = {"ts": ts, "level": os.environ["_APC_LEVEL"], "src": os.environ["_APC_SRC"],
         "event": os.environ["_APC_EVENT"], "msg": os.environ["_APC_MSG"],
         "data": json.loads(os.environ["_APC_DATA"])}
print(json.dumps(entry))
' >> "$log_dir/events.jsonl"
}
