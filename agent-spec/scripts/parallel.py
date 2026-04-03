#!/usr/bin/env python3
"""parallel.py — Launch parallel invoke instances for a target.

Consumes invoke.py's stdout JSONL protocol to track results.
Human display goes to stderr via StatusLine.

Usage:
  python3 scripts/parallel.py <target> [config] [options]

Options:
  --instances N          Reps per variant (default: 1)
  --configs c1,c2        Comma-separated configs
  --models m1,m2         Comma-separated models (creates matrix)
  --stimuli-dir <path>   Per-instance files to inject (round-robin)
  --keep                 Preserve sandboxes
  --model <name>         Single model override
  --budget <usd>         Budget override
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (
    PROJECT_DIR, SCRIPTS_DIR, PORT_MIN, PORT_MAX, RUN_ROOT,
    die, require_dir, apc_log, now_ms,
    list_evals, list_configs, get_baseline_cost, find_results_dir,
    track_pid, stop_tracked_pids,
    StatusLine, _color, GREEN, RED, RESET, DIM, BOLD, _IS_TTY,
)
from system_monitor import check_preflight, get_disk_usage, get_memory_usage


def _drain_stdout(proc: subprocess.Popen) -> dict:
    """Read all JSONL from a child's stdout, return the run_finished event data.

    Returns {"run_id": str, "result": str, "cost_usd": float} or empty dict.
    """
    finished = {}
    if proc.stdout is None:
        return finished
    for raw_line in proc.stdout:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            ev = event.get("event", "")
            data = event.get("data", {})
            if ev == "run_finished":
                finished = {
                    "run_id": data.get("run_id"),
                    "result": data.get("result", "UNKNOWN"),
                    "cost_usd": data.get("cost_usd", 0.0),
                }
        except json.JSONDecodeError:
            pass
    return finished


def main(args=None):
    parser = argparse.ArgumentParser(description="Parallel eval runner")
    parser.add_argument("target", help="Target name")
    parser.add_argument("config", nargs="?", default="baseline")
    parser.add_argument("--instances", type=int, default=1)
    parser.add_argument("--configs", default="")
    parser.add_argument("--models", default="")
    parser.add_argument("--stimuli-dir", default="")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--model", default="")
    parser.add_argument("--budget", default="")
    parser.add_argument("--stream", action="store_true", help="Use stream-json for real-time Claude events")
    parser.add_argument("--verbose", action="store_true")
    args = args or parser.parse_args()

    target_dir = PROJECT_DIR / "evals" / args.target
    if not target_dir.is_dir():
        available = list_evals()
        die(f"Eval '{args.target}' not found. Available: {', '.join(available) if available else 'none'}")

    # Build variant matrix
    config_list = args.configs.split(",") if args.configs else [args.config]
    if args.models:
        model_list = args.models.split(",")
    elif args.model:
        model_list = [args.model]
    else:
        model_list = [""]

    variants = []
    for c in config_list:
        for m in model_list:
            for _ in range(args.instances):
                variants.append((c.strip(), m.strip()))

    total = len(variants)
    max_parallel = PORT_MAX - PORT_MIN + 1
    if total > max_parallel:
        die(f"Too many parallel instances ({total}). Max is {max_parallel}.")

    # Pre-flight resource check
    ok, snapshot = check_preflight()
    if not ok:
        die(f"System resources critical — {snapshot['status_summary']}. "
            f"Run 'python3 scripts/system_monitor.py' to see details.")

    # Memory warning for parallel runs
    mem = get_memory_usage()
    estimated_mb = total * 500
    available_mb = mem["free_gb"] * 1024
    if estimated_mb > available_mb * 0.8:
        print(f"  WARNING: {total} agents need ~{estimated_mb}MB, "
              f"only {available_mb:.0f}MB free. Risk of system overload.",
              file=sys.stderr)

    # Collect stimuli
    stimuli_files = []
    if args.stimuli_dir and Path(args.stimuli_dir).is_dir():
        stimuli_files = sorted(Path(args.stimuli_dir).glob("*"))

    # Launch
    pid = os.getpid()
    procs = []
    log_files = []
    labels = []

    # Generate parallel master run_id
    parallel_id = f"p-{uuid.uuid4().hex[:8]}"
    os.environ["AGENT_SPEC_RUN_ID"] = parallel_id
    start_ms = now_ms()

    apc_log("INFO", "parallel_started", f"Launching {total} instances of {args.target}", {
        "target": args.target, "total": total,
        "configs": config_list, "models": model_list, "instances": args.instances,
    })

    # ── Header ───────────────────────────────────────────────────
    print(f"── {args.target} ({total} runs) ──", file=sys.stderr)
    if args.verbose:
        print(f"  Parallel ID: {parallel_id}", file=sys.stderr)
    print(file=sys.stderr)

    # ── Launch all instances ─────────────────────────────────────
    baseline = get_baseline_cost(args.target, config_list[0])
    budget = float(args.budget) if args.budget else None
    statuses: list[StatusLine] = []

    for i, (v_config, v_model) in enumerate(variants, 1):
        instance_port = PORT_MIN + i - 1
        log_file = f"/tmp/agent-spec-parallel-out-{pid}-{i}.log"
        log_files.append(log_file)

        # Resolve config
        config_dir = target_dir / "configs" / v_config
        if not config_dir.is_dir():
            die(f"Config '{v_config}' not found in evals/{args.target}/configs/")

        # Stimuli injection
        inject_dir = None
        if stimuli_files:
            inject_dir = Path(f"/tmp/agent-spec-inject-{pid}-{i}")
            inject_dir.mkdir(parents=True, exist_ok=True)
            stim = stimuli_files[(i - 1) % len(stimuli_files)]
            shutil.copy2(stim, inject_dir / "wireframe.png")

        label = f"Run {i}: {v_config}"
        if v_model:
            label += f" / {Path(v_model).name}"
        labels.append(label)

        apc_log("DEBUG", "instance_launched", f"Instance {i}: {v_config}",
                {"instance": i, "config": v_config, "model": v_model, "port": instance_port})

        # Build args
        cmd = [
            sys.executable, str(SCRIPTS_DIR / "run_eval.py"),
            args.target, v_config,
            "--port", str(instance_port),
        ]
        if v_model:
            cmd += ["--model", v_model]
        if args.budget:
            cmd += ["--budget", args.budget]
        if args.keep:
            cmd.append("--keep")
        if inject_dir:
            cmd += ["--inject", str(inject_dir)]
        if args.stream:
            cmd.append("--stream")

        # stdout=PIPE for JSONL protocol, stderr to log file for human display
        lf = open(log_file, "w")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=lf)
        track_pid(proc.pid, instance_port, f"parallel-{i}")
        procs.append((proc, lf))

        # Create status line and print initial placeholder
        status = StatusLine(label=label, budget=budget, baseline_cost=baseline)
        statuses.append(status)
        status.update()
        if _IS_TTY:
            print(file=sys.stderr)

    # ── Poll loop ────────────────────────────────────────────────
    is_tty = _IS_TTY
    finished = [False] * total
    instance_results: list[dict] = [{}] * total
    resource_tick = 0

    while not all(finished):
        for i, ((proc, _lf), status) in enumerate(zip(procs, statuses)):
            if finished[i]:
                continue
            if proc.poll() is not None:
                # Instance done — drain stdout JSONL for run_finished event
                result_data = _drain_stdout(proc)
                instance_results[i] = result_data
                result = result_data.get("result", "UNKNOWN")
                cost = result_data.get("cost_usd", 0.0)
                status.finish(result, cost=cost)
                finished[i] = True
            elif is_tty:
                status.update()

        if is_tty and not all(finished):
            active_count = total
            sys.stderr.write(f"\033[{active_count}A")
            for s in statuses:
                if not s.finished:
                    s.update()
                    sys.stderr.write("\n")
                else:
                    sys.stderr.write("\n")
            sys.stderr.flush()

        # Periodic resource check
        resource_tick += 1
        if resource_tick >= 30:
            resource_tick = 0
            disk = get_disk_usage()
            mem = get_memory_usage()
            if disk["status"] == "CRITICAL" or mem["status"] == "CRITICAL":
                apc_log("WARN", "resource_warning",
                        f"CRITICAL: disk {disk['free_gb']}GB free, memory {mem['pct']:.0f}%",
                        {"disk_free_gb": disk["free_gb"], "mem_pct": mem["pct"]},
                        run_id=parallel_id)
                print(f"  WARNING: Resources critical — disk {disk['free_gb']}GB free, "
                      f"memory {mem['pct']:.0f}%", file=sys.stderr)

        time.sleep(2)

    # Close log file handles
    for _proc, lf in procs:
        lf.close()

    # ── Collect results and log ──────────────────────────────────
    failures = 0
    run_ids = []
    manifest = f"/tmp/agent-spec-parallel-{pid}-{int(time.time())}.txt"

    for i, (proc, _lf) in enumerate(procs):
        result_data = instance_results[i]
        run_id = result_data.get("run_id")
        result = result_data.get("result", "UNKNOWN")
        cost = result_data.get("cost_usd", 0.0)

        if run_id:
            run_ids.append(run_id)
            with open(manifest, "a") as mf:
                mf.write(run_id + "\n")

            # Archive instance log
            results_dir = find_results_dir(run_id)
            if results_dir:
                shutil.copy2(log_files[i], results_dir / "parallel-instance.log")

            if result != "PASS":
                failures += 1
                stderr_tail = ""
                try:
                    stderr_tail = Path(log_files[i]).read_text().splitlines()[-15:]
                    stderr_tail = "\n".join(stderr_tail)[:500]
                except (FileNotFoundError, IndexError):
                    pass
                apc_log("ERROR", "instance_failed", f"Instance {i+1} failed",
                        {"instance": i+1, "run_id": run_id, "result": result,
                         "exit_code": proc.returncode, "stderr_tail": stderr_tail},
                        run_id=parallel_id)
            else:
                apc_log("INFO", "instance_complete", f"Instance {i+1} passed",
                        {"instance": i+1, "run_id": run_id, "result": result,
                         "exit_code": proc.returncode},
                        run_id=parallel_id)
        else:
            failures += 1
            apc_log("ERROR", "instance_failed", f"Instance {i+1} crashed (no run_id)",
                    {"instance": i+1, "exit_code": proc.returncode},
                    run_id=parallel_id)
            if args.verbose:
                print(f"\n  Instance {i+1} failed (no run_id). Last 15 lines:", file=sys.stderr)
                try:
                    lines = Path(log_files[i]).read_text().splitlines()
                    for line in lines[-15:]:
                        print(f"    {line}", file=sys.stderr)
                except FileNotFoundError:
                    pass

    duration_ms = now_ms() - start_ms
    passed = total - failures

    apc_log("INFO", "parallel_complete", f"{passed}/{total} passed",
            {"total": total, "passed": passed, "failed": failures,
             "run_ids": run_ids, "duration_ms": duration_ms},
            run_id=parallel_id)

    # ── Summary ──────────────────────────────────────────────────
    print(file=sys.stderr)
    duration_s = duration_ms / 1000
    if passed == total:
        summary = _color(GREEN, f"{passed}/{total} passed")
    else:
        summary = _color(RED, f"{passed}/{total} passed")
    print(f"  {summary}  ({duration_s:.0f}s)", file=sys.stderr)

    # Clean up inject dirs
    for d in Path("/tmp").glob(f"agent-spec-inject-{pid}-*"):
        shutil.rmtree(d, ignore_errors=True)

    # Parseable output on stdout
    for rid in run_ids:
        print(rid)

    sys.exit(failures)


if __name__ == "__main__":
    main()
