#!/usr/bin/env python3
"""run_eval.py — Run an evaluation by eval name.

Usage: python3 scripts/run_eval.py <eval> [config] [options]
"""

import argparse
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


def main(args=None):
    parser = argparse.ArgumentParser(description="Run eval by name")
    parser.add_argument("eval", help="Eval name (directory in evals/)")
    parser.add_argument("config", nargs="?", default="baseline", help="Config name (default: baseline)")
    parser.add_argument("--model", default=None)
    parser.add_argument("--budget", default=None)
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--inject", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = args or parser.parse_args()

    eval_dir = PROJECT_DIR / "evals" / args.eval
    if not eval_dir.is_dir():
        available = list_evals()
        die(f"Eval '{args.eval}' not found. Available: {', '.join(available) if available else 'none'}")

    # Resolve config
    config_dir = eval_dir / "configs" / args.config
    if not config_dir.is_dir():
        available = list_configs(args.eval)
        die(f"Config '{args.config}' not found. Available: {', '.join(available) if available else 'none'}")

    # Parse EVAL.md
    eval_file = eval_dir / "EVAL.md"
    require_file(eval_file, "No EVAL.md")
    cfg = parse_eval_md(eval_file)

    # Resolve source path
    source_path = (eval_dir / cfg["source"]).resolve()
    if not source_path.is_dir():
        die(f"Source repo not found: {cfg['source']} (from {eval_dir})")

    # Write prompt to temp file (from EVAL.md body)
    prompt = cfg.get("prompt", "")
    if not prompt:
        die("EVAL.md has no prompt body (content after frontmatter)")

    # Lint: warn on hardcoded ports
    if re.search(r'\b3[01]\d{2}\b', prompt):
        print("WARNING: prompt may contain hardcoded port — use __PORT__", file=sys.stderr)

    # Write prompt to a temp file for invoke.py
    prompt_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, prefix='eval-prompt-')
    prompt_file.write(prompt)
    prompt_file.close()

    # Build invoke.py args
    model = args.model or cfg["model"] or DEFAULT_MODEL
    budget = args.budget or cfg["budget"] or DEFAULT_BUDGET

    invoke_args = [
        sys.executable, str(SCRIPTS_DIR / "invoke.py"),
        str(source_path),
        str(config_dir),
        prompt_file.name,
        "--model", model,
        "--budget", budget,
        "--verify", str(eval_dir / cfg["verify"]),
    ]

    if cfg["delete"]:
        invoke_args += ["--delete", ",".join(cfg["delete"])]
    if cfg["setup"]:
        invoke_args += ["--setup", ";".join(cfg["setup"])]
    if args.keep:
        invoke_args.append("--keep")
    if args.inject:
        invoke_args += ["--inject", args.inject]
    if args.port is not None:
        invoke_args += ["--port", str(args.port)]

    os.execvp(sys.executable, invoke_args)


if __name__ == "__main__":
    main()
