# Security

## Contents

- [Reporting a problem](#reporting-a-problem)
- [What the library can do on your machine](#what-the-library-can-do-on-your-machine)
- [Threat model and defences](#threat-model-and-defences)
- [Ways code could run (RCE review)](#ways-code-could-run-rce-review)
- [Automated checks](#automated-checks)
- [Review findings](#review-findings)
- [Accepted risks](#accepted-risks)
- [References](#references)

## Reporting a problem

Please use GitHub's **private vulnerability reporting** on this
repository (Security tab → "Report a vulnerability") rather than a
public issue.

## What the library can do on your machine

`natural_mouse` moves the real cursor, clicks, scrolls, and reads the
screen (screenshots, to find things). It does that only when your code
calls it, and only while that call runs: nothing loops, schedules, or
runs in the background. Screenshots are kept in memory, except
`capture_region` (which you call to save a template) and
`ScreenshotOnMissPlugin` (which saves to the folder you give it).

## Threat model and defences

| Risk | Defence | Where / test |
| --- | --- | --- |
| A runaway script keeps clicking | `FailSafeExecutor` stops the moment you move the mouse, or when the cursor is in the top-left corner | `extensions/executors.py`; `tests/test_extensions.py` |
| Clicks land somewhere unintended | `RegionGuardPlugin` cancels any click/scroll outside allowed rectangles | `plugins/region_guard.py`; `tests/test_plugins.py` |
| The test bench's web server is reached by other programs or sites | binds `127.0.0.1` only, random port, random token (constant-time compare), `Host` header check (DNS rebinding), body/event limits, JSON-only, strict CSP | `testbench/server.py`; `tests/test_testbench_server.py`; [TESTBENCH.md §6](TESTBENCH.md#6-security) |
| Coordinates in the wrong units on scaled displays | the process is made DPI-aware before any input | `input/win32_executor.py`; `tests/test_win32_executor.py` |
| Personal screen content committed by accident | `templates/*` and `targets.json` are gitignored | `.gitignore` |

## Ways code could run (RCE review)

- **No `eval`, `exec`, `pickle`, or shell commands** anywhere in the
  library or apps.
- **Plugins by name**: `PluginManager.load_path("pkg.module:Class")` and
  `load_entry_points()` import Python code. That's by design (it's how
  plugins work), so only load plugins you trust, the same as `import`.
- **Images**: template images are read with OpenCV (`cv2.imread`), so a
  malicious image file is as risky as OpenCV's decoder. Use your own
  screenshots.
- **The test bench** accepts JSON from its page and only parses
  (`json.loads`) and counts it; nothing received is executed or written
  to disk.
- **The scripts** run `ruff`, `unittest`, `git` and `pip-audit` with
  `subprocess.run` and a fixed argument *list*: never a shell, never
  user input in the command. `git` is resolved to its full path
  (`shutil.which`), so a program named `git` earlier on PATH isn't run
  by accident.
- **Link checking** refuses anything but `http://` and `https://`
  (`urllib` would also open `file://`).

## Automated checks

`python scripts/check.py` runs everything below and fails (exit code 1)
if anything fails. CI runs it on Windows for every push and pull
request (`.github/workflows/ci.yml`, read-only permissions).

| Check | Tool | What it catches |
| --- | --- | --- |
| Known-vulnerable dependencies | `pip-audit` (in `scripts/security_scan.py`, and as its own CI step) | any installed package with a published advisory. Result on 2026-10-09: **no known vulnerabilities** |
| Dangerous code patterns | `scripts/security_scan.py` | `eval`/`exec`, `pickle`/`marshal`, shell commands, `subprocess` (must carry a reason), unsafe YAML, `__import__`, listening on `0.0.0.0`, TLS verification off, `tempfile.mktemp` |
| Invariants | same | private keys, GitHub/AWS tokens, JWTs, personal email addresses, real-looking IPs (only RFC 5737 and loopback allowed), screenshots in `templates/`, `targets.json`, `.env`, images outside `docs/images/` |
| Security lint | Ruff's `S` (bandit) rules | e.g. partial executable paths (S607), `urllib` with any scheme (S310), weak random for secrets (S311), hard-coded passwords (S105/S106) |
| Updates | Dependabot | pull requests for new versions of dependencies and actions |

**Proven to work**: `tests/test_security_scan.py` plants a bad line for
every pattern and every invariant (in strings and temporary files, never
in the real code) and checks each is caught; it also checks normal code
stays quiet, and that a whole run on a temporary repo fails, then passes
once the planted line is fixed.

A pattern check can be waived on one line with
`# security-scan: allow <reason>`; invariants can't be waived.

## Review findings

Review of 2026-10-09 (every file that writes files, loads code, opens
URLs or starts processes, plus the full lint):

| Finding | Fix | Test that pins it |
| --- | --- | --- |
| `ScreenshotOnMissPlugin` named files straight from the query: a colour like `#ff00ff` or text with `:`/`*`/`?` makes Windows refuse the name, and `cv2.imwrite` fails *silently* (returns `False`) while the plugin recorded the file as saved | `safe_stem()`: only letters, digits, `-`, `_`, max 60; `imwrite`'s result is checked and a failure raises `OSError` | `tests/test_screenshot_on_miss.py` |
| `check_links.status()` would have opened any URL scheme `urllib` supports | refuses non-`http(s)` URLs | checked by hand: `file://` → "refused" |
| the scanner ran `git` by bare name | full path via `shutil.which`; clear error if missing | Ruff S607 in the gate |
| at display scaling > 100%, coordinates changed units mid-run (found earlier, live) | DPI awareness set when the executor is created | `tests/test_win32_executor.py` |

## Accepted risks

- It controls the real mouse: a bug in *your* script can click the
  wrong thing. Use `FailSafeExecutor` and `RegionGuardPlugin` while
  developing.
- Plugins loaded by name run with your permissions (see above).

## References

- GitHub Docs, [Privately reporting a security vulnerability](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
- Python Packaging User Guide, [creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)
- OWASP, [Code Injection](https://owasp.org/www-community/attacks/Code_Injection)
