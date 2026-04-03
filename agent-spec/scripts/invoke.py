#!/usr/bin/env python3
"""invoke.py — Run one agent in a sandbox and score the result.

Output protocol:
  stdout — JSONL events (one per line), parseable by parent processes
  stderr — Human-readable display (headers, spinners, results)

Usage: python3 scripts/invoke.py <source> <config> <prompt> [options]
"""

import argparse
import atexit
import json
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
    parse_output_json, now_ms, get_baseline_cost, StatusLine, render_event,
    track_pid, _stop_process_tree,
)
from system_monitor import check_preflight, get_disk_usage, get_memory_usage, get_cpu_usage

# ── Globals for cleanup ──────────────────────────────────────────

_sandbox: Path | None = None
_agent_proc: subprocess.Popen | None = None
_keep = False
_run_dir: Path | None = None
_results_dir: Path | None = None


def emit(level: str, event: str, msg: str, data: dict | None = None):
    """Write event to events.jsonl AND stdout JSONL stream."""
    apc_log(level, event, msg, data)
    print(json.dumps({"event": event, "data": data or {}}), flush=True)


def _extract_tool_detail(block: dict) -> str:
    """Extract the primary argument from a tool_use block for display."""
    inp = block.get("input", {})
    name = block.get("name", "")

    if "file_path" in inp:
        return Path(inp["file_path"]).name
    if "command" in inp:
        cmd = inp["command"].strip().split("\n")[0]
        return cmd[:60]
    if "pattern" in inp:
        return inp["pattern"][:40]
    if "query" in inp:
        return inp["query"][:40]
    if "prompt" in inp:
        return inp["prompt"][:40]
    if "description" in inp:
        return inp["description"][:40]
    if "url" in inp:
        return inp["url"][:60]
    return ""


def _process_stream_event(se: dict, status: StatusLine):
    """Translate a Claude stream-json event into our event protocol.

    With -p --verbose, stream-json emits complete messages per line:
      type=system, type=assistant (with content blocks), type=user (tool results),
      type=rate_limit_event, type=result
    """
    etype = se.get("type", "")

    if etype == "assistant":
        msg = se.get("message", {})
        blocks = msg.get("content", [])

        emit("DEBUG", "claude_turn_start", "Assistant turn", {
            "role": "assistant",
        })

        # Extract tool uses from content blocks
        for block in blocks:
            if block.get("type") == "tool_use":
                detail = _extract_tool_detail(block)
                tool_data = {
                    "tool": block.get("name", ""),
                    "tool_use_id": block.get("id", ""),
                    "detail": detail,
                }
                emit("INFO", "claude_tool_use", f"Tool: {block.get('name', '?')}", tool_data)
                render_event({"event": "claude_tool_use", "data": tool_data}, status=status, verbose=True)

        # Update token count from usage if present
        usage = msg.get("usage", {})
        if usage:
            status.update(tokens_out=usage.get("output_tokens", 0))


def _emit_resource_snapshot(status: StatusLine):
    """Collect and emit a resource snapshot with real CPU."""
    disk = get_disk_usage()
    mem = get_memory_usage()
    cpu = get_cpu_usage()
    snapshot_data = {
        "cpu": cpu["pct"],
        "mem": round(mem["pct"], 1),
        "disk_free_gb": disk["free_gb"],
    }
    emit("METRIC", "resource_snapshot", "System resources", snapshot_data)
    render_event({"event": "resource_snapshot", "data": snapshot_data}, status=status)
    if disk["status"] == "CRITICAL" or mem["status"] == "CRITICAL":
        emit("WARN", "resource_warning",
             f"CRITICAL: disk {disk['free_gb']}GB, mem {mem['pct']:.0f}%",
             snapshot_data)


def _archive_and_cleanup():
    """Archive logs then clean up. Runs on ANY exit."""
    # Stop agent and its entire process tree
    if _agent_proc and _agent_proc.poll() is None:
        _stop_process_tree(_agent_proc.pid, "agent")

    # Archive logs to results/
    if _run_dir and _results_dir:
        _results_dir.mkdir(parents=True, exist_ok=True)
        for artifact in ["events.jsonl", "output.json", "stderr.log", "stream.jsonl"]:
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
    emit("ERROR", "run_terminated", f"Run terminated by {sig_name}",
         {"signal": sig_name, "run_id": os.environ.get("AGENT_SPEC_RUN_ID", "unknown")})
    sys.exit(1)


