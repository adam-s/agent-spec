#!/usr/bin/env python3
"""parallel.py — Launch parallel invoke instances for a target.

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
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (
    PROJECT_DIR, SCRIPTS_DIR, PORT_MIN, PORT_MAX,
    die, require_dir, apc_log, now_ms,
    list_targets, list_configs, get_baseline_cost,
    StatusLine, _color, GREEN, RED, RESET, DIM, BOLD, _IS_TTY,
)


def _parse_log_for_result(log_file: str) -> tuple[str | None, str, float]:
    """Parse an instance log for run_id, result, and cost."""
    run_id = None
    result = "UNKNOWN"
    cost = 0.0
    try:
        log_text = Path(log_file).read_text()
        m = re.search(r'Run:\s+([a-f0-9]{8})', log_text)
        if not m:
            m = re.search(r'agent-spec run: ([a-f0-9]{8})', log_text)
        if m:
            run_id = m.group(1)
        rm = re.findall(r'RESULT: [A-Z/]+', log_text)
        if rm:
            result = rm[-1].replace("RESULT: ", "")
        cm = re.findall(r'\$(\d+\.\d+)', log_text)
        if cm:
            cost = float(cm[-1])
    except FileNotFoundError:
        pass
    return run_id, result, cost


def _render_multi_status(statuses: list[StatusLine], labels: list[str]):
    """Render all status lines by moving cursor up and rewriting."""
    n = len(statuses)
    # Move up n lines, rewrite each, end at bottom
    sys.stderr.write(f"\033[{n}A")
    for s in statuses:
        s.update()
    sys.stderr.flush()


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
    parser.add_argument("--verbose", action="store_true")
    args = args or parser.parse_args()

    target_dir = PROJECT_DIR / "targets" / args.target
    if not target_dir.is_dir():
        available = list_targets()
        die(f"Target '{args.target}' not found. Available: {', '.join(available) if available else 'none'}")

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
            config_dir = PROJECT_DIR / "targets" / "_shared" / "configs" / v_config
            require_dir(config_dir, f"Config '{v_config}' not found in target or _shared")

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

        with open(log_file, "w") as lf:
            proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT)
            procs.append(proc)

        # Create status line and print initial placeholder
        status = StatusLine(label=label, budget=budget, baseline_cost=baseline)
        statuses.append(status)
        status.update()
        if _IS_TTY:
            print(file=sys.stderr)  # newline for each status line slot

    # ── Poll loop ────────────────────────────────────────────────
    is_tty = _IS_TTY
    finished = [False] * total

    while not all(finished):
        for i, (proc, status) in enumerate(zip(procs, statuses)):
            if finished[i]:
                continue
            if proc.poll() is not None:
                # Instance done — parse result
                run_id, result, cost = _parse_log_for_result(log_files[i])
                status.finish(result, cost=cost)
                finished[i] = True
            elif is_tty:
                # Tick the spinner for running instances
                status.update()

        if is_tty and not all(finished):
            # Move cursor up to rewrite all lines
            active_count = total
            sys.stderr.write(f"\033[{active_count}A")
            for s in statuses:
                if not s.finished:
                    s.update()
                    sys.stderr.write("\n")
                else:
                    # Re-render finished line (already has newline from finish())
                    sys.stderr.write("\n")
            sys.stderr.flush()

        time.sleep(2)

    # ── Collect results and log ──────────────────────────────────
    failures = 0
    run_ids = []
    manifest = f"/tmp/agent-spec-parallel-{pid}-{int(time.time())}.txt"

    for i, proc in enumerate(procs):
        log_file = log_files[i]
        run_id, result, cost = _parse_log_for_result(log_file)

        if run_id:
            run_ids.append(run_id)
            with open(manifest, "a") as mf:
                mf.write(run_id + "\n")

            # Archive instance log
            results_dir = PROJECT_DIR / "results" / run_id
            if results_dir.is_dir():
                shutil.copy2(log_file, results_dir / "parallel-instance.log")

            if result != "PASS":
                failures += 1
                stderr_tail = ""
                try:
                    stderr_tail = Path(log_file).read_text().splitlines()[-15:]
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
                    lines = Path(log_file).read_text().splitlines()
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
