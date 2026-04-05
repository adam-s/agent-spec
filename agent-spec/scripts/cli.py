#!/usr/bin/env python3
"""agent-spec — Test harness for .claude agents.

Unified CLI entry point. Each subcommand delegates to an existing script.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import PROJECT_DIR, RUN_ROOT, list_evals, list_configs, load_events, get_event


# ── Subcommand handlers ─────────────────────────────────────────

def cmd_run(args):
    """Run an evaluation (single or parallel)."""
    # run_eval.py expects args.eval; cli.py names the positional arg 'target'
    args.eval = args.target
    # Supply defaults for run_eval.py attrs not exposed via cli.py
    if not hasattr(args, "challenge"):
        args.challenge = None
    if not hasattr(args, "prompt_variant"):
        args.prompt_variant = None
    if not hasattr(args, "escalate"):
        args.escalate = False
    # cli.py --parallel is store_true; run_eval.py expects int (concurrency)
    if isinstance(args.parallel, bool):
        args.parallel = args.instances if args.parallel else 1
    if args.parallel > 1 or args.configs or args.models or args.instances > 1:
        import parallel
        parallel.main(args)
    else:
        import run_eval
        run_eval.main(args)


def cmd_status(args):
    """Show run dashboard."""
    if not args.run_id and not args.diff and not args.parallel and not args.latest:
        args.latest = True
    import dashboard
    dashboard.main(args)


def cmd_report(args):
    """Generate reports."""
    import report
    report.main(args)


def cmd_clean(args):
    """Stop processes and remove sandboxes."""
    import cleanup
    cleanup.main(args)


def cmd_tokens(args):
    """Show token metrics (delegates to report.py)."""
    import report
    if args.session:
        report.print_tokens_session(args.session)
    elif args.run_id:
        report.print_tokens_single(args.run_id)
    else:
        print("Usage: agent-spec tokens <run_id> or agent-spec tokens --session <id>", file=sys.stderr)
        sys.exit(1)


def cmd_monitor(args):
    """Show system resource status."""
    import system_monitor
    if args.watch:
        args.command = "watch"
    else:
        args.command = None
    system_monitor.main(args)


def cmd_list(args):
    """Discover and list all evals with their configs."""
    evals = list_evals()
    if not evals:
        print("No evals found.")
        return

    for eval_name in evals:
        last = _latest_result(eval_name)
        suffix = f"  [{last}]" if last else ""
        print(f"{eval_name}{suffix}")
        configs = list_configs(eval_name)
        for c in configs:
            print(f"  {c}")
    print()


def _latest_result(target_name: str) -> str | None:
    """Find the most recent result for a target from /tmp/agent-spec/."""
    if not RUN_ROOT.exists():
        return None
    # Scan run dirs, newest first
    dirs = sorted(RUN_ROOT.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True)
    for d in dirs[:50]:  # only check recent runs
        events_file = d / "events.jsonl"
        if not events_file.exists():
            continue
        events = load_events(events_file)
        started = get_event(events, "agent_started")
        if started and started.get("data", {}).get("target") == target_name:
            score = get_event(events, "score")
            if score:
                return score["data"].get("result", "N/A")
    return None


# ── Parser ──────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog="agent-spec",
        description="Test harness for .claude agents",
        epilog="""examples:
  agent-spec list                          Show all evals and configs
  agent-spec run csv-reporter              Run eval with baseline config
  agent-spec run csv-reporter experimental Run eval with experimental config
  agent-spec run csv-reporter --parallel --instances 3
  agent-spec status                        Show latest run dashboard
  agent-spec report --all                  Report across all runs
  agent-spec clean                         Stop everything""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # ── run ──
    p_run = sub.add_parser("run", help="Run an evaluation")
    p_run.add_argument("target", help="Eval name or path (e.g. 'bug-squashing' or 'intercept/auth-bypass')")
    p_run.add_argument("config", nargs="?", default="baseline", help="Config name (default: baseline)")
    p_run.add_argument("--model", default=None, help="Model override")
    p_run.add_argument("--budget", default=None, help="Budget override (USD)")
    p_run.add_argument("--keep", action="store_true", help="Preserve sandbox after run")
    p_run.add_argument("--inject", default=None, help="Directory to inject into sandbox")
    p_run.add_argument("--port", type=int, default=None, help="Port override")
    p_run.add_argument("--parallel", action="store_true", help="Run in parallel mode")
    p_run.add_argument("--instances", type=int, default=1, help="Number of parallel instances")
    p_run.add_argument("--configs", default="", help="Comma-separated configs for A/B test")
    p_run.add_argument("--models", default="", help="Comma-separated models for benchmarking")
    p_run.add_argument("--stimuli-dir", default="", help="Per-instance inject files")
    p_run.add_argument("--stream", action="store_true", help="Use stream-json for real-time Claude events")
    p_run.add_argument("--verbose", action="store_true", help="Show sandbox lifecycle details")
    p_run.set_defaults(func=cmd_run)

    # ── status ──
    p_status = sub.add_parser("status", help="Show run dashboard")
    p_status.add_argument("run_id", nargs="?", help="Run ID (default: latest)")
    p_status.add_argument("--latest", action="store_true", help="Show most recent run")
    p_status.add_argument("--summary", action="store_true", help="One-shot summary")
    p_status.add_argument("--stream", action="store_true", help="Compact no-color output")
    p_status.add_argument("--diff", nargs=2, metavar="RUN_ID", help="Config diff between two runs")
    p_status.add_argument("--parallel", metavar="PARALLEL_ID", help="Multi-instance status table")
    p_status.set_defaults(func=cmd_status)

    # ── report ──
    p_report = sub.add_parser("report", help="Generate comparison reports")
    p_report.add_argument("run_ids", nargs="*", help="Run IDs to report on")
    p_report.add_argument("--all", action="store_true", dest="show_all", help="Show all runs")
    p_report.add_argument("--latest", action="store_true", help="Show most recent run")
    p_report.add_argument("--group-by", choices=["config", "model", "target"], help="Group by field")
    p_report.add_argument("--compare", nargs=2, metavar="RUN_ID", help="Side-by-side comparison")
    p_report.add_argument("--session", metavar="SESSION_ID", help="Iterate session report")
    p_report.set_defaults(func=cmd_report)

    # ── tokens ──
    p_tokens = sub.add_parser("tokens", help="Show token metrics and costs")
    p_tokens.add_argument("run_id", nargs="?", help="Run ID")
    p_tokens.add_argument("--session", metavar="SESSION_ID", help="Session cost rollup")
    p_tokens.set_defaults(func=cmd_tokens)

    # ── clean ──
    p_clean = sub.add_parser("clean", help="Stop processes, clear ports, remove sandboxes")
    p_clean.add_argument("--force", action="store_true", help="Also delete /tmp run logs")
    p_clean.set_defaults(func=cmd_clean)

    # ── monitor ──
    p_monitor = sub.add_parser("monitor", help="Show system resource status")
    p_monitor.add_argument("--watch", action="store_true", help="Continuous monitoring")
    p_monitor.add_argument("--interval", type=int, default=10, help="Watch interval in seconds")
    p_monitor.set_defaults(func=cmd_monitor)

    # ── list ──
    p_list = sub.add_parser("list", help="List all evals and their configs")
    p_list.set_defaults(func=cmd_list)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