def main():
    global _sandbox, _agent_proc, _keep, _run_dir, _results_dir

    parser = argparse.ArgumentParser(description="Run one agent in a workspace")
    parser.add_argument("source", nargs="?", default=None, help="Source repo path (optional if --seeds used)")
    parser.add_argument("config", help="Config directory path")
    parser.add_argument("prompt_file", help="Prompt file path")
    parser.add_argument("--budget", default=DEFAULT_BUDGET)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--verify", default="")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--delete", default="", help="Comma-separated files to delete")
    parser.add_argument("--setup", default="", help="Semicolon-separated setup commands")
    parser.add_argument("--inject", default="", help="Directory to inject into workspace")
    parser.add_argument("--seeds", default="", help="Directory of seed files to copy into workspace")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--verbose", action="store_true", help="Show workspace lifecycle details")
    parser.add_argument("--stream", action="store_true", help="Use stream-json for real-time Claude events")
    parser.add_argument("--challenge", default="", help="Challenge name (for logging)")
    parser.add_argument("--eval-name", default="", help="Eval name (results go to evals/<name>/results/)")
    args = parser.parse_args()

    _keep = args.keep
    verbose = args.verbose

    # ── Phase 1: VALIDATE ────────────────────────────────────────
    if not args.source and not args.seeds:
        die("Either source repo or --seeds must be provided")
    if args.source:
        require_dir(args.source, "Source repo not found")
    if args.seeds:
        require_dir(args.seeds, "Seeds directory not found")
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
    if args.eval_name:
        _results_dir = PROJECT_DIR / "evals" / args.eval_name / "results" / run_id
    else:
        _results_dir = PROJECT_DIR / "results" / run_id
    _run_dir.mkdir(parents=True, exist_ok=True)
    _results_dir.mkdir(parents=True, exist_ok=True)

    port = allocate_port(args.port)
    os.environ["PORT"] = str(port)

    target_name = args.challenge or (Path(args.source).name if args.source else Path(args.seeds).parent.name)
    config_name = Path(args.config).name

    # ── Emit run_started (stdout + stderr + events.jsonl) ────────
    run_started_data = {
        "run_id": run_id, "target": target_name, "config": config_name,
        "eval": args.eval_name, "model": args.model, "budget": float(args.budget), "port": port,
    }
    emit("INFO", "run_started", "Run started", run_started_data)
    render_event({"event": "run_started", "data": run_started_data}, verbose=verbose)

    # ── Phase 2: WORKSPACE ───────────────────────────────────────
    workspace_path = Path(f"{SANDBOX_ROOT}-{run_id}")
    if workspace_path.exists():
        die(f"Workspace already exists: {workspace_path}")

    if args.source:
        shutil.copytree(args.source, workspace_path, symlinks=False)
    else:
        workspace_path.mkdir(parents=True)

    if args.seeds:
        seeds_dir = Path(args.seeds)
        for item in seeds_dir.iterdir():
            dest = workspace_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    _sandbox = workspace_path

    # Register cleanup
    atexit.register(_archive_and_cleanup)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGHUP, _handle_signal)

    emit("DEBUG", "sandbox_created", "Sandbox ready",
         {"sandbox": str(workspace_path), "source": args.source})

    # ── Phase 3: PREPARE ─────────────────────────────────────────

    # 3a. Delete files
    if args.delete:
        for f in args.delete.split(","):
            target = workspace_path / f.strip()
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
        delete_data = {"files": args.delete}
        emit("DEBUG", "files_deleted", "Deleted files for agent to produce", delete_data)
        render_event({"event": "files_deleted", "data": delete_data}, verbose=verbose)

    # 3b. Inject files
    if args.inject:
        inject_dir = Path(args.inject)
        for item in inject_dir.iterdir():
            dest = workspace_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
        emit("DEBUG", "files_injected", "Injected files", {"from": args.inject})

    # 3c. Setup commands
    if args.setup:
        for cmd in args.setup.split(";"):
            cmd = cmd.strip()
            if not cmd:
                continue
            result = subprocess.run(cmd, shell=True, cwd=workspace_path,
                                    capture_output=True, text=True)
            if result.returncode != 0:
                emit("WARN", "setup_failed", f"Setup failed: {cmd}",
                     {"cmd": cmd, "exit_code": result.returncode, "stderr": result.stderr[:500]})
            else:
                setup_data = {"cmd": cmd, "exit_code": 0}
                emit("DEBUG", "setup_command", f"Setup: {cmd}", setup_data)
                render_event({"event": "setup_command", "data": setup_data}, verbose=verbose)
        emit("DEBUG", "setup_complete", "Setup finished", {})

    # 3d. Swap .claude/
    claude_dir = workspace_path / ".claude"
    if claude_dir.exists():
        shutil.rmtree(claude_dir)
    config_path = Path(args.config)
    if any(config_path.iterdir()) if config_path.exists() else False:
        shutil.copytree(config_path, claude_dir)
    else:
        claude_dir.mkdir()
        emit("WARN", "empty_config", "Agent has no instructions", {"config": config_name})
    emit("INFO", "config_swapped", "Config applied", {"config": config_name})

    # 3e. Inject emitters
    for emitter in ["_apc.py", "_apc.ts"]:
        src = SCRIPTS_DIR / emitter
        if src.exists():
            shutil.copy2(src, workspace_path / emitter)

    # 3f. Pre-flight resource check
    ok, snapshot = check_preflight()
    preflight_data = {"overall": snapshot["overall"], "cpu": snapshot["cpu_pct"],
                      "mem": snapshot["mem_pct"], "disk_free_gb": snapshot["disk_free_gb"]}
    emit("INFO", "preflight_check", f"Resources: {snapshot['status_summary']}", preflight_data)
    render_event({"event": "preflight_check", "data": preflight_data}, verbose=verbose)
    if not ok:
        die(f"System resources critical — {snapshot['status_summary']}. "
            f"Run 'python3 scripts/system_monitor.py' to see details.")

    # 3g. Exclude sandbox from Spotlight indexing
    Path(workspace_path / ".metadata_never_index").touch()

    # ── Phase 4: EXECUTE ─────────────────────────────────────────
    prompt_text = Path(args.prompt_file).read_text()
    prompt_text = prompt_text.replace("__PORT__", str(port))

    output_format = "stream-json" if args.stream else "json"
    emit("INFO", "agent_started", "Agent invoked", {
        "target": target_name, "config": config_name,
        "model": args.model, "budget": float(args.budget), "port": port,
        "stream": args.stream,
    })

    # Create status line for live rendering
    baseline = get_baseline_cost(target_name, config_name)
    status = StatusLine(
        label=f"{target_name}/{config_name}",
        budget=float(args.budget),
        baseline_cost=baseline,
    )

    timeout = int(os.environ.get("TIMEOUT", TIMEOUT_DEFAULT))
    start_ms = now_ms()

    stderr_path = _run_dir / "stderr.log"
    try:
        with open(_run_dir / "output.json", "w") as out_f, \
             open(stderr_path, "w") as err_f:

            claude_cmd = [
                "claude", "-p", prompt_text,
                "--output-format", output_format,
                "--dangerously-skip-permissions",
                "--max-budget-usd", args.budget,
                "--model", args.model,
            ]

            if args.stream:
                # Stream mode: read NDJSON from stdout in real-time
                # stream-json with -p requires --verbose
                claude_cmd.append("--verbose")
                _agent_proc = subprocess.Popen(
                    claude_cmd, cwd=workspace_path,
                    stdout=subprocess.PIPE, stderr=err_f,
                )
                track_pid(_agent_proc.pid, port, "agent")

                stream_log_path = _run_dir / "stream.jsonl"
                with open(stream_log_path, "w") as stream_f:
                    deadline = time.time() + timeout
                    for raw_line in _agent_proc.stdout:
                        if time.time() > deadline:
                            _stop_process_tree(_agent_proc.pid, "agent")
                            break
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line:
                            continue

                        # Archive every stream line
                        stream_f.write(line + "\n")

                        try:
                            se = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        etype = se.get("type", "")

                        # The final result blob — write to output.json for compat
                        if etype == "result":
                            out_f.write(json.dumps(se))

                        # Translate high-value stream events into our protocol
                        _process_stream_event(se, status)

                    _agent_proc.wait()

            else:
                # Default mode: write output.json at end
                _agent_proc = subprocess.Popen(
                    claude_cmd, cwd=workspace_path,
                    stdout=out_f, stderr=err_f,
                )
                track_pid(_agent_proc.pid, port, "agent")

                deadline = time.time() + timeout
                resource_tick = 0
                while _agent_proc.poll() is None:
                    if time.time() > deadline:
                        _stop_process_tree(_agent_proc.pid, "agent")
                        break
                    resource_tick += 1
                    if resource_tick >= 15:  # every 15 ticks × 2s = 30s
                        resource_tick = 0
                        _emit_resource_snapshot(status)
                    status.update()
                    time.sleep(2)

        exit_code = _agent_proc.returncode if _agent_proc.returncode is not None else 124

    except Exception as e:
        exit_code = 1
        emit("ERROR", "agent_error", f"Failed to start agent: {e}",
             {"exit_code": 1, "duration_ms": now_ms() - start_ms})

    duration_ms = now_ms() - start_ms

    # Post-run resource snapshot (bookend — especially useful for stream mode)
    _emit_resource_snapshot(status)

    timed_out = exit_code == 124 or (_agent_proc and _agent_proc.returncode is None)

    if timed_out:
        emit("ERROR", "agent_timeout", f"Agent timed out after {timeout}s",
             {"timeout": timeout})
        time.sleep(2)
    elif exit_code == 0:
        emit("INFO", "agent_complete", "Agent finished",
             {"exit_code": 0, "duration_ms": duration_ms})
    else:
        stderr_tail = ""
        stderr_file = _run_dir / "stderr.log"
        if stderr_file.exists():
            lines = stderr_file.read_text().splitlines()
            stderr_tail = " ".join(lines[-5:])[:200]
        emit("ERROR", "agent_error", f"Agent failed (exit {exit_code})",
             {"exit_code": exit_code, "duration_ms": duration_ms, "stderr": stderr_tail})

    # ── Phase 5: METRICS ─────────────────────────────────────────
    output_file = _run_dir / "output.json"
    final_cost = 0.0
    if output_file.exists() and output_file.stat().st_size > 0:
        tokens = parse_output_json(output_file)
        if tokens:
            if timed_out:
                tokens["note"] = "timeout"
            emit("METRIC", "token_update", "Token usage", tokens)
            render_event({"event": "token_update", "data": tokens}, status=status)
            final_cost = tokens.get("cost_usd", final_cost)
    elif timed_out:
        emit("METRIC", "token_update", "Token usage (unavailable after timeout)",
             {"input": 0, "output": 0, "cost_usd": 0, "note": "timeout_no_output"})

    # ── Phase 6: VERIFY ──────────────────────────────────────────
    result_str = "N/A"
    if args.verify:
        shutil.copy2(args.verify, workspace_path / "verify.sh")

        vresult = subprocess.run(
            ["bash", "verify.sh"],
            cwd=workspace_path,
            capture_output=True, text=True,
            env={**os.environ, "PORT": str(port), "AGENT_SPEC_RUN_ID": run_id},
        )
        output = vresult.stdout + vresult.stderr

        verify_data = {"output": output[:5000], "exit_code": vresult.returncode}
        emit("INFO", "verification_output", "Verify script output", verify_data)
        render_event({"event": "verification_output", "data": verify_data}, verbose=verbose)

        # Parse individual test results
        for line in output.splitlines():
            if "PASS:" in line and "RESULT:" not in line:
                test_name = line.split("PASS:")[-1].strip()
                test_data = {"test_name": test_name}
                emit("INFO", "test_passed", "Test passed", test_data)
                render_event({"event": "test_passed", "data": test_data}, verbose=verbose)
            elif "FAIL:" in line and "RESULT:" not in line:
                test_name = line.split("FAIL:")[-1].strip()
                test_data = {"test_name": test_name}
                emit("ERROR", "test_failed", "Test failed", test_data)
                render_event({"event": "test_failed", "data": test_data}, verbose=verbose)

        # Parse final result
        if "RESULT: PASS" in output:
            result_str = "PASS"
            emit("INFO", "score", "PASS", {"result": "PASS"})
        elif "RESULT: FAIL" in output:
            result_str = "FAIL"
            emit("ERROR", "score", "FAIL", {"result": "FAIL"})
        else:
            emit("WARN", "score", "No RESULT line", {"result": "N/A"})

    # ── Final: run_finished (the terminal event) ─────────────────
    finished_data = {
        "run_id": run_id, "target": target_name, "config": config_name,
        "result": result_str, "cost_usd": final_cost,
        "duration_s": duration_ms / 1000,
    }
    emit("INFO", "run_finished", "Run complete", finished_data)
    render_event({"event": "run_finished", "data": finished_data}, status=status)

    render_event({"event": "results_dir", "data": {"path": str(_results_dir)}}, verbose=verbose)


if __name__ == "__main__":
    main()
