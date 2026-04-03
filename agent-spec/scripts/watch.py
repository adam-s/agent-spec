#!/usr/bin/env python3
"""watch.py — Live renderer for agent-spec runs.

Reads JSONL events from stdin or events.jsonl and renders
a hierarchical, colored, real-time display inspired by vitest/pytest.

Usage:
  python3 scripts/run_eval.py ... --stream 2>/dev/null | python3 scripts/watch.py
  python3 scripts/watch.py --run <run_id>
  python3 scripts/watch.py --latest
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (
    RUN_ROOT, load_events,
    RESET, BOLD, DIM, RED, GREEN, YELLOW, CYAN, _IS_TTY, _color,
)

# ── Display State ──────────────────────────────────────────────


class RunDisplay:
    """Tracks run state and renders events as vitest-style output."""

    def __init__(self):
        self.run_id = ""
        self.target = ""
        self.config = ""
        self.model = ""
        self.budget = 0.0
        self.turn_num = 0
        self.turn_start = 0.0
        self.turns: list[dict] = []
        self.tests: list[dict] = []
        self.result = ""
        self.cost = 0.0
        self.duration_s = 0.0
        self.tokens_in = 0
        self.tokens_out = 0
        self.stop_reason = ""
        self.started = False

    def handle(self, event: dict):
        """Process one JSONL event and render it."""
        ev = event.get("event", "")
        data = event.get("data", {})

        if ev == "run_started":
            self.run_id = data.get("run_id", "?")
            self.target = data.get("target", "?")
            self.config = data.get("config", "?")
            self.model = _short_model(data.get("model", "?"))
            self.budget = data.get("budget", 0)
            self.started = True
            self._print_header()

        elif ev == "claude_turn_start":
            # Close previous turn timing
            if self.turn_num > 0 and not self.turns:
                # First tool-less turn (text only)
                dur = time.time() - self.turn_start if self.turn_start else 0
                self._print_turn(self.turn_num, "text", "", dur)
            self.turn_num += 1
            self.turn_start = time.time()

        elif ev == "claude_tool_use":
            tool = data.get("tool", "?")
            detail = data.get("detail", "")
            dur = time.time() - self.turn_start if self.turn_start else 0
            self._print_turn(self.turn_num, tool, detail, dur)
            self.turns.append({"tool": tool, "detail": detail, "duration_s": dur})
            self.turn_start = time.time()

        elif ev == "agent_complete":
            # Close final turn if it was text-only
            if self.turn_start and (not self.turns or self.turns[-1].get("_turn") != self.turn_num):
                dur = time.time() - self.turn_start
                if dur > 0.5:  # skip trivial gaps
                    self._print_turn(self.turn_num, "text", "", dur)

        elif ev == "token_update":
            self.cost = data.get("cost_usd", 0)
            self.tokens_in = data.get("input", 0)
            self.tokens_out = data.get("output", 0)
            self.stop_reason = data.get("stop_reason", "")

        elif ev == "test_passed":
            name = data.get("test_name", "")
            self.tests.append({"name": name, "passed": True})

        elif ev == "test_failed":
            name = data.get("test_name", "")
            self.tests.append({"name": name, "passed": False})

        elif ev.startswith("debug:"):
            tag = ev.replace("debug:", "")
            msg = event.get("msg", "")
            _out(f"           {DIM}{tag}: {msg}{RESET}" if _IS_TTY
                 else f"           {tag}: {msg}")

        elif ev == "score":
            self.result = data.get("result", "?")

        elif ev == "run_finished":
            self.result = self.result or data.get("result", "?")
            self.cost = self.cost or data.get("cost_usd", 0)
            self.duration_s = data.get("duration_s", 0)
            self._print_verify()
            self._print_summary()

    def _print_header(self):
        label = f"{self.target} / {self.config}"
        _out(f"\n{BOLD}── {label} ({self.model}) ──{RESET}  run: {DIM}{self.run_id}{RESET}")
        # System baseline
        try:
            from system_monitor import get_snapshot
            snap = get_snapshot()
            disk = snap["disk"]
            mem = snap["memory"]
            cpu = snap["cpu"]
            gpu = snap.get("gpu", {})
            parts = [
                f"CPU {cpu['pct']:.0f}%",
                f"Mem {mem['used_gb']:.0f}/{mem['total_gb']:.0f}GB",
                f"Disk {disk['free_gb']:.0f}GB free",
            ]
            _out(f"  {DIM}{' | '.join(parts)}{RESET}" if _IS_TTY
                 else f"  {' | '.join(parts)}")
        except Exception:
            pass
        _out("")

    def _print_turn(self, num: int, tool: str, detail: str, dur: float):
        num_str = f"{DIM}Turn {num:>2}{RESET}" if _IS_TTY else f"Turn {num:>2}"
        tool_str = f"{tool:<8}"
        if detail:
            detail_str = f" {DIM}({detail}){RESET}" if _IS_TTY else f" ({detail})"
        else:
            detail_str = ""
        dur_str = f"{DIM}{dur:.0f}s{RESET}" if _IS_TTY else f"{dur:.0f}s"
        _out(f"  {num_str}  {tool_str}{detail_str}  {dur_str}")

    def _print_verify(self):
        if not self.tests:
            return
        _out(f"\n  {BOLD}Verify{RESET}" if _IS_TTY else "\n  Verify")
        for t in self.tests:
            if t["passed"]:
                icon = _color(GREEN, "\u2713") if _IS_TTY else "+"
                _out(f"    {icon} {t['name']}")
            else:
                icon = _color(RED, "\u2717") if _IS_TTY else "x"
                _out(f"    {icon} {_color(RED, t['name'])}" if _IS_TTY else f"    {icon} {t['name']}")

    def _print_summary(self):
        if self.result == "PASS":
            icon = _color(GREEN, "\u2713")
            result_str = _color(GREEN, "PASS")
        elif self.result == "FAIL":
            icon = _color(RED, "\u2717")
            result_str = _color(RED, "FAIL")
        else:
            icon = "?"
            result_str = self.result

        parts = [f"{icon} {result_str}"]
        if self.duration_s:
            parts.append(f"{self.duration_s:.0f}s")
        if self.cost:
            parts.append(f"${self.cost:.2f}")
        if self.turns:
            parts.append(f"{len(self.turns)} tools")
        if self.turn_num:
            parts.append(f"{self.turn_num} turns")
        total_tokens = self.tokens_in + self.tokens_out
        if total_tokens:
            parts.append(f"{total_tokens} tokens")

        _out(f"\n  {'  '.join(parts)}\n")


def _short_model(m: str) -> str:
    """Shorten model name for display."""
    for prefix in ("claude-", "anthropic-"):
        m = m.replace(prefix, "")
    if len(m) > 15 and m[-8:].isdigit():
        m = m[:-9]
    return m


def _out(line: str):
    """Print a line, handling TTY color stripping."""
    if _IS_TTY:
        print(line, file=sys.stderr)
    else:
        # Strip ANSI codes for non-TTY
        import re
        clean = re.sub(r'\033\[[0-9;]*m', '', line)
        print(clean, file=sys.stderr)


# ── Input Sources ──────────────────────────────────────────────


def read_stdin(display: RunDisplay):
    """Read JSONL events from stdin (piped from invoke.py stdout)."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            display.handle(event)
        except json.JSONDecodeError:
            pass


