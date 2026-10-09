# Architecture

This document has two audiences: (1) explaining how `natural_mouse` works,
and (2) teaching the reasoning behind *why* it's built this way — the
engineering principles, not just the file list — so the approach can be
reused on other projects.

## What this project does

Finds a UI element on screen (image matching), moves the real cursor to
it along a human-like curved path (Bezier curve, eased speed, jitter,
occasional overshoot-and-correct), and clicks or scrolls. Two front ends
(a CLI and a Tkinter GUI) sit on top of the same core library. Every
action — a CLI command, a GUI button press — happens because a human
triggered it, then it's done. Nothing in this codebase loops, schedules,
or runs unattended, by design.

```text
                    main.py (CLI)         gui/app.py (Tkinter)
                         \                    /
                          \                  /
                       natural_mouse.UIAutomator
                       (orchestrator, in automator.py)
                       /        |         \
                      v         v          v
              ScreenLocator  InputExecutor  PathGenerator
               (abstract)     (abstract)     (abstract)
                     |             |               |
           +---------+      +-----+-----+          v
           v                v           v    BezierPathGenerator
  TemplateMatchLocator  Win32InputExecutor  FakeInputExecutor
   (OpenCV + mss)       (Win32 SendInput)    (for tests)
```

`main.py` and `gui/app.py` are the only files that import concrete
classes directly (`TemplateMatchLocator`, `Win32InputExecutor`,
`BezierPathGenerator`). Every other file talks only to the abstract type
above it in this diagram. That one fact is the single most important
design decision in this codebase — everything else follows from it.

---

## Part 1: The principles, with real examples from this code

### Dependency Inversion (the big one)

