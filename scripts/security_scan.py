"""Security scan: part of the check gate (scripts/check.py) and CI.

    python scripts/security_scan.py              # everything, including pip-audit
    python scripts/security_scan.py --offline    # skip pip-audit (no network)

Three kinds of check; exit code 0 = clean, 1 = findings:

1. **Dependencies**: `pip-audit` looks up every installed package in
   the Python Packaging Advisory Database (PyPA) and OSV for known
   vulnerabilities.
2. **Dangerous patterns** in the code: eval/exec, pickle/marshal, shell
   commands, unsafe YAML, listening on all interfaces, switched-off TLS
   checks, insecure temp files.
3. **Invariants** for the files git tracks: no secrets (private keys,
   tokens), no personal email addresses, no real-looking IP addresses
   (only RFC 5737 documentation ranges and loopback), and none of the
   user-specific files (screenshots in templates/, targets.json).

A line can opt out of a *pattern* check with a comment saying why:
`# security-scan: allow <reason>`. Invariants can't be opted out of.
The scanner's own pattern definitions are skipped, since they must
contain the patterns. Tests that prove each check fires:
tests/test_security_scan.py.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import shutil
import subprocess  # security-scan: allow runs git and pip-audit with fixed argument lists, no shell
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOW = "security-scan: allow"

# (name, regex): code patterns that can run arbitrary code, weaken
# transport security, or expose a local server.
DANGEROUS = [
    ("eval/exec", re.compile(r"\b(eval|exec)\s*\(")),
    ("pickle/marshal (unsafe deserialisation)", re.compile(r"\b(pickle|marshal|shelve)\.(loads?|Unpickler)\b")),
    ("shell command", re.compile(r"\bos\.(system|popen)\s*\(|shell\s*=\s*True")),
    ("subprocess", re.compile(r"^\s*(import subprocess|from subprocess import)")),
    ("unsafe YAML load", re.compile(r"\byaml\.load\s*\((?![^)]*SafeLoader)")),
    ("dynamic import", re.compile(r"\b__import__\s*\(")),
    ("listening on all interfaces", re.compile(r"""["']0\.0\.0\.0["']""")),
    ("TLS verification off", re.compile(r"verify\s*=\s*False|_create_unverified_context|CERT_NONE")),
    ("insecure temp file", re.compile(r"\btempfile\.mktemp\s*\(")),
]

# Invariants: no secrets or personal data in tracked files.
SECRETS = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("JSON web token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.")),
    ("personal email address", re.compile(
        r"\b[\w.+-]+@(gmail|yahoo|hotmail|outlook|icloud|proton(mail)?)\.(com|me)\b", re.I)),
]
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
SAFE_NETWORKS = [ipaddress.ip_network(n) for n in (
    "127.0.0.0/8",         # loopback
    "0.0.0.0/32",          # "any" placeholder (DANGEROUS catches it as a listener)
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24",   # RFC 5737 documentation ranges
)]
TEXT_SUFFIXES = {".py", ".md", ".toml", ".txt", ".html", ".json", ".yml", ".yaml", ".cfg", ".ini", ""}
FORBIDDEN_FILES = [
    (re.compile(r"^templates/(?!\.gitkeep$)"), "a screenshot in templates/ (user screen content)"),
    (re.compile(r"(^|/)targets\.json$"), "targets.json (the GUI's saved targets)"),
    (re.compile(r"(^|/)\.env$"), ".env (secrets)"),
    (re.compile(r"\.(png|jpe?g|bmp|gif)$"), "an image outside docs/images/"),
]
SCANNER_ITSELF = "scripts/security_scan.py"


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str
    text: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.kind}: {self.text.strip()[:100]}"


def scan_text(path: str, text: str) -> list[Finding]:
    """Every finding in one file's text. Pure: no file access."""
    findings = []
    is_python = path.endswith(".py")
    for number, line in enumerate(text.splitlines(), 1):
        if path != SCANNER_ITSELF:
            if is_python and ALLOW not in line:
                findings += [Finding(path, number, name, line) for name, rx in DANGEROUS if rx.search(line)]
            findings += [Finding(path, number, name, line) for name, rx in SECRETS if rx.search(line)]
        for match in IPV4.finditer(line):
            try:
                ip = ipaddress.ip_address(match.group())
            except ValueError:          # e.g. 999.1.1.1: not an address
                continue
            if not any(ip in net for net in SAFE_NETWORKS) and not _looks_like_a_version(line, match):
                findings.append(Finding(path, number, f"real-looking IP address {ip}", line))
    return findings


def _looks_like_a_version(line: str, match: re.Match) -> bool:
    """'opencv-python 4.10.0.84' is a version, not an address."""
    before = line[:match.start()].rstrip().lower()
    return before.endswith(("version", "==", ">=", "<=", "~=", "python", "v")) or "version" in before[-20:]


def scan_paths(paths: list[str]) -> list[Finding]:
    findings = []
    for rel in paths:
        for rx, why in FORBIDDEN_FILES:
            if rx.search(rel) and not rel.startswith("docs/images/"):
                findings.append(Finding(rel, 0, f"must not be committed: {why}", rel))
        path = ROOT / rel
        if path.suffix.lower() in TEXT_SUFFIXES and path.is_file():
            findings += scan_text(rel, path.read_text(encoding="utf-8", errors="replace"))
    return findings


def tracked_files() -> list[str]:
    git = shutil.which("git")   # the full path, not whatever "git" is first on PATH at run time
    if git is None:
        raise SystemExit("git isn't installed or not on PATH")
    out = subprocess.run([git, "ls-files"], cwd=ROOT,  # noqa: S603 - fixed arguments, no shell, no user input
                         capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line]


def pip_audit() -> tuple[bool, str]:
    """(clean?, report). Audits the packages installed in this Python."""
    result = subprocess.run([sys.executable, "-m", "pip_audit", "--progress-spinner", "off"],
                            capture_output=True, text=True)
    if "No module named pip_audit" in result.stderr:
        return False, "pip-audit isn't installed: pip install pip-audit (or use --offline)"
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Security scan for natural-mouse.")
    parser.add_argument("--offline", action="store_true", help="skip pip-audit (it needs the network)")
    args = parser.parse_args(argv)

    files = tracked_files()
    findings = scan_paths(files)
    for finding in findings:
        print(finding)
    print(f"patterns + invariants: {len(files)} tracked files, {len(findings)} finding(s)")

    audit_ok = True
    if args.offline:
        print("dependencies: skipped (--offline)")
    else:
        audit_ok, report = pip_audit()
        print("dependencies (pip-audit):", "no known vulnerabilities" if audit_ok else "PROBLEMS")
        if not audit_ok:
            print(report)
    return 0 if not findings and audit_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
