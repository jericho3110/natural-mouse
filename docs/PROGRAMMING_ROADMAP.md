# Programming Roadmap: Beyond This Project

`LEARNING_RESOURCES.md` ties concepts to specific files in this
repository. This document is broader — it's the map of what else
separates a solid programmer from a genuinely excellent one, organized
into three scopes: ideas that apply regardless of language, ideas that
are specifically about Python, and ideas best understood by looking at
*other* languages (several of which this project actually brushed up
against). Where something connects back to `natural_mouse`, that's
called out explicitly; the rest is just important to know.

---

## Part 1: General, language-agnostic concepts

### 1.1 Data structures & algorithmic thinking

The foundation under everything else: arrays, linked lists, hash
maps/sets, stacks/queues, trees, graphs, and heaps — what each is good
at, and what it's bad at. On top of that, a handful of recurring
*patterns* solve a huge fraction of real problems: two pointers, sliding
window, binary search, breadth/depth-first search, recursion, and dynamic
programming. Alongside the structures themselves, **Big-O notation** — the
language for describing how an algorithm's time/memory cost grows as
input grows — is what lets you reason about "will this still work when
the input is 1000x bigger" before you find out the hard way in
production.

- [Big-O Cheat Sheet](https://www.bigocheatsheet.com/) — complexity of common data structures and algorithms, one page.
- [NeetCode — Big-O Notation cheatsheet](https://neetcode.io/cheatsheets/big-o-notation)
- [NeetCode (YouTube channel)](https://www.youtube.com/@NeetCode) — the standard recommendation for learning these patterns by working through real problems rather than reading theory alone.

### 1.2 Debugging & problem-solving methodology

`ARCHITECTURE.md` (Part 3, in this repo) walks through a real debugging
session — the scroll bug — as a worked example: trace the actual call
chain rather than guess, compare the broken path against a working one to
spot the asymmetry, confirm the underlying mechanism before trusting a
fix, fix at the right layer, add a regression test, then verify the
*visible* effect rather than trusting a clean exit code. That's the whole
methodology in miniature. Two more tools worth having explicitly: **binary
search debugging** (if a bug appeared somewhere across 50 commits, don't
inspect all 50 — bisect: check the middle one, narrow by half each time —
`git bisect` automates exactly this), and **rubber duck debugging**
(explaining the problem out loud, line by line, to *anyone or anything*,
surfaces the wrong assumption far more often than staring at the code
silently).

### 1.3 Software architecture patterns

This project is, without it being named at the time, a small example of
**hexagonal architecture** (also called "ports and adapters"): a core
(`natural_mouse`) that knows nothing about how it's driven, and two
separate "adapters" (`main.py`'s CLI, `gui/app.py`'s Tkinter window) that
each translate a different kind of human input into calls against that
same core. The core has zero knowledge that either adapter exists.

That's one answer to a question every larger system has to answer somehow:
*how do you stop the "core" of a system from becoming tangled up with the
details of how it's used or what it talks to, and why does that question
get more urgent as a project grows?* See
**[SOFTWARE_ARCHITECTURE_STYLES.md](SOFTWARE_ARCHITECTURE_STYLES.md)**
for the full tour — monoliths, layered architecture, MVC/MVP/MVVM,
hexagonal and Clean Architecture, event-driven architecture,
microservices, serverless, and monorepo vs. polyrepo, each with when it
earns its cost and where it tends to hurt.

### 1.4 Databases & data modeling

Not touched by this project (there's no database here), but foundational
elsewhere: **normalization** (structuring tables so each fact lives in
exactly one place, avoiding update anomalies), **ACID** transactions
(Atomicity, Consistency, Isolation, Durability — the guarantees that make
a transaction either fully happen or not happen at all, even if the
system crashes mid-way), **indexing** (why some queries are instant and
others crawl), and the general **SQL vs. NoSQL** tradeoff (strong
consistency and relational integrity vs. horizontal scalability and
schema flexibility).

- [GeeksforGeeks — ACID Properties in DBMS](https://www.geeksforgeeks.org/dbms/acid-properties-in-dbms/)
- [Use The Index, Luke!](https://use-the-index-luke.com/) — the best free resource specifically on how indexes actually work and why queries are slow without them.

### 1.5 Networking & web fundamentals

HTTP request/response, status codes, REST conventions, the rough
difference between TCP (reliable, ordered) and UDP (fast, no guarantees),
and what DNS actually does (translates a name to an address) are baseline
knowledge for almost anything that talks over a network — including, for
what it's worth, `llama-server`'s OpenAI-compatible `/v1` API from the
local-LLM detour earlier in this project's history, which is just HTTP
underneath.

- [MDN — Overview of HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview)

### 1.6 Security fundamentals

The **OWASP Top 10** is the standard reference for the most common ways
real applications get broken into (injection, broken authentication,
security misconfiguration, etc.) — worth reading start to finish at least
once, even outside web development, because the underlying lessons
(never trust input, validate at the boundary, least privilege, don't roll
your own crypto) generalize everywhere. Two specific distinctions worth
knowing cold: **authentication vs. authorization** ("who are you" vs.
"what are you allowed to do," two different problems, often conflated),
and **input validation at the boundary** (validate/sanitize the moment
data enters your system, not scattered ad hoc throughout).

- [OWASP Top 10](https://owasp.org/Top10/2021/)

### 1.7 Distributed systems & scalability

Once a system spans more than one machine, new problems appear that don't
exist on a single process: the **CAP theorem** (a distributed system
facing a network partition must choose between Consistency and
Availability — it cannot have both simultaneously), **idempotency**
(designing an operation so running it twice has the same effect as
running it once — critical when retries are possible over an unreliable
network), caching strategies, and load balancing. This is a big field;
the goal at this stage is recognizing the vocabulary, not mastering it.

- [IBM — What Is the CAP Theorem?](https://www.ibm.com/think/topics/cap-theorem)
- [system-design-primer (GitHub)](https://github.com/donnemartin/system-design-primer) — the most widely used free resource for this entire topic area.

### 1.8 Version control mastery

Beyond `git add`/`commit`/`push`: branching strategies (feature branches,
trunk-based development), the actual difference between **rebase**
(rewrites history to look linear) and **merge** (preserves history,
creates a merge commit), `git bisect` (mentioned in §1.2), and writing
commit messages that explain *why*, not just *what* — which this
project's own commit history (check `git log` in this repo) tries to
model throughout.

- [Pro Git (free online book)](https://git-scm.com/book/en/v2)

---

## Part 2: Python-specific concepts

### 2.1 The GIL

Already covered in `LEARNING_RESOURCES.md` §9, but worth restating here
as a Python-specific fact: CPython's Global Interpreter Lock means only
one thread executes Python bytecode at a time, ever, in a single process
— which is *why* CPU-bound work needs `multiprocessing` (separate
processes, each with its own GIL) to actually use multiple cores, while
I/O-bound work can get real concurrency benefit from `threading` or
`asyncio` despite the GIL, since those threads/tasks spend most of their
time waiting, not computing.

### 2.2 Generators, iterators, and `yield`

This project's `Path` class (`natural_mouse/path/base.py`) implements
`__iter__`, making it directly iterable (`for point in path:`) without
ever building a second copy of the data for iteration purposes. A
**generator** (a function using `yield` instead of `return`) takes this
further: it produces values one at a time, on demand, without ever
holding the whole sequence in memory at once. If `BezierPathGenerator`
ever needed to support extremely long paths, rewriting `generate()` as a
generator (yielding each `PathPoint` as it's computed, instead of
building the full list first) would be the natural next step — worth
trying as an exercise.

- [Python docs — Generators (in the tutorial)](https://docs.python.org/3/howto/functional.html#generators)

### 2.3 Context managers (`with`)

Used directly in this project: `natural_mouse/screen.py` opens the
screen-capture resource with `with mss.mss() as sct:` — the `with`
statement guarantees `sct` gets cleaned up (via its `__exit__` method)
even if an exception happens inside the block. This is Python's answer to
"how do I guarantee cleanup happens" without a `finally` block everywhere.
Writing your own context manager (either a class with
`__enter__`/`__exit__`, or a generator function decorated with
`@contextlib.contextmanager`) is a good, small exercise.

- [Python docs — `contextlib`](https://docs.python.org/3/library/contextlib.html)

### 2.4 Decorators

`natural_mouse/path/bezier.py` uses `@staticmethod` (a method that
doesn't need `self`, grouped into the class purely for namespacing —
`BezierPathGenerator._quadratic_bezier` is math that doesn't depend on any
instance state). `@property` (turning a method into something accessed
like an attribute — see `Path.end` and `Path.total_duration`) is the other
decorator used throughout this project. Writing a *custom* decorator
(a function that wraps another function, commonly for logging, timing, or
retry logic) is the next level up — a genuinely core Python skill once
you're past the basics.

- [Real Python — Primer on Python Decorators](https://realpython.com/primer-on-python-decorators/)

### 2.5 Dunder methods & the data model

`Path.__iter__` and `Path.__len__` (in `natural_mouse/path/base.py`) are
"dunder" (double-underscore) methods — they're how a class plugs into
Python's built-in syntax (`for x in path`, `len(path)`) instead of
requiring a custom method name. Every `@dataclass` in this project
(`Point`, `Match`, `PathPoint`) gets `__init__`, `__eq__`, and `__repr__`
generated automatically — which *is* the data model in action, just
handed to you for free. Understanding this model is what makes "why does
`==` work on my dataclass but not on my plain class" click.

- [Python docs — Data Model](https://docs.python.org/3/reference/datamodel.html) — the official, dense, but authoritative reference.

### 2.6 Duck typing vs. explicit interfaces

Python is dynamically typed — if an object has the methods you call on
it, Python doesn't care what class it actually is ("if it walks like a
duck and quacks like a duck..."). This project deliberately chose *not*
to rely purely on duck typing for its core abstractions — `PathGenerator`,
`InputExecutor`, and `ScreenLocator` are `abc.ABC` subclasses with
`@abstractmethod`, which means Python will refuse to even instantiate a
subclass that doesn't implement every required method. That's a
deliberate tradeoff: duck typing is more flexible, but an explicit `ABC`
contract catches "forgot to implement a method" at the moment a class is
defined, not the first time it's actually used and something's missing.

- [Python docs — `abc` module](https://docs.python.org/3/library/abc.html)

### 2.7 EAFP vs. LBYL

Two philosophies for handling things that might fail: **LBYL** ("Look
Before You Leap" — check a condition first, e.g. `if key in dict:` before
accessing it) vs. **EAFP** ("Easier to Ask Forgiveness than Permission" —
just try the operation and catch the exception if it fails). Python
culture leans EAFP; this project's `main.py` (`try: amount =
int(...)` / `except ValueError:` pattern in the GUI's scroll handler)
follows that convention rather than pre-checking whether a string looks
numeric.

- [Python glossary — EAFP](https://docs.python.org/3/glossary.html#term-EAFP)

### 2.8 Comprehensions

List/dict/set comprehensions (`[x for x in items if condition]`) are
Python's concise syntax for the "filter and transform a collection"
pattern that appears constantly. This project doesn't lean on them
heavily (the code style here favors explicit loops where a step needs a
comment-worthy explanation, like the jitter/easing loop in
`bezier.py`), which is itself worth noticing: comprehensions are great for
simple transforms, but a plain `for` loop is often more readable the
moment the logic inside it needs more than one line to explain.

### 2.9 Packaging & environments

This project started with the simplest possible setup — a `venv` plus a
flat `requirements.txt` — deliberately, while the only requirement was
"install three dependencies." That stopped being enough the moment a
*real* need showed up: being able to `import natural_mouse` from a
completely separate script/project, not just from inside this repo. A
plain `requirements.txt` only installs dependencies; it doesn't make the
project itself an importable package. The fix was `pyproject.toml` (the
modern standard project-metadata file) plus `pip install -e .` — an
"editable" install that registers `natural_mouse` as a real package
pointing at the live source, importable from anywhere using that venv's
Python, with edits to the source taking effect immediately. Larger or
more actively-developed projects often go further still, pairing
`pyproject.toml` with a tool like Poetry or `uv` for full dependency
*locking* (pinning exact versions, including transitive dependencies, so
"works on my machine" problems don't happen) — this project didn't need
that yet, since the dependency list is still short and stable; only the
"is it importable elsewhere" problem was real, so only that problem got
solved. Worth noticing as a general pattern: add the heavier tool when a
concrete need shows up, not preemptively because it's "more proper."

- [Python Packaging User Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [pip documentation — Local project installs (editable installs)](https://pip.pypa.io/en/stable/topics/local-project-installs/)

---

## Part 3: Other languages & different paradigms

### 3.1 C, and what changes when you cross into it

`natural_mouse/input/win32_executor.py` calls straight into the Win32 C
API via `ctypes` — `_MOUSEINPUT`/`_INPUT` are hand-written mirrors of C
`struct`s, and `SendInput` is a real C function from `user32.dll` being
called directly from Python. This is a genuinely good doorway into
systems programming concepts: C has **manual memory management** (no
garbage collector — you allocate and free explicitly, and getting it
wrong causes leaks or crashes, not just slowness), fixed-size numeric
types (`DWORD` is exactly 32 bits, always — which is *why* this project
had to manually bit-mask a negative Python integer to fit into an
unsigned 32-bit field for the scroll-wheel event), and no built-in
concept of "safe" — an out-of-bounds access can corrupt memory instead of
raising a clean exception.

- [Python docs — Extending Python with C or C++](https://docs.python.org/3/extending/extending.html)
- [Python docs — `ctypes`](https://docs.python.org/3/library/ctypes.html)

### 3.2 Memory management models, compared

Worth seeing side by side, since this project touches two of them
directly (Python's, and — through `ctypes` — C's):

- **Manual (C, C++)** — you call `malloc`/`free` yourself. Maximum control, maximum ability to get it wrong.
- **Garbage-collected (Python, Java, Go)** — the runtime tracks references and frees memory automatically once nothing points to it anymore. Simpler, at the cost of some unpredictability in *when* cleanup happens and some runtime overhead.
- **Ownership-based (Rust)** — the compiler tracks, at compile time, exactly one "owner" for each piece of data and enforces (via compiler errors, not runtime checks) that memory is freed exactly once, with no garbage collector needed at all. This is Rust's signature idea and worth understanding conceptually even without writing Rust.

- [The Rust Programming Language (the official book) — Ch. 4, Understanding Ownership](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html)

### 3.3 JavaScript's event loop

Directly relevant to this project's own history: the (ultimately
abandoned) idea of a browser-DOM-based locator, explored via Playwright,
would have meant driving a browser — and every browser's JavaScript
engine runs on a **single-threaded event loop**, the exact same
*conceptual* model as Python's `asyncio` (covered in
`LEARNING_RESOURCES.md` §9): one thread, a queue of callbacks, and
"blocking" work handed off elsewhere so the loop never freezes. The talk
below is the single most-recommended explanation of this model, full
stop, regardless of which language you're using it to reason about.

- [Philip Roberts — "What the heck is the event loop anyway?" (JSConf EU)](https://www.youtube.com/watch?v=8aGhZQkoFbQ)

### 3.4 SQL as a different paradigm

Every language discussed so far is **imperative** — you write a sequence
of steps ("do this, then this, then this"). SQL is **declarative** — you
describe *what result you want* (`SELECT name FROM users WHERE age >
18`) and leave *how* to get it entirely to the database engine's query
planner. Learning to think declaratively is a genuinely different mental
model from everything else in this document, and worth deliberately
practicing rather than writing SQL like a for-loop in disguise.

### 3.5 Go and Rust, briefly

Not used anywhere in this project, but worth knowing conceptually as two
modern, widely-adopted alternatives to Python with very different
tradeoffs: **Go** is garbage-collected like Python but compiled, and its
concurrency model (goroutines + channels — lightweight, runtime-managed
concurrent tasks that communicate by passing messages rather than sharing
memory directly) is a genuinely different answer to the concurrency
question than either Python's `asyncio` or `threading`. **Rust** trades
a steeper learning curve (the ownership system in §3.2) for C-level
performance with memory-safety guarantees enforced at compile time,
without a garbage collector.

- [A Tour of Go](https://go.dev/tour/) — official, interactive, runs in the browser.
- [The Rust Programming Language (the official book)](https://doc.rust-lang.org/book/)