def read_events_file(path: Path, display: RunDisplay):
    """Read events from an events.jsonl file (existing or live-tailing)."""
    if not path.exists():
        print(f"No events found: {path}", file=sys.stderr)
        sys.exit(1)

    # Print existing events
    for event in load_events(path):
        display.handle(event)

    # If run not finished, tail for new events
    if not display.result:
        try:
            with open(path) as f:
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        try:
                            display.handle(json.loads(line))
                        except json.JSONDecodeError:
                            pass
                        if display.result:
                            break
                    else:
                        time.sleep(0.3)
        except KeyboardInterrupt:
            pass


# ── CLI ────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="watch",
        description="Live renderer for agent-spec runs",
    )
    parser.add_argument("--run", metavar="RUN_ID", help="Watch a specific run's events.jsonl")
    parser.add_argument("--latest", action="store_true", help="Watch the most recent run")
    args = parser.parse_args()

    display = RunDisplay()

    if args.run:
        path = RUN_ROOT / args.run / "events.jsonl"
        read_events_file(path, display)
    elif args.latest:
        if not RUN_ROOT.exists():
            print("No runs found", file=sys.stderr)
            sys.exit(1)
        dirs = sorted(RUN_ROOT.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True)
        if not dirs:
            print("No runs found", file=sys.stderr)
            sys.exit(1)
        path = dirs[0] / "events.jsonl"
        read_events_file(path, display)
    else:
        # Read from stdin (piped from invoke.py)
        read_stdin(display)


if __name__ == "__main__":
    main()
