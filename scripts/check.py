"""The check gate: everything that must pass before a commit (and in CI).

    python scripts/check.py              # lint, tests, links, security (needs the network)
    python scripts/check.py --offline    # same, minus web links and pip-audit

Each step runs in its own process and the gate fails if any step fails
(exit code 1). Commit only when it says "all checks passed": gate on
this command's exit code, never on filtered output.
"""

from __future__ import annotations

import argparse
import subprocess  # security-scan: allow runs this project's own tools with fixed argument lists, no shell
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def steps(offline: bool) -> list[tuple[str, list[str]]]:
    extra = ["--offline"] if offline else []
    return [
        ("lint (ruff)", [sys.executable, "-m", "ruff", "check", "."]),
        ("tests (unittest)", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."]),
        ("links", [sys.executable, "scripts/check_links.py", *extra]),
        ("security", [sys.executable, "scripts/security_scan.py", *extra]),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run every check.")
    parser.add_argument("--offline", action="store_true", help="skip the checks that need the network")
    args = parser.parse_args(argv)

    failed = []
    for name, command in steps(args.offline):
        print(f"\n=== {name} ===", flush=True)
        if subprocess.run(command, cwd=ROOT).returncode != 0:  # noqa: S603 - fixed commands, no shell
            failed.append(name)
    print("\n" + ("all checks passed" if not failed else f"FAILED: {', '.join(failed)}"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
