#!/usr/bin/env python3
"""cache_fixes.py — Generate fix.diff files for bug-squashing challenges.

Clones each repo, extracts the fix commit diff, and saves it to the
challenge directory. Run once, or whenever benchmark.md changes.

Usage: python3 scripts/cache_fixes.py
"""

import re
import subprocess
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CHALLENGES_DIR = PROJECT_DIR / "evals" / "bug-squashing" / "challenges"
BENCHMARK = PROJECT_DIR / "evals" / "bug-squashing" / "benchmark.md"

# Parse benchmark.md to extract challenge metadata
CHALLENGES = {
    "rich-infinite-loop": {
        "repo": "https://github.com/Textualize/rich.git",
        "commit": "7338cb9dafd0d0e916585f191ae505b3e602bb51",
    },
    "marshmallow-email-idn": {
        "repo": "https://github.com/marshmallow-code/marshmallow.git",
        "commit": "f07eadc87dfac25ed505d5cd9d186920f2682733",
    },
    "arrow-humanize-month": {
        "repo": "https://github.com/arrow-py/arrow.git",
        "commit": "b423717da81aaf8117313b4b377efaa6413a9639",
    },
    "werkzeug-bearer-whitespace": {
        "repo": "https://github.com/pallets/werkzeug.git",
        "commit": "dafe7f1e37cf78cc7f11a9706c62a23e0dba9010",
    },
    "botocore-chunked-upload": {
        "repo": "https://github.com/boto/botocore.git",
        "commit": "b2e20b2d4e6ee92b7f46bbad73a5a9a7abe18b28",
    },
    "textual-selection-disappearing": {
        "repo": "https://github.com/Textualize/textual.git",
        "commit": "04b03c8db64266a6a7811cc161bae9986e53b1a1",
    },
    "aiohttp-zstd-multiframe": {
        "repo": "https://github.com/aio-libs/aiohttp.git",
        "commit": "cfcad08dbd4c2c4247f505d9a34ff5c09586b42e",
    },
    "httpcore-keepalive": {
        "repo": "https://github.com/encode/httpcore.git",
        "commit": "10a658221deb38a4c5b16db55ab554b0bf731707",
    },
    "sqlalchemy-orm-update-wrong-column": {
        "repo": "https://github.com/sqlalchemy/sqlalchemy.git",
        "commit": "dc0d0817622435ea46b33575fd4f84d3959dc42d",
    },
}


def cache_fix(name: str, repo_url: str, commit: str) -> bool:
    """Clone repo, extract fix diff, save to challenge directory."""
    challenge_dir = CHALLENGES_DIR / name
    if not challenge_dir.is_dir():
        print(f"  SKIP {name}: no challenge directory")
        return False

    fix_path = challenge_dir / "fix.diff"

    with tempfile.TemporaryDirectory(prefix=f"fix-{name}-") as tmpdir:
        # Clone with enough depth to reach merge parents
        subprocess.run(
            ["git", "clone", "--depth", "50", "--no-checkout", repo_url, tmpdir],
            capture_output=True, text=True,
        )

        # Fetch the specific commit
        subprocess.run(
            ["git", "-C", tmpdir, "fetch", "origin", commit],
            capture_output=True, text=True,
        )

        # Check if it's a merge commit (has 2+ parents)
        parents = subprocess.run(
            ["git", "-C", tmpdir, "rev-parse", f"{commit}^2"],
            capture_output=True, text=True,
        )
        if parents.returncode == 0:
            # Merge commit: diff the feature branch against first parent
            result = subprocess.run(
                ["git", "-C", tmpdir, "diff", f"{commit}^1", f"{commit}^2"],
                capture_output=True, text=True,
            )
        else:
            # Regular commit: show the diff
            result = subprocess.run(
                ["git", "-C", tmpdir, "show", commit],
                capture_output=True, text=True,
            )

        if result.returncode != 0 or not result.stdout.strip():
            print(f"  FAIL {name}: could not get diff for {commit[:8]}")
            return False

        # For merge commits, prepend the commit message for context
        if parents.returncode == 0:
            msg = subprocess.run(
                ["git", "-C", tmpdir, "show", "--no-patch", commit],
                capture_output=True, text=True,
            )
            output = msg.stdout + "\n" + result.stdout if msg.returncode == 0 else result.stdout
        else:
            output = result.stdout

        fix_path.write_text(output)
        lines = result.stdout.count("\n")
        print(f"  OK   {name}: {lines} lines -> fix.diff")
        return True


def main():
    print("Caching fix diffs for bug-squashing challenges\n")
    ok = 0
    for name, info in CHALLENGES.items():
        if cache_fix(name, info["repo"], info["commit"]):
            ok += 1
    print(f"\n{ok}/{len(CHALLENGES)} cached")


if __name__ == "__main__":
    main()
