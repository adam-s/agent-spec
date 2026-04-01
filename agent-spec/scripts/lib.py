"""Shared library for agent-spec. All constants, logging, port management, parsing."""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────

PORT_MIN = 3100
PORT_MAX = 3110
TIMEOUT_DEFAULT = 600
REGRESSION_COST_THRESHOLD = 50   # percent
REGRESSION_TOKEN_THRESHOLD = 50  # percent

SANDBOX_ROOT = Path("/tmp/claude/agent-spec")
RUN_ROOT = Path("/tmp/agent-spec")
PID_FILE = Path("/tmp/agent-spec-pids.txt")

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_BUDGET = "2.00"

SCRIPTS_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPTS_DIR.parent


# ── Validation ────────────────────────────────────────────────────

def die(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def require_file(path: str | Path, msg: str = "File not found"):
    if not Path(path).is_file():
        die(f"{msg}: {path}")


def require_dir(path: str | Path, msg: str = "Directory not found"):
    if not Path(path).is_dir():
        die(f"{msg}: {path}")


# ── Logging ───────────────────────────────────────────────────────

def apc_log(level: str, event: str, msg: str, data: dict | None = None,
            run_id: str | None = None):
    rid = run_id or os.environ.get("AGENT_SPEC_RUN_ID", "unknown")
    log_dir = RUN_ROOT / rid
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "level": level,
        "src": Path(sys.argv[0]).name if sys.argv else "unknown",
        "event": event,
        "msg": msg,
        "data": data or {},
    }
    with open(log_dir / "events.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


_DEBUG_ENABLED = os.environ.get("AGENT_SPEC_DEBUG", "1") != "0"


def debug(tag: str, msg: str, data=None, run_id: str | None = None):
    """Developer debug logging — stderr + events.jsonl with level DEBUG."""
    if not _DEBUG_ENABLED:
        return
    resolved = data() if callable(data) else data
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] [{tag}] {msg}"
    if resolved:
        line += f"  {json.dumps(resolved, default=str)}"
    print(f"\033[2m{line}\033[0m", file=sys.stderr)
    apc_log("DEBUG", f"debug:{tag}", msg, resolved or {}, run_id=run_id)


# ── Port Management ──────────────────────────────────────────────

def allocate_port(requested: int | None = None) -> int:
    if requested is not None:
        return requested
    for p in range(PORT_MIN, PORT_MAX + 1):
        result = subprocess.run(["lsof", f"-ti:{p}"], capture_output=True)
        if result.returncode != 0:  # port is free
            return p
    die(f"No free port in range {PORT_MIN}-{PORT_MAX}")


def release_port(port: int):
    result = subprocess.run(["lsof", f"-ti:{port}"], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        for pid in result.stdout.strip().split("\n"):
            try:
                os.kill(int(pid), 9)
            except (ProcessLookupError, ValueError):
                pass


# ── Process Management ────────────────────────────────────────────

def track_pid(pid: int, port: int = 0, purpose: str = "unknown"):
    with open(PID_FILE, "a") as f:
        f.write(f"{pid}|{port}|{purpose}\n")


def stop_tracked_pids():
    if not PID_FILE.exists():
        return
    for line in PID_FILE.read_text().splitlines():
        parts = line.strip().split("|")
        if len(parts) >= 1 and parts[0]:
            try:
                pid = int(parts[0])
                os.kill(pid, signal.SIGTERM)
                purpose = parts[2] if len(parts) > 2 else "unknown"
                port = parts[1] if len(parts) > 1 else "?"
                print(f"  Stopped: PID {pid} ({purpose}) port {port}")
            except (ProcessLookupError, ValueError):
                pass
    PID_FILE.write_text("")


# ── YAML Parsing ─────────────────────────────────────────────────

def parse_target_yaml(path: str | Path) -> dict:
    """Parse target.yaml using regex. Returns dict with keys:
    source, verify, model, budget, delete_before_run, setup"""
    text = Path(path).read_text()

    def get(key, default=""):
        m = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
        return m.group(1).strip().strip("'\"") if m else default

    def get_list(key):
        m = re.search(rf"^{key}:\s*\n((?:\s+-\s+.+\n)*)", text, re.MULTILINE)
        if not m:
            return []
        return [line.strip().lstrip("- ") for line in m.group(1).strip().split("\n") if line.strip()]

    def get_nested(parent, key, default=""):
        m = re.search(rf"^{parent}:\s*\n(?:.*\n)*?\s+{key}:\s*(.+)$", text, re.MULTILINE)
        return m.group(1).strip().strip("'\"") if m else default

    return {
        "source": get("source"),
        "verify": get("verify", "verify.sh"),
        "model": get_nested("agent", "model", ""),
        "budget": get_nested("agent", "budget", ""),
        "delete_before_run": get_list("delete_before_run"),
        "setup": get_list("setup"),
    }


# ── Output Parsing ───────────────────────────────────────────────

def parse_output_json(path: str | Path) -> dict:
    """Parse Claude's output.json and extract token metrics."""
    try:
        data = json.loads(Path(path).read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

    # modelUsage may be {model_name: {inputTokens:...}} or flat
    mu = data.get("modelUsage", {})
    if mu and "inputTokens" not in mu:
        mu = next(iter(mu.values()), {})

    u = data.get("usage", {})
    return {
        "input": mu.get("inputTokens", u.get("input_tokens", 0)),
        "output": mu.get("outputTokens", u.get("output_tokens", 0)),
        "cache_create": mu.get("cacheCreationInputTokens", u.get("cache_creation_input_tokens", 0)),
        "cache_read": mu.get("cacheReadInputTokens", u.get("cache_read_input_tokens", 0)),
        "cost_usd": round(data.get("total_cost_usd", mu.get("costUSD", 0)), 4),
        "turns": data.get("num_turns", 0),
    }


# ── Events ───────────────────────────────────────────────────────

def load_events(path: str | Path) -> list[dict]:
    """Load events.jsonl, skipping malformed lines."""
    events = []
    for line in Path(path).read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def get_event(events: list[dict], event_name: str) -> dict | None:
    """Get the last event matching event_name."""
    for e in reversed(events):
        if e.get("event") == event_name:
            return e
    return None


# ── Timing ───────────────────────────────────────────────────────

def now_ms() -> int:
    return int(time.time() * 1000)
