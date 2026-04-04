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

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_BUDGET = "5.00"

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
    """Register a PID for cleanup. Called for every process we spawn."""
    with open(PID_FILE, "a") as f:
        f.write(f"{pid}|{port}|{purpose}\n")


def _pid_alive(pid: int) -> bool:
    """Check if a process is still running."""
    try:
        os.kill(pid, 0)  # signal 0 = check existence
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _stop_pid(pid: int, purpose: str = "", timeout: float = 5) -> bool:
    """Stop a process: SIGTERM → wait → SIGKILL. Returns True if stopped."""
    if not _pid_alive(pid):
        return True
    try:
        # Try SIGTERM first
        os.kill(pid, signal.SIGTERM)
        deadline = time.time() + timeout
        while time.time() < deadline and _pid_alive(pid):
            time.sleep(0.2)
        # Escalate to SIGKILL if still alive
        if _pid_alive(pid):
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)
        label = f" ({purpose})" if purpose else ""
        if not _pid_alive(pid):
            print(f"  Stopped: PID {pid}{label}")
            return True
        else:
            print(f"  WARNING: PID {pid}{label} did not stop", file=sys.stderr)
            return False
    except (ProcessLookupError, PermissionError):
        return True


def _stop_process_tree(pid: int, purpose: str = "", timeout: float = 5):
    """Stop a process and all its children (bottom-up)."""
    # Find children first
    try:
        result = subprocess.run(
            ["pgrep", "-P", str(pid)], capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            for child_pid in result.stdout.strip().split("\n"):
                if child_pid.strip():
                    _stop_process_tree(int(child_pid.strip()), f"child of {pid}", timeout)
    except (subprocess.TimeoutExpired, ValueError):
        pass
    # Then stop the parent
    _stop_pid(pid, purpose, timeout)


def stop_tracked_pids():
    """Stop all tracked processes and their children. Clears the registry."""
    if not PID_FILE.exists():
        return
    for line in PID_FILE.read_text().splitlines():
        parts = line.strip().split("|")
        if len(parts) >= 1 and parts[0]:
            try:
                pid = int(parts[0])
                purpose = parts[2] if len(parts) > 2 else "unknown"
                _stop_process_tree(pid, purpose)
            except ValueError:
                pass
    PID_FILE.write_text("")


def get_tracked_pids() -> list[dict]:
    """Return list of tracked PIDs with their status."""
    if not PID_FILE.exists():
        return []
    pids = []
    for line in PID_FILE.read_text().splitlines():
        parts = line.strip().split("|")
        if len(parts) >= 1 and parts[0]:
            try:
                pid = int(parts[0])
                pids.append({
                    "pid": pid,
                    "port": parts[1] if len(parts) > 1 else "?",
                    "purpose": parts[2] if len(parts) > 2 else "unknown",
                    "alive": _pid_alive(pid),
                })
            except ValueError:
                pass
    return pids


# ── EVAL.md Parsing ──────────────────────────────────────────────

def parse_eval_md(path: str | Path) -> dict:
    """Parse EVAL.md frontmatter (YAML between --- delimiters).
    Returns dict with keys: source, verify, model, budget, delete, setup, prompt.
    Also supports legacy target.yaml format for backwards compatibility."""
    text = Path(path).read_text()

    # Check if this is EVAL.md (frontmatter) or legacy target.yaml
    if text.strip().startswith("---"):
        # EVAL.md format: split on --- delimiters
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            prompt = parts[2].strip()
        else:
            frontmatter = parts[1] if len(parts) > 1 else ""
            prompt = ""
    else:
        # Legacy target.yaml format
        frontmatter = text
        prompt = ""

    def get(key, default=""):
        m = re.search(rf"^{key}:\s*(.+)$", frontmatter, re.MULTILINE)
        return m.group(1).strip().strip("'\"") if m else default

    def get_list(key):
        # Try both 'key' and legacy 'delete_before_run'
        m = re.search(rf"^{key}:\s*\n((?:\s+-\s+.+\n)*)", frontmatter, re.MULTILINE)
        if not m:
            return []
        return [line.strip().lstrip("- ") for line in m.group(1).strip().split("\n") if line.strip()]

    def get_nested(parent, key, default=""):
        m = re.search(rf"^{parent}:\s*\n(?:.*\n)*?\s+{key}:\s*(.+)$", frontmatter, re.MULTILINE)
        return m.group(1).strip().strip("'\"") if m else default

    # Support both 'delete' (new) and 'delete_before_run' (legacy)
    delete = get_list("delete") or get_list("delete_before_run")

    return {
        "source": get("source"),
        "verify": get("verify", "verify.sh"),
        "model": get("model") or get_nested("agent", "model", ""),
        "budget": get("budget") or get_nested("agent", "budget", ""),
        "delete": delete,
        "setup": get_list("setup"),
        "prompt": prompt,
    }


# Keep old name as alias during migration
parse_target_yaml = parse_eval_md


# ── Output Parsing ───────────────────────────────────────────────

def parse_output_json(path: str | Path) -> dict:
    """Parse Claude's output.json and extract metrics.

    Extracts token counts, cost, timing, stop reason, session info,
    and permission denials from Claude CLI's JSON output.
    """
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
        # Token counts
        "input": mu.get("inputTokens", u.get("input_tokens", 0)),
        "output": mu.get("outputTokens", u.get("output_tokens", 0)),
        "cache_create": mu.get("cacheCreationInputTokens", u.get("cache_creation_input_tokens", 0)),
        "cache_read": mu.get("cacheReadInputTokens", u.get("cache_read_input_tokens", 0)),
        "cost_usd": round(data.get("total_cost_usd", mu.get("costUSD", 0)), 4),
        "turns": data.get("num_turns", 0),
        # Timing
        "duration_ms": data.get("duration_ms", 0),
        "duration_api_ms": data.get("duration_api_ms", 0),
        # Execution metadata
        "stop_reason": data.get("stop_reason", ""),
        "session_id": data.get("session_id", ""),
        "is_error": data.get("is_error", False),
        "result_message": (data.get("result", "") or "")[:500],
        "permission_denials": data.get("permission_denials", []),
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


def find_session_runs(session_id: str) -> dict[int, list[str]]:
    """Find all run_ids belonging to an iterate session, grouped by depth."""
    depth_runs: dict[int, list[str]] = {}
    if not RUN_ROOT.exists():
        return depth_runs
    for run_dir in RUN_ROOT.iterdir():
        events_file = run_dir / "events.jsonl"
        if not events_file.exists():
            continue
        events = load_events(events_file)
        for e in events:
            if (e.get("event") == "iteration_started"
                    and e.get("data", {}).get("session_id", "").startswith(session_id)):
                depth = e["data"].get("depth", 0)
                for e2 in events:
                    if e2.get("event") == "instance_complete":
                        child_id = e2["data"].get("run_id")
                        if child_id:
                            depth_runs.setdefault(depth, []).append(child_id)
                break
    return depth_runs


# ── Timing ───────────────────────────────────────────────────────

def now_ms() -> int:
    return int(time.time() * 1000)


# ── Discovery ───────────────────────────────────────────────────

def list_evals() -> list[str]:
    """Return sorted list of eval names (directories with EVAL.md)."""
    evals_dir = PROJECT_DIR / "evals"
    if not evals_dir.is_dir():
        return []
    return sorted(
        d.name for d in evals_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "EVAL.md").exists()
    )


