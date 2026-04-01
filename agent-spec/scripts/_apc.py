"""Lightweight APC emitter for Python sandboxes. Zero dependencies."""

import json
import os
import sys
from datetime import datetime, timezone

_RUN_ID = os.environ.get("AGENT_SPEC_RUN_ID", "unknown")
_LOG = f"/tmp/agent-spec/{_RUN_ID}/events.jsonl"


def log(level, event, msg, data=None, src=None):
    os.makedirs(os.path.dirname(_LOG), exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
        "level": level,
        "src": src or os.path.basename(sys.argv[0]),
        "event": event,
        "msg": msg,
        "data": data or {},
    }
    with open(_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


_DEBUG_ENABLED = os.environ.get("AGENT_SPEC_DEBUG", "1") != "0"


def debug(tag, msg, data=None):
    """Developer debug logging — stderr + events.jsonl with level DEBUG."""
    if not _DEBUG_ENABLED:
        return
    resolved = data() if callable(data) else data
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] [{tag}] {msg}"
    if resolved:
        line += f"  {json.dumps(resolved, default=str)}"
    print(f"\033[2m{line}\033[0m", file=sys.stderr)
    log(f"DEBUG", f"debug:{tag}", msg, resolved or {})
