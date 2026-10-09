# Security

## Contents

- [Reporting a problem](#reporting-a-problem)
- [What the library can do on your machine](#what-the-library-can-do-on-your-machine)
- [Threat model and defences](#threat-model-and-defences)
- [Ways code could run (RCE review)](#ways-code-could-run-rce-review)
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

## Accepted risks

- It controls the real mouse: a bug in *your* script can click the
  wrong thing. Use `FailSafeExecutor` and `RegionGuardPlugin` while
  developing.
- Plugins loaded by name run with your permissions (see above).

## References

- GitHub Docs, [Privately reporting a security vulnerability](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
- Python Packaging User Guide, [creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)
- OWASP, [Code Injection](https://owasp.org/www-community/attacks/Code_Injection)
