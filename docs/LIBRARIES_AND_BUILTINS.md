# Libraries and built-ins

Every standard-library module, external library, built-in function,
dunder method, decorator and notable language feature this project
uses: **where** (file), **what for**, **why**, and the alternatives.
Paths are relative to `src/` unless they start with `tests/`,
`scripts/` or `examples/`. Checked against the imports on 2026-10-09
(a `grep` of every `import` line).

## Contents

- [1. The policy](#1-the-policy)
- [2. External libraries](#2-external-libraries)
- [3. Standard-library modules](#3-standard-library-modules)
- [4. Built-in functions](#4-built-in-functions)
- [5. Dunder methods and attributes](#5-dunder-methods-and-attributes)
- [6. Decorators](#6-decorators)
- [7. Language features worth knowing](#7-language-features-worth-knowing)
- [8. Development tools](#8-development-tools)
- [9. Exercises](#9-exercises)
- [References](#references)

## 1. The policy

Standard library first. An external library has to do something the
standard library can't do well. This project has three runtime
dependencies, one optional extra, and two development tools:

| Need | Used | Kind |
| --- | --- | --- |
| Find an image on the screen | OpenCV (`opencv-python`) | runtime |
| Arrays of pixels | NumPy | runtime (OpenCV needs it anyway) |
| Fast screenshots | `mss` | runtime |
| Move the mouse, click, scroll | `ctypes` → Windows' `SendInput` | standard library |
| Lint, security audit | Ruff, pip-audit | `[dev]` extra, never imported by the library |

## 2. External libraries

| Library | Where | What for | Why this one | Alternatives |
| --- | --- | --- | --- | --- |
| **opencv-python** (`cv2`) ≥ 4.9 | `natural_mouse/vision/template_locator.py`, `color_locator.py`, `screen.py`, `capture.py`, `extensions/locators.py`, `plugins/screenshot_on_miss.py`, `pathlab/render.py` | `matchTemplate` (find an image), `inRange` + `connectedComponentsWithStats` (find a colour block), `cvtColor`, `imread`/`imwrite`, `resize`, and the drawing functions (`polylines`, `addWeighted`, `putText`, `circle`, `line`, `rectangle`) for the path lab picture | the standard tool for image matching; one dependency covers both matching and drawing | Pillow (no template matching), scikit-image (slower, bigger), matplotlib for the picture (another large dependency) |
| **numpy** ≥ 1.26 | `screen.py`, `vision/*`, `extensions/locators.py`, `pathlab/render.py`, tests | OpenCV images *are* NumPy arrays; `np.full` makes the blank canvas; `np.where` finds every match above a threshold | required by OpenCV | — |
| **mss** ≥ 9.0 | `screen.py` | grabs the screen (or a region) quickly, as raw BGRA pixels | fast, small, pure Python over Windows' GDI; also makes the process DPI-aware (see `input/win32_executor.py` for why that matters) | Pillow's `ImageGrab` (slower), `pyautogui.screenshot` (uses Pillow) |
| **playwright** | — | not used here | — | the AdsPower library uses it for its proxy check; this library has no browser code |

## 3. Standard-library modules

### Language, types and data

| Module | What we use | Where | Why |
| --- | --- | --- | --- |
| `__future__` | `annotations` | almost every module | type hints are stored as text, not evaluated at import (PEP 563): `X \| None` works on 3.10 and classes can name themselves |
| `abc` | `ABC`, `@abstractmethod` | `input/base.py`, `path/base.py`, `vision/base.py` | the three *strategy interfaces* (`InputExecutor`, `PathGenerator`, `ScreenLocator`): a subclass that forgets a method fails when created, not halfway through a click |
| `dataclasses` | `@dataclass`, `frozen=True`, `field`, `replace` | `geometry.py`, `path/base.py`, `path/fitts.py`, `path/bezier.py` (`replace`), `vision/base.py`, `plugins/base.py`, `pathlab/stats.py`, `testbench/*`, `scripts/security_scan.py` | value objects with `__init__`/`__eq__`/`__repr__` written for you; `frozen` = immutable, so `Point(0, 0)` can be shared safely as a default; `replace` copies a `MovementProfile` with a few fields changed (the overshoot correction) |
| `typing` | `TYPE_CHECKING` | `geometry.py`, `plugins/base.py` | an import only type checkers see: breaks the import cycle path → geometry → path |
| `collections.abc` | `Callable`, `Iterable`, `Sequence`, `Iterator` | `path/easing.py`, `pluggable.py`, `plugins/manager.py`, `extensions/*`, `vision/color_locator.py` | abstract types for hints: "anything iterable", not only `list` |
| `collections` | `defaultdict` | `plugins/stats.py` | counters and lists that start empty, so `counts[action]["found"] += 1` needs no setup |
| `enum` | — | not used in the library | — |

### Maths and randomness

| Module | What we use | Where | Why |
| --- | --- | --- | --- |
| `math` | `hypot`, `dist`, `atan2`, `cos`, `sin`, `exp`, `log2`, `sqrt`, `pi` | `geometry.py`, `path/*`, `pathlab/stats.py`, `testbench/report.py`, `extensions/paths.py` | distances, angles (overshoot direction), the logistic curve (`exp`), Fitts's law (`log2`), jitter gain (`sqrt`), the taper (`sin`) |
| `random` | `random.Random` (an instance), `uniform`, `gauss`, `random`, `choice`, `shuffle` | `path/bezier.py`, `curves.py`, `jitter.py`, `vision/base.py`, `input/win32_executor.py`, `extensions/paths.py`, `pathlab/lab.py`, tests | variety in movements. An *injected* `Random` (seeded in tests and the path lab) makes paths reproducible. Not for secrets: that's `secrets` (Ruff's S311 is marked "timing variety, not security" where it applies) |
| `statistics` | `mean`, `pstdev` | `pathlab/stats.py`, `tests/test_motion.py` | averages for the path lab; the jitter test checks the spread |

### Files, OS, processes

| Module | What we use | Where | Why |
| --- | --- | --- | --- |
| `pathlib` | `Path` | `gui/*`, `testbench/bench.py`, `plugins/screenshot_on_miss.py`, scripts, tests | paths as objects (`Path(__file__).parent / "page.html"`); `.stem` drops folders and the extension |
| `os` | `path.join`, `path.exists` | tests only | building temporary file paths in tests |
| `sys` | `argv`, `path`, `executable`, `platform`, `modules` | `main.py`, `tests/__init__.py`, scripts, tests | CLI arguments; put `src/` on the import path for tests; run tools with the same Python (`sys.executable`); skip Windows-only tests elsewhere |
| `ctypes` | `windll.user32` (`SendInput`, `GetCursorPos`, `GetSystemMetrics`, `SetProcessDpiAwarenessContext`), `Structure`, `Union`, `byref`, `sizeof`, `c_void_p`; `ctypes.wintypes` | `input/win32_executor.py` | calls Windows' C functions directly, so no extra dependency. `SendInput` is the documented way to synthesise input |
| `subprocess` | `run` with an argument *list* (never a shell) | `scripts/check.py`, `scripts/security_scan.py` | runs ruff, unittest, git and pip-audit. Lines carry `# security-scan: allow` with the reason |
| `shutil` | `which` | `scripts/security_scan.py` | the full path to `git`, not whatever is first on PATH |
| `tempfile` | `TemporaryDirectory` | tests | each test writes into its own folder, deleted afterwards |
| `importlib` | `import_module`; `importlib.metadata.entry_points`; `importlib.util.spec_from_file_location` | `plugins/manager.py`; `tests/test_security_scan.py` | load plugins by name or advertised entry point; load a script as a module in a test |
| `logging` | `getLogger("natural_mouse")` | `plugins/logging_plugin.py`, `examples/` | a named logger the application configures, instead of `print` |

### Text, data formats, network

| Module | What we use | Where | Why |
| --- | --- | --- | --- |
| `re` | `compile`, `search`, `sub`, `finditer` | `vision/color_locator.py` (`#rrggbb`), `plugins/screenshot_on_miss.py` (`safe_stem`), scripts | validate colours; strip unsafe characters from file names; scan for patterns and links |
| `json` | `loads`, `dumps`, `dump` | `gui/targets.py`, `extensions/paths.py`, `testbench/server.py`, tests | saved targets, recorded paths, the test bench's events. JSON can't run code (unlike `pickle`) |
| `ipaddress` | `ip_address`, `ip_network` | `scripts/security_scan.py` | "is this a real IP or a documentation one?" parsed properly, not by string matching |
| `http.server` | `ThreadingHTTPServer`, `BaseHTTPRequestHandler` | `testbench/server.py` | the test bench's tiny local web server |
| `http.client` | `HTTPConnection` | `tests/test_testbench_server.py` | send exact requests (wrong `Host`, oversized bodies) to the server |
| `urllib.parse` | `urlsplit`, `parse_qs` | `testbench/server.py` | read the path and the token from a request |
| `urllib.request`, `urllib.error` | `Request`, `urlopen`, `HTTPError`, `URLError` | `scripts/check_links.py`, `tests/test_testbench_bench.py` | check web links (http/https only); post events in the bench test |
| `hmac` | `compare_digest` | `testbench/server.py` | compares the token in constant time, so timing can't reveal how much of a guess was right |
| `secrets` | `token_urlsafe` | `testbench/server.py` | an unguessable token (unlike `random`) |
| `webbrowser` | `open` | `main.py`, `testbench/bench.py` | opens the test page in the default browser |

### Concurrency, time, UI, CLI, tests

| Module | What we use | Where | Why |
| --- | --- | --- | --- |
| `threading` | `Thread`, `Condition` | `testbench/server.py` | the server runs on its own thread; `Condition` lets the bench sleep until events arrive instead of polling |
| `concurrent.futures` | `ThreadPoolExecutor.map` | `scripts/check_links.py` | check 8 links at a time: link checks are mostly waiting |
| `time` | `sleep`, `monotonic`, `strftime` | `input/win32_executor.py`, `extensions/locators.py`, `plugins/*`, `testbench/*` | the delay between path points; timeouts that don't jump when the clock changes (`monotonic`) |
| `tkinter`, `tkinter.ttk` | the GUI's window, list, buttons, full-screen overlay | `gui/app.py`, `gui/capture_overlay.py` | ships with Python on Windows; enough for a small tool |
| `argparse` | `ArgumentParser`, subcommands | `main.py`, `examples/`, scripts | the CLI (`click`, `scroll`, `capture`, `testbench`, `pathlab`) |
| `unittest`, `unittest.mock` | `TestCase`, `skipUnless`, `patch` | `tests/` | built in; `patch` replaces `grab_screen`, `cv2.imwrite` and friends so tests never need a screen |

## 4. Built-in functions

| Built-in | Where, for what |
| --- | --- |
| `zip(..., strict=)` | pairs neighbours (`zip(pts, pts[1:], strict=False)`: one shorter *on purpose*) or equal-length lists (`strict=True`: a mismatch raises instead of silently dropping data) |
| `enumerate`, `range`, `len` | step loops in `bezier.py`, `jitter.py` |
| `min`, `max`, `sum`, `abs`, `round` | measurements (`pathlab/stats.py`), rounding a path point to a whole pixel for `SendInput` |
| `any`, `all` | "is there a smaller duplicate match?"; "is every easing step non-decreasing?" (tests) |
| `iter`, `next` | `plan`-style hand-out of values in order; `next(..., default)` to find the first match |
| `isinstance`, `getattr`, `hasattr` | the plugin manager (`getattr(plugin, hook)`) and type checks |
| `sorted` | ordering matches, files |
| `open`, `print` | saving recorded paths; CLI output |
| `super` | plugin and executor subclasses call the parent's `__init__` |
| `int`, `float`, `str`, `tuple`, `list`, `dict`, `set` | conversions; `tuple` inside frozen dataclasses (a list would be mutable) |

## 5. Dunder methods and attributes

| Dunder | Where | What it does |
| --- | --- | --- |
| `__init__` | most classes | the constructor |
| `__iter__` | `path/base.py` (`Path`), `plugins/manager.py` (`PluginManager`), `extensions/executors.py` (the fail-safe's path wrapper, which checks the mouse between points) | makes `for point in path:` work; the fail-safe hooks into that loop |
| `__len__` | `Path`, `PluginManager` | `len(path)` |
| `__add__` | `geometry.py` (`Point`) | `Point(1, 2) + Point(3, 4)` |
| `__enter__`, `__exit__` | `testbench/server.py` (`BenchServer`) | `with BenchServer(page) as url:` starts and always stops the server |
| `__file__` | scripts, `testbench/bench.py`, `tests/__init__.py` | find files next to the code (`page.html`, `src/`) |
| `__name__ == "__main__"` | `main.py`, scripts, tests | run code only when the file is executed, not imported |
| `__all__` | `natural_mouse/__init__.py` and sub-packages | the public names (`from natural_mouse import *`, and documentation of the API) |
| generated by `@dataclass` | every dataclass | `__init__`, `__repr__`, `__eq__`; with `frozen=True` also `__setattr__` that refuses changes, and `__hash__` |

## 6. Decorators

| Decorator | Where | Why |
| --- | --- | --- |
| `@dataclass` / `@dataclass(frozen=True)` | value objects (13 classes) | less boilerplate, immutability |
| `@abstractmethod` | the three strategy interfaces | a subclass must implement it |
| `@property` | `Path.end`, `Path.total_duration`, `Match.center`, `Planned.ready`-style flags, `BezierPathGenerator.profile` | a computed value that reads like an attribute |
| `@staticmethod` | helpers that need no `self` (`TemplateMatchLocator._load_template`, `Win32InputExecutor._split_into_steps`) | grouped with the class, callable without an instance |
| `@unittest.skipUnless` | `tests/test_win32_executor.py` | Windows-only test |

## 7. Language features worth knowing

| Feature | Where | Gotcha / why |
| --- | --- | --- |
| Relative imports (`from ..geometry import Point`) | inside `natural_mouse` | a package importing *itself by name* (`from natural_mouse import ...`) can see a half-loaded module; relative imports point at the exact file (used when mouse-ext was merged in) |
| Import cycles and `TYPE_CHECKING` | `geometry.py` | `geometry` needs `FittsLaw` only for a hint; importing it for real would loop back through `path/__init__.py` |
| Default arguments are evaluated once | `fake_executor.py` (`ORIGIN`), `pathlab/lab.py` (`DEFAULT_FITTS`) | `def f(x=Point(0, 0))` builds one object at definition time; fine only because `Point` is frozen. Named constants make that visible (Ruff B008) |
| Closures over loop variables | `testbench/*` callbacks | bind values as defaults (`lambda e=e: ...`) when a callback runs later |
| `with` / context managers | `BenchServer`, `TemporaryDirectory`, `mss.mss()` | cleanup happens even when something raises |
| Loading a file as a module | `tests/test_security_scan.py` | register it in `sys.modules` **before** `exec_module`, or `@dataclass` fails (found while writing that test) |
| f-strings with format specs | `pathlab/lab.py` (`{d:>11}`, `{x:.2f}`) | aligned tables without a library |
| Keyword-only intent via names | `MovementProfile(curve="cubic", ...)` | a dataclass with many fields is clearer called by name |

## 8. Development tools

| Tool | Command | What it does |
| --- | --- | --- |
| Ruff | `ruff check .` | lint with the rule sets in `ruff.toml`: pycodestyle (E, W), pyflakes (F), import order (I), bugbear (B), pyupgrade (UP), simplify (SIM), bandit security rules (S) |
| pip-audit | `python -m pip_audit` | checks installed packages against known-vulnerability databases |
| the gate | `python scripts/check.py [--offline]` | lint, tests, links, security in one command; exit code 0 = all passed |

Install them with `pip install -e ".[dev]"` (`-e` = editable, `.[dev]` =
this project plus its `dev` extra).

## 9. Exercises

1. Replace `statistics.mean` in `pathlab/stats.py` with `sum(...)/len(...)`.
   What edge case does `statistics` handle that you now must?
2. Why does the test bench use `secrets.token_urlsafe` and not
   `random.choice` for its token? Write one sentence.
3. Find every `zip(..., strict=False)`. For each, explain why the
   shorter result is intended.

**Self-check:** which standard-library module would you reach for to
call a Windows function that has no Python wrapper?

## References

**Official**

- Python standard library: [index](https://docs.python.org/3/library/index.html); [`ctypes`](https://docs.python.org/3/library/ctypes.html); [`dataclasses`](https://docs.python.org/3/library/dataclasses.html); [`abc`](https://docs.python.org/3/library/abc.html); [`random`](https://docs.python.org/3/library/random.html); [`secrets`](https://docs.python.org/3/library/secrets.html); [`hmac.compare_digest`](https://docs.python.org/3/library/hmac.html#hmac.compare_digest); [`importlib`](https://docs.python.org/3/library/importlib.html); [`zip`](https://docs.python.org/3/library/functions.html#zip)
- PEP 563 ([postponed annotations](https://peps.python.org/pep-0563/)), PEP 618 ([`zip(strict=)`](https://peps.python.org/pep-0618/))
- [OpenCV docs](https://docs.opencv.org/4.x/), [NumPy docs](https://numpy.org/doc/stable/), [mss docs](https://python-mss.readthedocs.io/)
- Microsoft Learn, [`SendInput`](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)
- [Ruff rules](https://docs.astral.sh/ruff/rules/), [pip-audit](https://pypi.org/project/pip-audit/)

**Other explanations**

- Real Python, [Python's `ctypes`](https://realpython.com/python-bindings-overview/) (bindings overview)

### Further learning

- [Exercism Python track](https://exercism.org/tracks/python)
