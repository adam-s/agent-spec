#!/usr/bin/env python3
"""run_eval.py — Run an evaluation by eval name.

Usage:
  python3 scripts/run_eval.py <eval> [config] [options]
  python3 scripts/run_eval.py <eval> [config] --challenge <name> [options]
"""

import argparse
import concurrent.futures
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (
    PROJECT_DIR, SCRIPTS_DIR, DEFAULT_MODEL, DEFAULT_BUDGET,
    parse_eval_md, require_dir, require_file, die,
    list_evals, list_configs,
)


def run_single(eval_dir, config_dir, cfg, args, challenge_name=None, challenge_dir=None):
    """Run a single challenge × config combination."""

    # Determine workspace source
    if challenge_dir:
        # Matrix eval: workspace from seeds
        seeds_dir = challenge_dir / "seeds"
        source_path = None
        if args.prompt_variant:
            prompt_file_path = challenge_dir / f"prompt-{args.prompt_variant}.md"
            if not prompt_file_path.exists():
                die(f"Prompt variant '{args.prompt_variant}' not found: {prompt_file_path}")
        else:
            prompt_file_path = challenge_dir / "prompt.md"
        verify_path = challenge_dir / "verify.sh"
        setup_script = challenge_dir / "setup.sh"
        setup_cmds = setup_script.read_text().strip() if setup_script.exists() else ""
    else:
        # Single-challenge eval: workspace from source
        seeds_dir = None
        source_path = (eval_dir / cfg["source"]).resolve() if cfg.get("source") else None
        # Prompt from EVAL.md body
        prompt_text = cfg.get("prompt", "")
        if not prompt_text:
            die("EVAL.md has no prompt body")
        verify_path = eval_dir / cfg.get("verify", "verify.sh")
        setup_cmds = ";".join(cfg.get("setup", []))

    # Write prompt to temp file
    if challenge_dir:
        require_file(prompt_file_path, f"No prompt.md in challenge {challenge_name}")
        prompt_text = prompt_file_path.read_text()

    prompt_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, prefix='eval-prompt-')
    prompt_file.write(prompt_text)
    prompt_file.close()

    # Build invoke.py args
    model = args.model or cfg.get("model") or DEFAULT_MODEL
    budget = args.budget or cfg.get("budget") or DEFAULT_BUDGET

    invoke_args = [
        sys.executable, str(SCRIPTS_DIR / "invoke.py"),
    ]

    if source_path:
        invoke_args.append(str(source_path))
    invoke_args += [
        str(config_dir),
        prompt_file.name,
        "--model", model,
        "--budget", budget,
    ]

    if verify_path.exists():
        invoke_args += ["--verify", str(verify_path)]
    if seeds_dir and seeds_dir.is_dir():
        invoke_args += ["--seeds", str(seeds_dir)]
    if cfg.get("delete"):
        invoke_args += ["--delete", ",".join(cfg["delete"])]
    if setup_cmds:
        invoke_args += ["--setup", setup_cmds]
    if challenge_name:
        invoke_args += ["--challenge", challenge_name]
    invoke_args += ["--eval-name", eval_dir.name]
    if args.keep:
        invoke_args.append("--keep")
    if args.port is not None:
        invoke_args += ["--port", str(args.port)]
    if getattr(args, "stream", False):
        invoke_args.append("--stream")

    return subprocess.run(invoke_args).returncode


def main(args=None):
    parser = argparse.ArgumentParser(description="Run eval by name")
    parser.add_argument("eval", help="Eval name (directory in evals/)")
    parser.add_argument("config", nargs="?", default="baseline", help="Config name (default: baseline)")
    parser.add_argument("--model", default=None)
    parser.add_argument("--budget", default=None)
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--stream", action="store_true", help="Use stream-json for real-time Claude events")
    parser.add_argument("--challenge", default=None, help="Run only this challenge (matrix evals)")
    parser.add_argument("--prompt-variant", default=None, metavar="VARIANT",
                        help="Use prompt-VARIANT.md instead of prompt.md (e.g. --prompt-variant vague)")
    parser.add_argument("--parallel", type=int, default=1, metavar="N",
                        help="Max challenges to run concurrently (default: 1 = sequential)")
    args = args or parser.parse_args()

    eval_dir = PROJECT_DIR / "evals" / args.eval
    if not eval_dir.is_dir():
        available = list_evals()
        die(f"Eval '{args.eval}' not found. Available: {', '.join(available) if available else 'none'}")

    # Resolve config
    config_dir = eval_dir / "configs" / args.config
    if not config_dir.is_dir():
        available = list_configs(args.eval)
        if args.config == "baseline" and available:
            args.config = available[0]
            config_dir = eval_dir / "configs" / args.config
            print(f"  No 'baseline' config — using '{args.config}'", file=sys.stderr)
        else:
            die(f"Config '{args.config}' not found. Available: {', '.join(available) if available else 'none'}")

    # Parse EVAL.md
    eval_file = eval_dir / "EVAL.md"
    require_file(eval_file, "No EVAL.md")
    cfg = parse_eval_md(eval_file)

    # Detect eval type: matrix (has challenges/) or single
    challenges_dir = eval_dir / "challenges"
    if challenges_dir.is_dir():
        # Matrix eval — run all challenges (or just one if --challenge specified)
        challenges = sorted(d.name for d in challenges_dir.iterdir() if d.is_dir())
        if args.challenge:
            if args.challenge not in challenges:
                die(f"Challenge '{args.challenge}' not found. Available: {', '.join(challenges)}")
            challenges = [args.challenge]

        if args.parallel > 1 and len(challenges) > 1:
            max_workers = min(args.parallel, len(challenges))
            print(f"  Running {len(challenges)} challenges ({max_workers} concurrent)", file=sys.stderr)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(run_single, eval_dir, config_dir, cfg, args,
                                challenge_name=ch, challenge_dir=challenges_dir / ch): ch
                    for ch in challenges
                }
                for future in concurrent.futures.as_completed(futures):
                    ch = futures[future]
                    rc = future.result()
                    if rc != 0:
                        print(f"  Challenge '{ch}' failed (exit {rc})", file=sys.stderr)
        else:
            for ch in challenges:
                run_single(eval_dir, config_dir, cfg, args,
                           challenge_name=ch, challenge_dir=challenges_dir / ch)
    else:
        # Single-challenge eval
        if not cfg.get("source"):
            die("Single-challenge eval requires 'source' in EVAL.md")
        run_single(eval_dir, config_dir, cfg, args)


if __name__ == "__main__":
    main()