# Keep old name as alias during migration
list_targets = list_evals


def list_configs(eval_name: str) -> list[str]:
    """Return sorted list of config names for an eval."""
    evals_dir = PROJECT_DIR / "evals"
    tc = evals_dir / eval_name / "configs"
    if not tc.is_dir():
        return []
    return sorted(d.name for d in tc.iterdir() if d.is_dir())


# ── ANSI Colors ─────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[90m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

_IS_TTY = sys.stderr.isatty()

def _color(code: str, text: str) -> str:
    return f"{code}{text}{RESET}" if _IS_TTY else text


# ── Output ──────────────────────────────────────────────────────

def print_result_line(target: str, config: str, result: str,
                      duration_s: float | None = None, cost_usd: float | None = None):
    """Print a standardized one-line result summary."""
    if result == "PASS":
        icon = _color(GREEN, "\u2713")
        result_str = _color(GREEN, result)
    elif result == "FAIL":
        icon = _color(RED, "\u2717")
        result_str = _color(RED, result)
    else:
        icon = "?"
        result_str = result
    line = f"  {icon} {target}/{config}: {result_str}"
    if duration_s is not None:
        line += f"  ({duration_s:.0f}s)"
    if cost_usd is not None:
        line += f"  ${cost_usd:.2f}"
    print(line)


