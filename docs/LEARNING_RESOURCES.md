# Learning Resources

A study guide tied directly to this codebase: every concept below is
something actually used in `natural_mouse`, with the exact file to go
look at, plus outside resources to go deeper. Suggested order: read top
to bottom once, then go back and actually open the referenced files side
by side with the linked articles/videos.

Once you're through this, see [PROGRAMMING_ROADMAP.md](PROGRAMMING_ROADMAP.md)
for the broader map of general, Python-specific, and other-language
concepts worth knowing beyond what this particular project happens to
use.

## 1. Project & folder structure

**What we did:** a `src`-less flat layout — the package (`natural_mouse/`)
sits next to its entry points (`main.py`, `gui/`) and its tests
(`tests/`), all at the repo root. Subpackages (`path/`, `input/`,
`vision/`) each group one concern and each has an `__init__.py` that
re-exports the public names, so callers write
`from natural_mouse.path import BezierPathGenerator` instead of reaching
into `natural_mouse.path.bezier`.

**Why it matters:** how you lay out folders is the first thing anyone
(including future-you) sees, and it silently communicates "here's how
this system is divided." A folder per responsibility (not per file type)
is the convention almost every serious Python project converges on.

- [Python Packaging User Guide — Packaging Python Projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/) — the official reference for how a Python project is structured.
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) — covers file/module layout conventions in section 3, alongside naming (see §5 below).

## 2. OOP principles applied

Go read `ARCHITECTURE.md` in this repo first — it walks through
Dependency Inversion, the Strategy pattern, Single Responsibility,
Encapsulation, the Composition Root, and value-object immutability, each
tied to a specific file in this project. This section is the external
reading to go with it.

**Abstraction / Encapsulation / Inheritance / Polymorphism**, the four
pillars, all show up together in `natural_mouse/input/`: `InputExecutor`
(`base.py`) is the abstraction, `Win32InputExecutor` and
`FakeInputExecutor` inherit from it, each encapsulates its own private
implementation details (`ctypes` structs vs. a plain call-recording list),
and `UIAutomator` uses either one polymorphically — it calls
`executor.click(...)` without knowing or caring which subclass it's
holding.

