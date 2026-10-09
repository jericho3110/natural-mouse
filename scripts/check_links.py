"""Check every link in the Markdown docs.

    python scripts/check_links.py              # relative links + web links
    python scripts/check_links.py --offline    # relative links only

Relative links (`docs/MOVEMENT.md`, `../src/...`) must point at a file
that exists. Web links get a HEAD request (GET if HEAD is refused), 8 at
a time, with a timeout; 200-399 counts as working. Sites that refuse
automated checks are listed in BLOCKS_BOTS and only reported.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\]\(([^)\s]+)\)|<(https?://[^>\s]+)>")
BLOCKS_BOTS = ("www.jneurosci.org",)       # answers 403 to scripts; checked by hand
TIMEOUT = 40


def markdown_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md")
                  if not any(part in {"venv", ".venv", "node_modules", ".git"} for part in p.parts))


def links(path: Path) -> list[str]:
    return [a or b for a, b in LINK.findall(path.read_text(encoding="utf-8"))]


def broken_relative(path: Path, target: str) -> bool:
    if target.startswith(("http://", "https://", "#", "mailto:")):
        return False
    return not (path.parent / target.split("#")[0]).resolve().exists()


def status(url: str) -> int | str:
    if not url.startswith(("http://", "https://")):   # urllib would also open file:// and others
        return "refused: not an http(s) URL"
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(  # noqa: S310 - only http(s), checked above
            url, method=method, headers={"User-Agent": "Mozilla/5.0 link-check"})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 - same
                return response.status
        except urllib.error.HTTPError as e:
            code = e.code
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            code = f"no answer ({type(e).__name__})"
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the links in the docs.")
    parser.add_argument("--offline", action="store_true", help="only check relative links")
    args = parser.parse_args(argv)

    problems, web = [], {}
    for path in markdown_files():
        for target in links(path):
            if broken_relative(path, target):
                problems.append(f"{path.relative_to(ROOT)}: missing file {target}")
            elif target.startswith(("http://", "https://")):
                web.setdefault(target, path.relative_to(ROOT))
    if not args.offline:
        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            for url, code in zip(web, pool.map(status, web), strict=True):
                if isinstance(code, int) and 200 <= code < 400:
                    continue
                if any(host in url for host in BLOCKS_BOTS):
                    print(f"note: {url} ({code}): blocks automated checks, verify by hand")
                    continue
                problems.append(f"{web[url]}: {url} -> {code}")
    for problem in problems:
        print(problem)
    checked = "relative links" + ("" if args.offline else f" and {len(web)} web links")
    print(f"{checked}: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