# ── Results Discovery ──────────────────────────────────────────

def find_results_dir(run_id: str) -> Path | None:
    """Find a run's results dir by searching evals/*/results/ then flat results/."""
    evals_dir = PROJECT_DIR / "evals"
    if evals_dir.is_dir():
        for eval_dir in evals_dir.iterdir():
            if not eval_dir.is_dir():
                continue
            candidate = eval_dir / "results" / run_id
            if candidate.is_dir():
                return candidate
    flat = PROJECT_DIR / "results" / run_id
    if flat.is_dir():
        return flat
    return None


# ── Baseline Cost ───────────────────────────────────────────────

def get_baseline_cost(target: str, config: str, max_runs: int = 10) -> float | None:
    """Return median cost of recent runs for this target/config."""
    if not RUN_ROOT.exists():
        return None
    costs = []
    dirs = sorted(RUN_ROOT.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True)
    for d in dirs[:50]:
        events_file = d / "events.jsonl"
        if not events_file.exists():
            continue
        events = load_events(events_file)
        started = get_event(events, "agent_started")
        if not started:
            continue
        data = started.get("data", {})
        if data.get("target") == target and data.get("config") == config:
            token = get_event(events, "token_update")
            if token:
                costs.append(token["data"].get("cost_usd", 0))
                if len(costs) >= max_runs:
                    break
    if not costs:
        return None
    costs.sort()
    mid = len(costs) // 2
    return costs[mid] if len(costs) % 2 else (costs[mid - 1] + costs[mid]) / 2


# ── Live Status ─────────────────────────────────────────────────

_SPINNER = ["\u280b", "\u2819", "\u2838", "\u2830", "\u2826", "\u2807"]


class StatusLine:
    """In-place updating status line for terminal output."""

    def __init__(self, label: str, budget: float | None = None,
                 baseline_cost: float | None = None):
        self.label = label
        self.budget = budget
        self.baseline_cost = baseline_cost
        self.start = time.time()
        self.cost = 0.0
        self.tokens_in = 0
        self.tokens_out = 0
        self.finished = False
        self._is_tty = sys.stderr.isatty()
        self._tick = 0
        self._last_print_time = 0.0

    def update(self, cost: float = 0.0, tokens_in: int = 0, tokens_out: int = 0):
        """Update metrics and rewrite the status line."""
        if self.finished:
            return
        if cost:
            self.cost = cost
        if tokens_in:
            self.tokens_in = tokens_in
        if tokens_out:
            self.tokens_out = tokens_out

        now = time.time()
        if self._is_tty:
            self._tick += 1
            spinner = _SPINNER[self._tick % len(_SPINNER)]
            line = self._render(spinner)
            print(f"\r{line}\033[K", end="", file=sys.stderr, flush=True)
        else:
            # Non-TTY: print a line every 30s
            if now - self._last_print_time >= 30:
                self._last_print_time = now
                elapsed = now - self.start
                parts = [f"  {self.label}: {elapsed:.0f}s"]
                if self.cost:
                    parts.append(f"${self.cost:.2f}")
                print("  ".join(parts), file=sys.stderr)

    def finish(self, result: str, cost: float | None = None,
               duration_s: float | None = None, total_tokens: int | None = None):
        """Print the final result line."""
        if self.finished:
            return
        self.finished = True
        if cost is not None:
            self.cost = cost
        if total_tokens is not None:
            self.total_tokens = total_tokens
        else:
            self.total_tokens = self.tokens_in + self.tokens_out
        if duration_s is None:
            duration_s = time.time() - self.start

        if result == "PASS":
            icon = _color(GREEN, "\u2713")
            result_str = _color(GREEN, result)
        elif result == "FAIL":
            icon = _color(RED, "\u2717")
            result_str = _color(RED, result)
        else:
            icon = "?"
            result_str = result

        line = f"  {icon} {self.label}: {result_str}  ({duration_s:.0f}s)"
        if self.total_tokens:
            line += f"  {self.total_tokens:,}tok"

        if self._is_tty:
            print(f"\r{line}\033[K", file=sys.stderr)
        else:
            print(line, file=sys.stderr)

    def _render(self, spinner: str) -> str:
        elapsed = time.time() - self.start
        line = f"  {spinner} {self.label}  {elapsed:.0f}s"
        if self.cost:
            line += f"  ${self.cost:.2f}"
            if self.budget:
                line += f" / ${self.budget:.2f}"
            if self.baseline_cost and self.cost > self.baseline_cost * 2:
                warn = _color(YELLOW, f"\u26a0 {self.cost/self.baseline_cost:.1f}x baseline")
                line += f"  {warn}"
        elif self.budget:
            line += f"  $0.00 / ${self.budget:.2f}"
        return line


