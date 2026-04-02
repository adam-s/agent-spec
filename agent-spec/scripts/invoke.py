#!/usr/bin/env python3
"""invoke.py — Run one agent in a sandbox and score the result.

Usage: python3 scripts/invoke.py <source> <config> <prompt> [options]
"""

import argparse
import atexit
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (
    PROJECT_DIR, RUN_ROOT, SANDBOX_ROOT, DEFAULT_MODEL, DEFAULT_BUDGET, TIMEOUT_DEFAULT,
    SCRIPTS_DIR, apc_log, allocate_port, die, require_file, require_dir,
    parse_output_json, now_ms, get_baseline_cost, StatusLine,
    track_pid, _stop_process_tree,
    DIM, RESET, _IS_TTY,
)
from system_monitor import check_preflight, get_disk_usage, get_memory_usage

# ── Globals for cleanup ──────────────────────────────────────────

_sandbox: Path | None = None
_agent_proc: subprocess.Popen | None = None
_keep = False
_run_dir: Path | None = None
_results_dir: Path | None = None


def _archive_and_cleanup():
    """Archive logs then clean up. Runs on ANY exit."""
    # Stop agent and its entire process tree
    if _agent_proc and _agent_proc.poll() is None:
        _stop_process_tree(_agent_proc.pid, "agent")

    # Archive logs to results/
    if _run_dir and _results_dir:
        _results_dir.mkdir(parents=True, exist_ok=True)
        for artifact in ["events.jsonl", "output.json", "stderr.log"]:
            src = _run_dir / artifact
            if src.exists():
                shutil.copy2(src, _results_dir / artifact)

        # Archive config snapshot for diff comparison
        if _sandbox and _sandbox.exists():
            claude_dir = _sandbox / ".claude"
            if claude_dir.exists():
                shutil.copytree(claude_dir, _results_dir / "config-snapshot", dirs_exist_ok=True)

        # Archive produced files from sandbox
        if _sandbox and _sandbox.exists():
            for ext in ("*.py", "*.js", "*.ts"):
                for f in _sandbox.rglob(ext):
                    if "node_modules" in f.parts or f.name.startswith("_apc"):
                        continue
                    rel = f.relative_to(_sandbox)
                    dest = _results_dir / "produced" / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)

    # Remove sandbox
    if not _keep and _sandbox and _sandbox.exists():
        shutil.rmtree(_sandbox, ignore_errors=True)


def _handle_signal(signum, frame):
    sig_name = signal.Signals(signum).name
    apc_log("ERROR", "run_terminated", f"Run terminated by {sig_name}",
            {"signal": sig_name, "run_id": os.environ.get("AGENT_SPEC_RUN_ID", "unknown")})
    sys.exit(1)