- [Real Python — Object-Oriented Programming (OOP) in Python 3](https://realpython.com/python3-object-oriented-programming/) — the four pillars, explained with Python examples.
- [Corey Schafer — Python OOP Tutorials playlist](https://www.youtube.com/playlist?list=PL-osiE80TeTsqhIuOqKhwlXsIBIdSeYtc) — classes, inheritance, dunder methods, property decorators, all in short focused videos.

**SOLID**, specifically:

- **S**ingle Responsibility — every file in this project answers exactly one question (see the table in `ARCHITECTURE.md` Part 1).
- **O**pen/Closed — `ScreenLocator`/`InputExecutor`/`PathGenerator` are open to new implementations (add a new file) but closed to modification (never edit the ABC to add a new strategy).
- **L**iskov Substitution — `Win32InputExecutor` and `FakeInputExecutor` are fully interchangeable anywhere an `InputExecutor` is expected; neither breaks an assumption the other relies on.
- **I**nterface Segregation — three small, focused ABCs instead of one giant "Automatable" interface.
- **D**ependency Inversion — covered above; `UIAutomator` depends on abstractions, never concretions.

- [Uncle Bob's SOLID Principles Made Easy — In Python! (ArjanCodes)](https://www.youtube.com/watch?v=pTB30aXS77U) — all five, in Python, roughly 45 minutes.
- [ArjanCodes — SOLID Design Principles with Python (playlist)](https://www.youtube.com/playlist?list=PLyLkn_nipSjNVOpdOG-nETxKfgEpbubMQ) — one video per letter, more depth than the single-video version above.
- [Wikipedia — SOLID](https://en.wikipedia.org/wiki/SOLID) — quick reference once you've watched the videos, for when you just need to recall a definition.

## 3. Design patterns

**Strategy pattern** — `PathGenerator`, `InputExecutor`, `ScreenLocator`
are all textbook Strategy: a family of interchangeable algorithms behind
one interface, chosen by whoever composes the object (`main.py`/`gui/app.py`).

- [Refactoring.Guru — Strategy Pattern (Python example)](https://refactoring.guru/design-patterns/strategy/python/example) — the clearest visual explanation of this pattern, with a Python code example structured almost identically to this project's `path/`/`input/`/`vision/` split.
- [ArjanCodes — How to Implement the Strategy Design Pattern in Python](https://www.youtube.com/watch?v=n2b_Cxh20Fw)

**Dependency Injection / Composition Root** — `UIAutomator.__init__`
receiving its three collaborators as constructor arguments (instead of
constructing them itself) is Dependency Injection; `main.py`'s
`build_automator()` and `gui/app.py`'s `App.__init__` being the *only*
places that instantiate concrete classes is the Composition Root pattern.

- [Martin Fowler — Inversion of Control Containers and the Dependency Injection pattern](https://www.martinfowler.com/articles/injection.html) — the original, canonical article that named this pattern (2004, still entirely relevant).
- [ArjanCodes — Dependency Injection Explained in 7 Minutes](https://www.youtube.com/watch?v=DpMGEhwuuyA) — fast, practical, Python-specific.
- [ArjanCodes — Best Practices for Python Dependency Injection](https://arjancodes.com/blog/python-dependency-injection-best-practices/) — the article version, good for re-reading later.

**Value Objects** — `Point`, `PathPoint`, `Match` are all
`@dataclass(frozen=True)`: immutable data holders with no identity beyond
their values. This is a small but genuinely useful pattern to internalize
— bugs from accidental mutation of shared state are eliminated by
construction, not by discipline.

- [Python docs — dataclasses](https://docs.python.org/3/library/dataclasses.html) — official reference, including the `frozen=True` option used throughout this project.

## 4. Type hints

**What we did:** every function signature in this project is fully typed
(`def generate(self, start: Point, end: Point) -> Path:`), every file
starts with `from __future__ import annotations` (lets modern union
syntax like `Point | None` work even though we target older Python
runtimes in principle), and `Optional` values are always written as
`X | None`, never left implicit.

**Why it matters:** type hints don't change how the code runs — Python
ignores them at runtime — but they let your editor catch mistakes before
you run anything, and they document what a function expects/returns
without needing a comment to say so.

- [Python docs — the `typing` module](https://docs.python.org/3/library/typing.html) — official reference.
- [Real Python — Python Type Checking (Guide)](https://realpython.com/python-type-checking/) — the best single guide; covers the syntax, `mypy`, and when type hints actually catch real bugs.
- [mypy documentation](https://mypy.readthedocs.io/) — the static type checker that actually enforces these hints. This project doesn't run mypy in CI, but it's worth installing and pointing it at `natural_mouse/` yourself as an exercise — see what it flags.

## 5. Naming conventions

- `snake_case` for functions/variables/modules, `PascalCase` for classes — standard PEP 8, applied consistently (`BezierPathGenerator`, `move_to`, `path_generator`).
- A single leading underscore (`self._locator`, `_send_wheel`) signals "internal, don't touch from outside this class/module" — a convention, not an enforced restriction, which is a deliberate Python design choice ("we're all consenting adults here").
- Abstract base classes are named for *what they are*, not suffixed with "Abstract" or "Interface" (`InputExecutor`, not `IInputExecutor` or `AbstractInputExecutor`) — this matches Python community convention (unlike, say, Java or C#, where an `I` prefix is idiomatic).
- Test doubles are named for *what they do*: `FakeInputExecutor` records calls and fakes state; it's deliberately not called `MockInputExecutor`, because a "mock" (in the strict testing-vocabulary sense) verifies that specific calls happened, while a "fake" is a real, simplified working implementation. See the testing section below for why this distinction is worth knowing.

- [PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/) — the foundational document; almost every Python style convention traces back to this.
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) — more opinionated and detailed than PEP 8, good second read.

## 6. Testing principles

**What we did:** `tests/test_bezier.py` tests pure logic directly — no
mocking needed, because `BezierPathGenerator` does no I/O.
`tests/test_automator.py` tests orchestration logic using a **fake**
(`FakeInputExecutor`, a real simplified stand-in that records calls) and
an inline fake `ScreenLocator`, instead of a mocking framework.

**Why fakes instead of `unittest.mock`:** a mock library lets you assert
"was `.click()` called with these exact arguments?" without a real
working implementation behind it. A fake is a genuine (if simplified)
implementation of the interface — `FakeInputExecutor` actually tracks a
position and actually appends to a list. Fakes tend to produce more
robust tests for this kind of orchestration code because they behave
consistently across multiple calls, the way the real thing would,
whereas a pile of mock assertions can pass even when the overall
behavior would be nonsensical.

- [Martin Fowler — TestDouble](https://martinfowler.com/bliki/TestDouble.html) — defines the vocabulary (dummy, fake, stub, spy, mock) this project's naming follows.
- [Martin Fowler — Mocks Aren't Stubs](https://martinfowler.com/articles/mocksArentStubs.html) — the deeper argument for when to prefer fakes/state-based testing over mock-heavy interaction testing; directly explains the reasoning behind this project's testing style.
- [Python docs — unittest](https://docs.python.org/3/library/unittest.html) — the standard library test framework used throughout `tests/`. This project deliberately uses only the standard library here (no `pytest`), to keep the dependency list minimal.

## 7. Why these specific libraries were chosen

Every dependency declared in `pyproject.toml` was picked for a specific
reason, not just "it's popular":

- **`opencv-python`** — does the actual template matching (`cv2.matchTemplate`). Chosen because it's the standard, battle-tested tool for this exact operation; hand-rolling image correlation would be reinventing a wheel that's been optimized for decades.
  - [OpenCV — Template Matching tutorial](https://docs.opencv.org/4.13.0/d4/dc6/tutorial_py_template_matching.html) — official tutorial, matches exactly what `TemplateMatchLocator` does.
- **`mss`** — takes the actual screenshots. Chosen over alternatives (like `pyautogui`'s built-in screenshot, or `PIL.ImageGrab`) specifically for speed — `mss` is built for fast, repeated full-screen capture, which matters since matching happens against a fresh screenshot every single call.
  - [python-mss documentation](https://python-mss.readthedocs.io/)
- **`ctypes` + the Win32 `SendInput` API** (standard library, no install needed) — used directly in `win32_executor.py` instead of a higher-level automation library like `pyautogui`, specifically so the exact path-following behavior (every intermediate point, precisely timed) is fully controlled rather than relying on a library's built-in (and usually much simpler/instant) mouse-move function.
  - [Python docs — ctypes](https://docs.python.org/3/library/ctypes.html) — the standard library's foreign-function interface, used here to call raw Win32 API functions.
- **`tkinter`** (standard library) — the GUI toolkit. Chosen specifically because it ships with Python — zero extra dependencies, which mattered once "this might run on a lightweight cloud VPS" entered the picture. A framework like PyQt would look nicer but adds real weight for no functional benefit here.
  - [Python docs — tkinter](https://docs.python.org/3/library/tkinter.html)
- **`argparse`** (standard library) — the CLI parser in `main.py`. Standard library, well documented, does everything a simple subcommand-based CLI needs without pulling in `click` or `typer`.
  - [Python docs — argparse](https://docs.python.org/3/library/argparse.html)
- **`abc` + `dataclasses`** (standard library) — `abc.ABC`/`@abstractmethod` enforce that a subclass actually implements every required method (Python raises `TypeError` at instantiation if it doesn't); `dataclasses` removes the boilerplate of writing `__init__`/`__eq__`/`__repr__` by hand for simple value-holding classes like `Point` and `Match`.
  - [Python docs — abc](https://docs.python.org/3/library/abc.html)
  - [Python docs — dataclasses](https://docs.python.org/3/library/dataclasses.html)

## 8. The `greenlet.h` question

This one has a specific, concrete answer tied to this project's actual
history, not just a generic explanation.

**What greenlet is:** a library that implements lightweight, cooperative
"micro-threads" (coroutines) at the C level, letting code switch between
different execution contexts without the OS's real thread scheduler being
involved. It's most commonly seen as the mechanism underneath other
libraries — `gevent`, `eventlet`, and (relevant here) **Playwright's
Python `sync_api`**, which uses greenlet internally to let you write
blocking-looking code (`page.click(...)`, no `await`) while the real
implementation underneath is asynchronous.

**Why it was in this project's `venv`:** during an earlier exploration in
this project's history, `playwright` was installed while investigating
whether a browser-DOM-based element locator would be more reliable than
pixel matching for one specific case (that direction was ultimately not
pursued — see the project's conversation history / commit log around
that decision). Installing `playwright` pulled in `greenlet` as a
transitive dependency, which is why `greenlet.h` (its C extension header)
ended up under `venv/Include/site/python3.14/greenlet/`. **`natural_mouse`
itself never imported or used greenlet or playwright** — it was inert,
leftover install baggage, and has since been removed (`pip uninstall
playwright greenlet pyee`) as part of a cleanup pass. It's documented here
anyway because the question ("what is this and why is it here") is a
useful, concrete example even after the answer became "it isn't, anymore."

**The broader lesson:** this is a good real example of why checking
`pip list` / your dependency tree periodically matters — dependencies
brought in for an experiment that didn't pan out can silently linger.

- [greenlet documentation](https://greenlet.readthedocs.io/) — what it actually does, at the API level.
- [Playwright Python — Installation/intro docs](https://playwright.dev/python/docs/intro) — for context on where greenlet was actually being used.

**On `.h` files and C extensions generally**, since this touches a
different language than the rest of this project: a `.h` file is a C
"header" — it declares the interface (function signatures, struct
layouts) that other C code compiles against, without containing the full
implementation. Many Python packages that need raw speed or low-level
system access (like `greenlet`, or parts of `numpy`) are written partly
in C and compiled into a binary extension; the `.h` files are part of
that C source, present because `pip` installed the package in a form that
includes its C sources/headers (common for packages that may need to
compile against your specific Python version).

- [Python docs — Extending Python with C or C++](https://docs.python.org/3/extending/extending.html) — official guide to how/why Python packages include C code.

## 9. Concurrency concepts (via the greenlet detour)

Since §8 already led here through greenlet, it's worth actually naming
these four distinctions explicitly — they're commonly confused, and this
project happens to touch real examples of most of them.

**Concurrent vs. parallel execution.** Concurrency is about *structure*:
dealing with multiple tasks whose progress overlaps in time, whether or
not anything is literally happening at the same instant. Parallelism is
about *execution*: things genuinely computing at the same instant, which
requires multiple CPU cores. A single-core machine can be concurrent
(rapidly switching between tasks) but never truly parallel. Rob Pike's
famous framing: concurrency is about *dealing with* lots of things at
once; parallelism is about *doing* lots of things at once.

**Where this project sits:** `natural_mouse` is neither concurrent nor
parallel — every call is synchronous and sequential (locate, *then* move,
*then* click, one step fully finishing before the next starts). That's a
deliberate choice, not an oversight: a "manual tool" that does exactly
one thing per user action has no task that needs to overlap with another,
so reaching for concurrency here would add real complexity for zero
benefit. Recognizing when concurrency *isn't* worth the complexity is as
important as knowing how to use it.

**Cooperative vs. preemptive multitasking.** Preemptive: the OS forcibly
interrupts a running thread on a timer and hands control to another,
whether that thread is "ready" for it or not — this is how real OS
threads and processes are scheduled. Cooperative: a task must *choose* to
give up control (an explicit `await`, an explicit greenlet switch, a
`yield`) — nothing else gets to run until it does, which means one
badly-behaved task can freeze everything else. **Greenlet is explicitly
cooperative** — Playwright's `sync_api` switches between its hidden event
loop and your calling code only at specific, defined points, never by
surprise.

**CPU-bound vs. I/O-bound tasks.** CPU-bound: the bottleneck is actual
computation — the CPU is genuinely busy. I/O-bound: the bottleneck is
*waiting* — for a network response, a disk read, or (a less obvious case)
just for time to pass. Both concretely exist in this codebase:
`TemplateMatchLocator.locate()`'s call to `cv2.matchTemplate` is
CPU-bound — it's real pixel-comparison work. Every `time.sleep(delay)`
inside `Win32InputExecutor.move_to()` (following the path
`BezierPathGenerator` generated) is I/O-bound-*like* — the CPU sits
completely idle, deliberately waiting so the movement reads as
human-paced. This distinction has a practical payoff: if this tool ever
felt sluggish, profiling would tell you *which* half to look at — a slow
`matchTemplate` call means optimizing computation (smaller search region,
different algorithm), while the sleeps are intentional and "optimizing"
them away would defeat the entire point of natural movement.

**Thread-based vs. event-based concurrency.** Thread-based: multiple
independent flows of control, each with its own call stack; something
(the OS, or a cooperative scheduler like greenlet) switches between them.
Event-based (an "event loop," as in `asyncio`): a *single* flow of
control that repeatedly asks "what's ready to make progress?" and
dispatches to it — no extra stacks at all. Playwright's `sync_api` is a
genuinely interesting hybrid to study once both models click
individually: its real engine is event-loop-based (`asyncio`), but
greenlet is layered on top specifically to make calling code *feel*
like it's making an ordinary blocking, thread-style call.

- [Real Python — Speed Up Your Python Program With Concurrency](https://realpython.com/python-concurrency/) — covers threading vs. asyncio vs. multiprocessing, and CPU-bound vs. I/O-bound, in one place with runnable examples.
- [Rob Pike — "Concurrency Is Not Parallelism" (via the official Go blog)](https://go.dev/blog/waza-talk) — the talk that popularized this exact distinction; links to both the slides and the video.
- [GeeksforGeeks — Difference between Preemptive and Cooperative Multitasking](https://www.geeksforgeeks.org/operating-systems/difference-between-preemptive-and-cooperative-multitasking/)
- [Python docs — asyncio](https://docs.python.org/3/library/asyncio.html) — the standard library's event-loop-based concurrency model, for seeing the event-based side directly (this project doesn't use it, but Playwright's sync API — mentioned in §8 — is built on it underneath).
- [AsyncIO vs Threading vs Multiprocessing in Python — YouTube](https://www.youtube.com/watch?v=QlkXji08lno)
- [Asyncio Finally Explained: What the Event Loop Really Does — YouTube](https://www.youtube.com/watch?v=RIVcqT2OGPA)

## 10. Git & commit conventions

Commit messages in this repo follow a consistent shape: a short present-tense
summary line, a blank line, then a body explaining *why* the change was
made (not just what changed — the diff already shows what changed).

- [Conventional Commits specification](https://www.conventionalcommits.org/en/v1.0.0/) — a stricter, more formal version of the same idea (this repo doesn't follow the `feat:`/`fix:` prefix convention exactly, but the underlying philosophy — structured, meaningful commit messages — is the same).

## 11. Suggested study order

1. Read `ARCHITECTURE.md` fully once, without jumping to the linked code yet.
2. Open `natural_mouse/path/base.py` and `natural_mouse/path/bezier.py` side by side — smallest, most self-contained example of Abstraction + Strategy in this repo.
3. Watch the ArjanCodes SOLID video (§2), then reread the `automator.py` file — it should read differently once Dependency Inversion has a name attached to it.
4. Read `tests/test_automator.py` and the Martin Fowler TestDouble article (§6) together — see how `FakeInputExecutor` maps onto the vocabulary.
5. Read §8 (`greenlet.h`) and §9 (concurrency concepts) back to back — the greenlet explanation is the motivating example, the concepts section is the vocabulary to describe what it's doing.
6. Try the "extension exercises" at the bottom of `ARCHITECTURE.md` — actually write a `LinearPathGenerator` yourself before looking at how `BezierPathGenerator` does it differently.
7. **The movement model**: read `MOVEMENT.md` §2-§6 with `path/curves.py`, `easing.py`, `jitter.py`, `fitts.py` open (each is under 100 lines of pure maths), then run `python src/main.py pathlab` and change one `VARIANTS` entry. Self-check: explain why tremor smoothing lowered "wobble" from 1.16 to 0.49 px.
8. **One movement end to end**: follow `MOVEMENT.md` §9 from `automator.py` into `win32_executor.py`'s `SendInput` calls.
9. **Extensions and plugins**: `EXTENSIONS_LEARNING.md` has its own study order.
10. **Safety**: read `SECURITY.md`, then `tests/test_security_scan.py`: see how each check is proven by planting a bad line.

## 12. Books worth owning eventually (no rush)

Not linked (avoiding pointing you at a specific retailer), but worth
knowing the titles/authors to look for:

- **"Clean Code"** — Robert C. Martin. The most common answer to "one book on naming, functions, and readability."
- **"Refactoring: Improving the Design of Existing Code"** — Martin Fowler. The book behind refactoring.guru's content; goes deeper into *when* and *how* to restructure working code.
- **"Design Patterns: Elements of Reusable Object-Oriented Software"** — Gamma, Helm, Johnson, Vlissides (the "Gang of Four"). The original catalog Strategy/Composition Root-adjacent patterns trace back to; dense, but the primary source.