**The idea:** high-level logic ("find something and click it") shouldn't
depend on low-level details ("how OpenCV matches templates," "how Win32
moves a cursor"). Both should depend on a shared abstraction.

**Where it lives here:** `UIAutomator.__init__` (`automator.py`) takes a
`ScreenLocator`, an `InputExecutor`, and a `PathGenerator` — all three
typed as the *abstract* base class, never the concrete one:

```python
def __init__(self, locator: ScreenLocator, executor: InputExecutor, path_generator: PathGenerator):
```

`UIAutomator` never imports `TemplateMatchLocator` or `Win32InputExecutor`
anywhere. It literally cannot — there's no `import` statement for them in
that file. This is what "depends on abstractions, not concretions" means
in practice: it's enforced by what the file imports, not just a style
preference.

**Why it matters, concretely:** this is *why* `tests/test_automator.py`
can test `UIAutomator`'s logic (does it click when a match is found? does
it skip clicking when there's no match? does `scroll(at=...)` move first?)
without ever touching a real screen or a real cursor. It hands
`UIAutomator` a `FakeScreenLocator` and a `FakeInputExecutor` instead —
objects that satisfy the same abstract contract but just record what
happened instead of doing it for real. If `UIAutomator` had imported
`Win32InputExecutor` directly, this kind of test would be impossible
without actually moving your mouse during every test run.

### The Strategy pattern

Each of the three abstractions (`PathGenerator`, `InputExecutor`,
`ScreenLocator`) is a "strategy": a family of interchangeable algorithms
behind one interface. Concretely:

- `PathGenerator.generate(start, end) -> Path` — today's only strategy is
  `BezierPathGenerator`. A `LinearPathGenerator` (straight line, no
  jitter) could be added for deterministic tests without touching
  anything else.
- `InputExecutor` — `Win32InputExecutor` (real cursor) vs.
  `FakeInputExecutor` (records calls, used only in tests). Both already
  exist in this codebase and are a working example of the same interface
  serving two completely different purposes.
- `ScreenLocator` — only `TemplateMatchLocator` exists today, but the
  interface doesn't assume "image matching" as a concept — `locate()`'s
  first argument is deliberately named `query` (not `template_path`)
  specifically so an OCR-based or different kind of locator could
  implement it later without the interface needing to change.

**The test for "did I actually apply this pattern correctly":** can you
add a new strategy by writing one new file, without editing any existing
file except the one composition root that wires concrete classes
together? In this codebase, yes — that's exactly how `FakeInputExecutor`
was added after `Win32InputExecutor` already existed, with zero changes
to `automator.py`.

### Single Responsibility Principle

Every file answers exactly one question:

| File | Question it answers |
| --- | --- |
| `geometry.py` | What is a point / a movement configuration? |
| `path/base.py` | What is a path, abstractly? |
| `path/bezier.py` | How do you generate a *human-like* path? |
| `input/base.py` | What can you do to a cursor, abstractly? |
| `input/win32_executor.py` | How do you *actually* move the Windows cursor? |
| `input/fake_executor.py` | How do you fake moving a cursor, for tests? |
| `vision/base.py` | What is "found something on screen," abstractly? |
| `vision/template_locator.py` | How do you *actually* find an image on screen? |
| `screen.py` | How do you grab a screenshot? (shared by vision and capture) |
| `capture.py` | How do you save a screen region to a file? |
| `automator.py` | How do the three abstractions get composed into one action? |
| `main.py` | How does a human trigger an action from a terminal? |
| `gui/app.py` | How does a human trigger an action from a window? |

Notice `screen.py` exists *because* two unrelated things
(`TemplateMatchLocator` and `capture_region`) both needed "grab a
screenshot." The first version of this code had that logic duplicated
inside `TemplateMatchLocator` as a private method; it moved out into its
own file the moment a second caller needed it. That's the practical
signal for "this deserves its own file": not a rule applied up front, but
duplication showing up as soon as a second thing needs the same
behavior.

### Encapsulation

Encapsulation here isn't "make fields private for its own sake" — it's
*hiding a specific kind of complexity behind a small, stable surface* so
the rest of the code never has to think about it:

- `Win32InputExecutor` hides every `ctypes.Structure`, every raw Win32
  flag (`_MOUSEEVENTF_WHEEL = 0x0800`), and the bit-masking needed to pass
  a negative number into a technically-unsigned Windows struct field.
  Nothing outside that one file ever sees a `ctypes` object.
- `Match.random_point(center_bias)` hides "pick a believable point inside
  a bounding box, weighted toward the center." Nothing outside `Match`
  ever reaches in and computes `match.x + random.random() * match.width`
  by hand — which matters because that computation has a subtlety (bias
  toward center, clamped to stay inside the box) that would be easy to
  get slightly wrong if every caller reimplemented it.
- `Path` hides its internal list of `PathPoint`s behind `__iter__`,
  `.end`, and `.total_duration`. Callers never index into it or mutate
  it — it's read-only by construction (`self._points = tuple(points)`).

**Rule of thumb used throughout:** if a piece of logic involves a
platform-specific API, a third-party library's quirks, or an invariant
that would be easy to violate by accident (like "this list should never
be mutated after creation"), it gets wrapped in a class with a small
public surface, even if that means a "boring" file with mostly private
methods.

### Composition Root

`main.py`'s `build_automator()` and `gui/app.py`'s `App.__init__` are the
*only* places in this codebase that write `TemplateMatchLocator()`,
`Win32InputExecutor()`, or `BezierPathGenerator()`. This single point
where concrete classes get chosen and wired together is called the
"composition root." Everything built before that point (the whole
`natural_mouse` package) knows nothing about which concrete classes will
eventually be used — it's all written against the abstractions.

**Why this specific rule ("only the composition root picks concretions")
is worth internalizing:** it's what makes the CLI and the GUI able to
share 100% of the actual logic (`natural_mouse`) while having completely
different entry points. Neither had to modify the library to exist; they
each just wrote their own small composition root.

### Value objects and immutability

`Point`, `PathPoint`, and `Match` are all `@dataclass(frozen=True)` —
immutable. Once created, they can't change. This matters because they get
passed around between layers (vision hands a `Match` to `automator`,
which derives a `Point` and hands it to the executor) — if any of those
were mutable, a bug in one layer could silently corrupt state another
layer is relying on. Making them immutable removes an entire category of
bug before it can happen, rather than relying on discipline to avoid it.

---

## Part 2: Testing philosophy

`tests/test_bezier.py` tests **pure logic** — `BezierPathGenerator` does
no I/O, so its tests just call `generate()` many times (it's randomized)
and assert invariants: the path always ends exactly on target, always has
a minimum number of points, duration stays in bounds. No mocking needed,
because there's nothing to mock — this is the easiest kind of code to
test, and it's easy specifically *because* the Bezier math was kept
separate from anything touching the OS.

`tests/test_automator.py` tests **orchestration logic** — the
decision-making in `UIAutomator` (locate, then click if found; move
first, then scroll). This is only testable in isolation because of the
Dependency Inversion described above: `FakeInputExecutor` and the
in-file `FakeScreenLocator` let the test assert "was `click` called with
a point inside the match's box?" without any real screen or cursor
involved.

**The pattern to remember:** when code is hard to test, it's usually
because it has two responsibilities tangled together — "decide what to
do" and "actually do it, touching the real world." Separating those (one
class that decides, one class that acts, connected through an interface)
is what makes both halves independently testable.

---

## Part 3: Worked example — debugging the scroll bug

This actually happened during development and is a good case study in
methodology, not just a bug story.

**Symptom reported:** "clicking and movement work fine, but scrolling
doesn't do anything."

**Step 1 — find the actual call chain, don't guess.** `scroll` on the CLI
goes: `main.py: run_scroll` → `UIAutomator.scroll()` →
`Win32InputExecutor.scroll()` → `SendInput` with `MOUSEEVENTF_WHEEL`.
Read every link before touching anything.

**Step 2 — compare against the working path.** `click` goes through
`UIAutomator.find_and_click()`, which calls
`self._executor.click(target, ...)`, and `Win32InputExecutor.click()`
calls `self.move_to(target, ...)` *before* clicking. `scroll()` had no
equivalent — it called `self._executor.scroll(amount, steps, ...)`
directly, with no target and no move. That asymmetry between the two
"working" and "broken" paths is the bug, found by comparing them side by
side rather than staring at the scroll code alone.

**Step 3 — confirm the mechanism, not just the symptom.** Windows
delivers `WM_MOUSEWHEEL` to whatever's under the cursor at that instant —
this is a real OS behavior, not a bug in this codebase. So "scrolling
does nothing" actually meant "scrolling is happening, just wherever the
cursor was left over from the last command" (e.g., the terminal). This
step matters: fixing the *symptom* (make scroll visibly work) requires
understanding the *mechanism* (why wheel events go where they go),
otherwise the fix would be a guess.

**Step 4 — fix at the right layer.** The fix wasn't "add a move before
this one call site" — it was adding `at: Point | None` as a first-class
optional parameter on `UIAutomator.scroll()` itself, so every caller
(CLI, GUI, future callers) gets the option, not just the one place that
happened to be reported broken. The GUI's fix (use the selected target's
location) and the CLI's fix (`--at X Y`) are both just different ways of
supplying that same new parameter.

**Step 5 — regression test.** `test_scroll_with_at_moves_there_before_scrolling`
asserts the exact call order (`move_to` then `scroll`) using
`FakeInputExecutor`, so this specific bug can never silently come back.

**Step 6 — verify live, honestly.** The fix was confirmed by actually
running it against a real point on screen and observing real content
scroll — not just "the code runs without an exception." A CLI command
returning exit code 0 proves nothing about whether the intended visible
effect happened.

---

## Part 4: Extension points (how to prove the architecture actually works)

If you want to test your own understanding, try one of these — each
should only require adding a new file, not editing existing ones (except
the one composition root):

- **A `LinearPathGenerator`** (straight line, constant speed, no jitter)
  implementing `PathGenerator` — useful for deterministic tests, and a
  good way to see exactly how little `UIAutomator` cares which path
  strategy it's holding.
- **An OCR-based `ScreenLocator`** — implement `locate`/`locate_all`
  using text recognition instead of pixel matching. The interface
  (`query: str`) was deliberately named generically enough to support
  this without changing `ScreenLocator`'s contract.
- **A `MacInputExecutor`** — same idea as `Win32InputExecutor` but using
  macOS's Quartz Event Services instead of `ctypes`/`SendInput`. Proves
  the whole design isn't secretly Windows-specific outside that one file.

If any of these end up requiring a change to `automator.py`, that's a
sign the abstraction has a leak worth fixing.
