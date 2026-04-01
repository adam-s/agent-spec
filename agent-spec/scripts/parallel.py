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
from lib import PROJECT_DIR, SCRIPTS_DIR, PORT_MIN, PORT_MAX, die, require_dir, apc_log, now_ms


def main():
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
    args = parser.parse_args()

    target_dir = PROJECT_DIR / "targets" / args.target
    require_dir(target_dir, "Target not found")

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

    # Generate parallel master run_id
    parallel_id = f"p-{uuid.uuid4().hex[:8]}"
    os.environ["AGENT_SPEC_RUN_ID"] = parallel_id
    start_ms = now_ms()

    apc_log("INFO", "parallel_started", f"Launching {total} instances of {args.target}", {
        "target": args.target, "total": total,
        "configs": config_list, "models": model_list, "instances": args.instances,
    })

    print(f"Launching {total} parallel instance(s) of {args.target}", file=sys.stderr)
    print(f"  Parallel ID: {parallel_id}", file=sys.stderr)
    print(f"  Logs: /tmp/agent-spec-parallel-out-{pid}-{{1..{total}}}.log", file=sys.stderr)
    print(f"  Watch: tail -f /tmp/agent-spec-parallel-out-{pid}-*.log", file=sys.stderr)
    print(f"  Master: python3 scripts/dashboard.py {parallel_id} --summary", file=sys.stderr)
    print(file=sys.stderr)

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

        desc = v_config
        if v_model:
            desc += f" / {Path(v_model).name}"
        print(f"  Instance {i}: {desc} (port {instance_port})", file=sys.stderr)
        apc_log("DEBUG", "instance_launched", f"Instance {i}: {desc}",
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

    print(file=sys.stderr)
    print("Waiting for all instances...", file=sys.stderr)

    # Collect results
    failures = 0
    run_ids = []
    manifest = f"/tmp/agent-spec-parallel-{pid}-{int(time.time())}.txt"

    for i, proc in enumerate(procs, 1):
        proc.wait()
        exit_code = proc.returncode
        log_file = log_files[i - 1]

        # Extract run_id from log
        run_id = None
        result_line = "RESULT: UNKNOWN"
        try:
            log_text = Path(log_file).read_text()
            m = re.search(r'agent-spec run: ([a-f0-9]{8})', log_text)
            if m:
                run_id = m.group(1)
            rm = re.findall(r'RESULT: [A-Z/]+', log_text)
            if rm:
                result_line = rm[-1]
        except FileNotFoundError:
            pass

        if run_id:
            run_ids.append(run_id)
            with open(manifest, "a") as mf:
                mf.write(run_id + "\n")
            print(f"  Instance {i}: run={run_id} exit={exit_code} {result_line}", file=sys.stderr)

            # Archive instance log
            results_dir = PROJECT_DIR / "results" / run_id
            if results_dir.is_dir():
                shutil.copy2(log_file, results_dir / "parallel-instance.log")

            # Normalize result to just PASS/FAIL (strip "RESULT: " prefix)
            result_short = result_line.replace("RESULT: ", "")

            if "PASS" not in result_line:
                failures += 1
                stderr_tail = ""
                try:
                    stderr_tail = Path(log_file).read_text().splitlines()[-15:]
                    stderr_tail = "\n".join(stderr_tail)[:500]
                except (FileNotFoundError, IndexError):
                    pass
                apc_log("ERROR", "instance_failed", f"Instance {i} failed",
                        {"instance": i, "run_id": run_id, "result": result_short,
                         "exit_code": exit_code, "stderr_tail": stderr_tail},
                        run_id=parallel_id)
            else:
                apc_log("INFO", "instance_complete", f"Instance {i} passed",
                        {"instance": i, "run_id": run_id, "result": result_short,
                         "exit_code": exit_code},
                        run_id=parallel_id)
        else:
            print(f"  Instance {i}: exit={exit_code} (no run_id)", file=sys.stderr)
            apc_log("ERROR", "instance_failed", f"Instance {i} crashed (no run_id)",
                    {"instance": i, "exit_code": exit_code},
                    run_id=parallel_id)
            print(f"  --- Failure log (last 15 lines) ---", file=sys.stderr)
            try:
                lines = Path(log_file).read_text().splitlines()
                for line in lines[-15:]:
                    print(f"    {line}", file=sys.stderr)
            except FileNotFoundError:
                pass
            print(f"  --- end ---", file=sys.stderr)
            failures += 1

    duration_ms = now_ms() - start_ms
    apc_log("INFO", "parallel_complete", f"{total - failures}/{total} passed",
            {"total": total, "passed": total - failures, "failed": failures,
             "run_ids": run_ids, "duration_ms": duration_ms},
            run_id=parallel_id)

    # Clean up inject dirs
    for d in Path("/tmp").glob(f"agent-spec-inject-{pid}-*"):
        shutil.rmtree(d, ignore_errors=True)

    print(file=sys.stderr)
    print(f"Manifest: {manifest}", file=sys.stderr)
    print("Run IDs:", file=sys.stderr)
    for rid in run_ids:
        print(rid)  # stdout — parseable output

    sys.exit(failures)


if __name__ == "__main__":
    main()