def main():
    global _sandbox, _agent_proc, _keep, _run_dir, _results_dir

    parser = argparse.ArgumentParser(description="Run one agent in a sandbox")
    parser.add_argument("source", help="Source repo path")
    parser.add_argument("config", help="Config directory path")
    parser.add_argument("prompt_file", help="Prompt file path")
    parser.add_argument("--budget", default=DEFAULT_BUDGET)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--verify", default="")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--delete", default="", help="Comma-separated files to delete")
    parser.add_argument("--setup", default="", help="Semicolon-separated setup commands")
    parser.add_argument("--inject", default="", help="Directory to inject into sandbox")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--verbose", action="store_true", help="Show sandbox lifecycle details")
    args = parser.parse_args()

    _keep = args.keep
    verbose = args.verbose

    # ── Phase 1: VALIDATE ────────────────────────────────────────
    require_dir(args.source, "Source repo not found")
    require_dir(args.config, "Config directory not found")
    require_file(args.prompt_file, "Prompt file not found")
    if args.verify:
        require_file(args.verify, "Verify script not found")
    if args.inject:
        require_dir(args.inject, "Inject directory not found")

    # ── Generate run ID and allocate port ────────────────────────
    run_id = uuid.uuid4().hex[:8]
    os.environ["AGENT_SPEC_RUN_ID"] = run_id
    _run_dir = RUN_ROOT / run_id
    _results_dir = PROJECT_DIR / "results" / run_id
    _run_dir.mkdir(parents=True, exist_ok=True)
    _results_dir.mkdir(parents=True, exist_ok=True)

    port = allocate_port(args.port)
    os.environ["PORT"] = str(port)

    target_name = Path(args.source).name
    config_name = Path(args.config).name

    # ── Header ───────────────────────────────────────────────────
    print(f"── {target_name}/{config_name} ({args.model}) ──")
    print(f"  Run:    {run_id}")
    print(f"  Budget: ${args.budget}")
    if verbose:
        print(f"  Port:   {port}")
        print(f"  Log:    {_run_dir}/events.jsonl")
    print()

    # ── Phase 2: SANDBOX ─────────────────────────────────────────
    sandbox_path = Path(f"{SANDBOX_ROOT}-{run_id}")
    if sandbox_path.exists():
        die(f"Sandbox already exists: {sandbox_path}")

    shutil.copytree(args.source, sandbox_path, symlinks=False)
    _sandbox = sandbox_path

    # Register cleanup
    atexit.register(_archive_and_cleanup)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGHUP, _handle_signal)

    apc_log("INFO", "sandbox_created", "Sandbox ready",
            {"sandbox": str(sandbox_path), "source": args.source})

    # ── Phase 3: PREPARE ─────────────────────────────────────────

    # 3a. Delete files
    if args.delete:
        for f in args.delete.split(","):
            target = sandbox_path / f.strip()
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                if verbose:
                    print(f"  Deleted: {f.strip()}")
        apc_log("DEBUG", "files_deleted", "Deleted files for agent to produce",
                {"files": args.delete})

    # 3b. Inject files
    if args.inject:
        inject_dir = Path(args.inject)
        for item in inject_dir.iterdir():
            dest = sandbox_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
        apc_log("DEBUG", "files_injected", "Injected files", {"from": args.inject})

    # 3c. Setup commands
    if args.setup:
        for cmd in args.setup.split(";"):
            cmd = cmd.strip()
            if not cmd:
                continue
            if verbose:
                print(f"  Setup: {cmd}")
            result = subprocess.run(cmd, shell=True, cwd=sandbox_path,
                                    capture_output=True, text=True)
            if result.returncode != 0:
                apc_log("WARN", "setup_failed", f"Setup failed: {cmd}",
                        {"cmd": cmd, "exit_code": result.returncode, "stderr": result.stderr[:500]})
            else:
                apc_log("DEBUG", "setup_command", f"Setup: {cmd}",
                        {"cmd": cmd, "exit_code": 0})
        apc_log("DEBUG", "setup_complete", "Setup finished")

    # 3d. Swap .claude/
    claude_dir = sandbox_path / ".claude"
    if claude_dir.exists():
        shutil.rmtree(claude_dir)
    config_path = Path(args.config)
    if any(config_path.iterdir()) if config_path.exists() else False:
        shutil.copytree(config_path, claude_dir)
    else:
        claude_dir.mkdir()
        apc_log("WARN", "empty_config", "Agent has no instructions",
                {"config": config_name})
    apc_log("INFO", "config_swapped", "Config applied", {"config": config_name})

    # 3e. Inject emitters
    for emitter in ["_apc.py", "_apc.ts"]:
        src = SCRIPTS_DIR / emitter
        if src.exists():
            shutil.copy2(src, sandbox_path / emitter)

    # 3f. Pre-flight resource check
    ok, snapshot = check_preflight()
    apc_log("INFO", "preflight_check", f"Resources: {snapshot['status_summary']}",
            {"overall": snapshot["overall"], "cpu": snapshot["cpu_pct"],
             "mem": snapshot["mem_pct"], "disk_free_gb": snapshot["disk_free_gb"]})
    if not ok:
        die(f"System resources critical — {snapshot['status_summary']}. "
            f"Run 'python3 scripts/system_monitor.py' to see details.")

    # 3g. Exclude sandbox from Spotlight indexing
    Path(sandbox_path / ".metadata_never_index").touch()

    # ── Phase 4: EXECUTE ─────────────────────────────────────────
    prompt_text = Path(args.prompt_file).read_text()
    prompt_text = prompt_text.replace("__PORT__", str(port))

    apc_log("INFO", "agent_started", "Agent invoked", {
        "target": target_name, "config": config_name,
        "model": args.model, "budget": float(args.budget), "port": port,
    })

    timeout = int(os.environ.get("TIMEOUT", TIMEOUT_DEFAULT))
    start_ms = now_ms()

    stderr_path = _run_dir / "stderr.log"
    try:
        with open(_run_dir / "output.json", "w") as out_f, \
             open(stderr_path, "w") as err_f:
            _agent_proc = subprocess.Popen(
                ["claude", "-p", prompt_text,
                 "--output-format", "json",
                 "--dangerously-skip-permissions",
                 "--max-budget-usd", args.budget,
                 "--model", args.model],
                cwd=sandbox_path,
                stdout=out_f,
                stderr=err_f,
            )
            track_pid(_agent_proc.pid, port, "agent")

            deadline = time.time() + timeout
            resource_tick = 0
            while _agent_proc.poll() is None:
                if time.time() > deadline:
                    _stop_process_tree(_agent_proc.pid, "agent")
                    break
                resource_tick += 1
                if resource_tick >= 30:  # every 30 ticks × 2s = 60s
                    resource_tick = 0
                    disk = get_disk_usage()
                    mem = get_memory_usage()
                    if disk["status"] == "CRITICAL" or mem["status"] == "CRITICAL":
                        apc_log("WARN", "resource_warning",
                                f"CRITICAL during run: disk {disk['free_gb']}GB, mem {mem['pct']:.0f}%",
                                {"disk_free_gb": disk["free_gb"], "mem_pct": mem["pct"]})
                time.sleep(2)

        exit_code = _agent_proc.returncode if _agent_proc.returncode is not None else 124

    except Exception as e:
        exit_code = 1
        apc_log("ERROR", "agent_error", f"Failed to start agent: {e}",
                {"exit_code": 1, "duration_ms": now_ms() - start_ms})

    duration_ms = now_ms() - start_ms

    if exit_code == 124 or (_agent_proc and _agent_proc.returncode is None):
        apc_log("ERROR", "agent_timeout", f"Agent timed out after {timeout}s",
                {"timeout": timeout})
    elif exit_code == 0:
        apc_log("INFO", "agent_complete", "Agent finished",
                {"exit_code": 0, "duration_ms": duration_ms})
    else:
        stderr_tail = ""
        stderr_file = _run_dir / "stderr.log"
        if stderr_file.exists():
            lines = stderr_file.read_text().splitlines()
            stderr_tail = " ".join(lines[-5:])[:200]
        apc_log("ERROR", "agent_error", f"Agent failed (exit {exit_code})",
                {"exit_code": exit_code, "duration_ms": duration_ms, "stderr": stderr_tail})

    # ── Phase 5: METRICS ─────────────────────────────────────────
    output_file = _run_dir / "output.json"
    final_cost = 0.0
    if output_file.exists() and output_file.stat().st_size > 0:
        tokens = parse_output_json(output_file)
        if tokens:
            apc_log("METRIC", "token_update", "Token usage", tokens)
            final_cost = tokens.get("cost_usd", final_cost)

    # ── Phase 6: VERIFY ──────────────────────────────────────────
    result_str = "N/A"
    if args.verify:
        shutil.copy2(args.verify, sandbox_path / "verify.sh")

        vresult = subprocess.run(
            ["bash", "verify.sh"],
            cwd=sandbox_path,
            capture_output=True, text=True,
            env={**os.environ, "PORT": str(port), "AGENT_SPEC_RUN_ID": run_id},
        )
        output = vresult.stdout + vresult.stderr

        apc_log("INFO", "verification_output", "Verify script output",
                {"output": output[:5000], "exit_code": vresult.returncode})

        # Parse individual test results
        for line in output.splitlines():
            if "PASS:" in line and "RESULT:" not in line:
                test_name = line.split("PASS:")[-1].strip()
                apc_log("INFO", "test_passed", "Test passed", {"test_name": test_name})
            elif "FAIL:" in line and "RESULT:" not in line:
                test_name = line.split("FAIL:")[-1].strip()
                apc_log("ERROR", "test_failed", "Test failed", {"test_name": test_name})

        # Parse final result
        if "RESULT: PASS" in output:
            result_str = "PASS"
            apc_log("INFO", "score", "PASS", {"result": "PASS"})
        elif "RESULT: FAIL" in output:
            result_str = "FAIL"
            apc_log("ERROR", "score", "FAIL", {"result": "FAIL"})
        else:
            apc_log("WARN", "score", "No RESULT line", {"result": "N/A"})

        # Show verification output in verbose mode
        if verbose and output.strip():
            print()
            print(f"  {DIM}── verify ──{RESET}" if _IS_TTY else "  -- verify --")
            for line in output.strip().splitlines():
                print(f"  {DIM}{line}{RESET}" if _IS_TTY else f"  {line}")

    # ── Final status line ────────────────────────────────────────
    baseline = get_baseline_cost(target_name, config_name)
    status = StatusLine(
        label=f"{target_name}/{config_name}",
        budget=float(args.budget),
        baseline_cost=baseline,
    )
    status.finish(result_str, cost=final_cost, duration_s=duration_ms / 1000)

    if verbose:
        print(f"  Results: {_results_dir}/")


if __name__ == "__main__":
    main()
