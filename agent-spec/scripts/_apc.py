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
