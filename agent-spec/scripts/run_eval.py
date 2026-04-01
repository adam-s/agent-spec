#!/usr/bin/env python3
"""run_eval.py — Run an evaluation by target name.

Usage: python3 scripts/run_eval.py <target> [config] [options]
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (
    PROJECT_DIR, SCRIPTS_DIR, DEFAULT_MODEL, DEFAULT_BUDGET,
    parse_target_yaml, require_dir, require_file, die,
)


def main():
    parser = argparse.ArgumentParser(description="Run eval by target name")
    parser.add_argument("target", help="Target name (directory in targets/)")
    parser.add_argument("config", nargs="?", default="baseline", help="Config name (default: baseline)")
    parser.add_argument("--model", default=None)
    parser.add_argument("--budget", default=None)
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--inject", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    target_dir = PROJECT_DIR / "targets" / args.target
    require_dir(target_dir, "Target not found")

    # Resolve config: target-specific first, then _shared
    config_dir = target_dir / "configs" / args.config
    if not config_dir.is_dir():
        config_dir = PROJECT_DIR / "targets" / "_shared" / "configs" / args.config
        require_dir(config_dir, f"Config '{args.config}' not found in target or _shared")

    # Parse target.yaml
    yaml_file = target_dir / "target.yaml"
    require_file(yaml_file, "No target.yaml")
    cfg = parse_target_yaml(yaml_file)

    # Resolve source path
    source_path = (target_dir / cfg["source"]).resolve()
    if not source_path.is_dir():
        die(f"Source repo not found: {cfg['source']} (from {target_dir})")

    # Lint: warn on hardcoded ports
    prompt_file = target_dir / "prompt.md"
    if prompt_file.exists():
        text = prompt_file.read_text()
        if re.search(r'\b3[01]\d{2}\b', text):
            print("WARNING: prompt.md may contain hardcoded port — use __PORT__", file=sys.stderr)

    # Build invoke.py args
    model = args.model or cfg["model"] or DEFAULT_MODEL
    budget = args.budget or cfg["budget"] or DEFAULT_BUDGET

    invoke_args = [
        sys.executable, str(SCRIPTS_DIR / "invoke.py"),
        str(source_path),
        str(config_dir),
        str(target_dir / "prompt.md"),
        "--model", model,
        "--budget", budget,
        "--verify", str(target_dir / cfg["verify"]),
    ]

    if cfg["delete_before_run"]:
        invoke_args += ["--delete", ",".join(cfg["delete_before_run"])]
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