# ── Event Rendering ────────────────────────────────────────────

def render_event(event: dict, status: StatusLine | None = None, verbose: bool = False):
    """Render a single event to stderr for human display.

    This is the single place where events become terminal output.
    invoke.py and parallel.py call this instead of scattered print() calls.
    """
    ev = event.get("event", "")
    data = event.get("data", {})

    if ev == "run_started":
        target = data.get("target", "?")
        config = data.get("config", "?")
        model = data.get("model", "?")
        run_id = data.get("run_id", "?")
        budget = data.get("budget", "?")
        print(f"── {target}/{config} ({model}) ──", file=sys.stderr)
        print(f"  Run:    {run_id}", file=sys.stderr)
        print(f"  Budget: ${budget}", file=sys.stderr)
        if verbose:
            print(f"  Port:   {data.get('port', '?')}", file=sys.stderr)
            print(f"  Log:    {RUN_ROOT / run_id}/events.jsonl", file=sys.stderr)
        print(file=sys.stderr)

    elif ev == "preflight_check" and verbose:
        print(f"  Resources: {data.get('overall', '?')} — "
              f"CPU {data.get('cpu', 0)}% Mem {data.get('mem', 0)}% "
              f"Disk {data.get('disk_free_gb', 0)}GB", file=sys.stderr)

    elif ev == "files_deleted" and verbose:
        print(f"  Deleted: {data.get('files', '')}", file=sys.stderr)

    elif ev == "setup_command" and verbose:
        print(f"  Setup: {data.get('cmd', '')}", file=sys.stderr)

    elif ev == "resource_snapshot" and status:
        status.update()

    elif ev == "token_update" and status:
        status.update(cost=data.get("cost_usd", 0),
                      tokens_in=data.get("input", 0),
                      tokens_out=data.get("output", 0))

    elif ev == "verification_output" and verbose:
        output = data.get("output", "").strip()
        if output:
            print(f"\n  {DIM}── verify ──{RESET}" if _IS_TTY else "\n  -- verify --",
                  file=sys.stderr)
            for line in output.splitlines():
                print(f"  {DIM}{line}{RESET}" if _IS_TTY else f"  {line}",
                      file=sys.stderr)

    elif ev == "test_passed" and verbose:
        print(f"  {_color(GREEN, '✓')} {data.get('test_name', '')}", file=sys.stderr)

    elif ev == "test_failed" and verbose:
        print(f"  {_color(RED, '✗')} {data.get('test_name', '')}", file=sys.stderr)

    elif ev == "run_finished" and status:
        status.finish(data.get("result", "?"),
                      cost=data.get("cost_usd"),
                      duration_s=data.get("duration_s"),
                      total_tokens=data.get("total_tokens"))

    elif ev == "run_finished" and not status:
        # Fallback when no StatusLine (e.g. non-interactive)
        print_result_line(data.get("target", "?"), data.get("config", "?"),
                          data.get("result", "?"),
                          duration_s=data.get("duration_s"),
                          cost_usd=data.get("cost_usd"))

    elif ev == "claude_tool_use" and verbose:
        print(f"  {DIM}tool: {data.get('tool', '?')}{RESET}" if _IS_TTY
              else f"  tool: {data.get('tool', '?')}", file=sys.stderr)

    elif ev == "results_dir" and verbose:
        print(f"  Results: {data.get('path', '?')}", file=sys.stderr)
