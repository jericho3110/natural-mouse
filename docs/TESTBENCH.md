# The live test bench

One command opens a local test page in your browser, drives the real
mouse over it with `natural_mouse`, and reports what the **browser**
actually received, which can differ from what the code meant to send.

## Contents

- [1. Run it](#1-run-it)
- [2. What happens, step by step](#2-what-happens-step-by-step)
- [3. Reading the results](#3-reading-the-results)
- [4. How it's built](#4-how-its-built)
- [5. Using the library from your own script](#5-using-the-library-from-your-own-script)
- [6. Security](#6-security)
- [7. Found live](#7-found-live)
- [8. Exercises](#8-exercises)
- [References](#references)

## 1. Run it

From `Natural/`, with the venv active (see the [README](../README.md#setup)):

```powershell
python src/main.py testbench            # opens the page in your default browser
python src/main.py testbench --no-open  # prints the URL; open it in any browser yourself
```

| Part | Meaning |
| --- | --- |
| `python src/main.py` | the project's single entry point (CLI + GUI) |
| `testbench` | the subcommand that runs the bench once |
| `--no-open` | don't call the default browser; print the page's URL instead |

Then:

1. When it asks, **click the browser window** to bring it to the front.
   Windows doesn't let a background program raise a window itself.
2. **Let go of the mouse.** The run takes about 15 seconds.
3. Moving the mouse yourself at any point stops the run.

It exits with code 0 if every step passed and 1 otherwise, and it
touches nothing outside the test page.

## 2. What happens, step by step

```text
main.py testbench
  │  builds UIAutomator(ColorLocator, Win32InputExecutor, BezierPathGenerator)
  ▼
bench.run_bench
  1. start BenchServer on 127.0.0.1:<random port>, random token
  2. open http://127.0.0.1:<port>/?t=<token>
  3. wait for the page's "ready" event, then for "focus" (you clicked it)
  4. find the magenta block (#ff00ff)             ── ColorLocator
  5. click magenta                                 ── find_and_click
  6. scroll down 5, scroll up 5                    ── scroll
  7. scroll down in small nudges until cyan (#00ffff) is half on screen
  8. click cyan
  9. print the table, stop the server
```

After each step the bench waits until the page has been quiet for
0.6 s (the page sends events every 150 ms, and smooth scrolling keeps
going after the last wheel event). It then judges that step only on the
events that arrived during it.

## 3. Reading the results

From the first live run on this machine (1920×1080 at 125% scaling,
Chrome):

```text
step           result  moves           curviness  details
-------------  ------  --------------  ---------  -------
scroll down 5  ok      0 in 0 ms       -          5 wheel events, deltaY +500, page moved +500 px, gaps min/mean/max 113/136/166 ms
scroll up 5    ok      0 in 0 ms       -          5 wheel events, deltaY -500, page moved -500 px, gaps min/mean/max 101/151/169 ms
```

| Column | Meaning |
| --- | --- |
| moves | `mousemove` events the page saw, and over how long. Browsers fire at most about one per frame, so this is lower than the number of points `SendInput` sent |
| curviness | trail length ÷ straight distance; 1.00 = straight line |
| dx / dy (clicks) | where the click landed: 0 = centre, ±1 = edge of the target |
| deltaY | wheel distance as the browser reports it; Chrome gave 100 per notch here |
| page moved | change in `window.scrollY`, i.e. whether the page really scrolled |
| gaps | time between wheel events: min / mean / max |

## 4. How it's built

| File | Layer | Job |
| --- | --- | --- |
| [src/testbench/page.html](../src/testbench/page.html) | browser | records mouse, wheel, scroll, click and focus events; POSTs them in batches |
| [src/testbench/server.py](../src/testbench/server.py) | I/O edge | `BenchServer`: serves the page, validates and stores events, `wait_for` / `wait_quiet` |
| [src/testbench/report.py](../src/testbench/report.py) | pure core | events → `MoveSummary`, `WheelSummary`, `ClickSummary`, table. No I/O |
| [src/testbench/bench.py](../src/testbench/bench.py) | orchestration | the scenario; gets the automator and cursor reader injected |
| [src/main.py](../src/main.py) | composition root | `run_testbench` picks the concrete classes |
| [src/natural_mouse/vision/color_locator.py](../src/natural_mouse/vision/color_locator.py) | library | `ColorLocator`, a new `ScreenLocator` strategy |

Design choices:

- **Measure at the receiving end.** Unit tests with `FakeInputExecutor`
  prove what the code *asks for*. Only a real browser shows what
  arrives: coalesced mouse moves, per-notch wheel deltas, DPI scaling.
- **`ColorLocator` instead of screenshot templates.** A solid colour
  block is found at any zoom or DPI. A template crop stops matching when
  scaling changes. The cost: a colour only works on pages you control,
  where nothing else uses it.
  - `confidence` means *fill ratio*: how much of the block's bounding
    box is that colour. That's how it ignores scattered pixels.
- **Functional core, imperative shell.** `report.py` is pure, so it's
  tested with hand-written events. The server, mouse and screen stay at
  the edges.
- **Dependency injection.** `run_bench(automator, cursor, opener, out,
  config)` takes everything it touches. That's how
  [tests/test_testbench_bench.py](../tests/test_testbench_bench.py)
  runs the whole scenario against a `FakeBrowser`, which plays both the
  automator and the page by posting events to the real local server.
  Everything runs except the real mouse.
- **Threads.** `ThreadingHTTPServer` handles requests on background
  threads. The events list is guarded by a `threading.Condition`, so
  `wait_for` sleeps until new events arrive instead of polling.
- **One run, then exit.** It's a test you start and watch, in line with
  the project's rule that every action is user-triggered.

## 5. Using the library from your own script

After `pip install -e .`, any script run with this venv's Python can
import the library. Nothing runs on import; you build one `UIAutomator`
and each method call does one action:

```python
from natural_mouse import BezierPathGenerator, ColorLocator, UIAutomator, Win32InputExecutor

automator = UIAutomator(
    locator=ColorLocator(),
    executor=Win32InputExecutor(),
    path_generator=BezierPathGenerator(),
)
automator.find_and_click("#ff00ff")   # True if found and clicked
automator.scroll(-5)                  # 5 notches down where the cursor is
```

| Call | Does | Returns |
| --- | --- | --- |
| `find_and_click(query, region=None, confidence=0.85, center_bias=0.6)` | locate, move, click | `True` / `False` |
| `locate(query, region=None, confidence=0.85)` | look only | `Match` or `None` |
| `scroll(amount, steps=5, step_delay_range=(0.05, 0.18), at=None)` | wheel; **negative = down** | `None` |

The sign is the opposite of the browser's: `scroll(-5)` arrives as
`deltaY = +500` (positive `deltaY` = down). All coordinates are physical
screen pixels (see [§7](#7-found-live)). Each part is explained in
[ARCHITECTURE.md](ARCHITECTURE.md).

## 6. Security

The bench runs a web server, so it's built defensively:

| Risk | Defence | Test |
| --- | --- | --- |
| other machines reach the server | binds `127.0.0.1` only, random free port | `test_listens_on_loopback_only` |
| another web page or program talks to it | random 32-character token on every request, compared in constant time (`hmac.compare_digest`) | `test_refuses_without_token_or_with_wrong_host` |
| DNS rebinding (a site re-points its name at 127.0.0.1) | `Host` header must be `127.0.0.1:<port>` or `localhost:<port>` | same test |
| huge or malformed posts | 256 KB body limit (413), JSON list of known event types only (400), 100 000 stored events max | `test_rejects_bad_or_oversized_posts`, `TestValidateBatch` |
| code execution | received data is only parsed with `json.loads` and counted; nothing is evaluated, run, or written to disk | — |
| page loading outside code | `Content-Security-Policy: default-src 'none'` plus inline script/style and same-origin fetch only | `test_serves_page_with_token` |
| run grabbing the mouse while you work | waits for you to click the browser window, then stops as soon as you move the mouse | `test_waits_for_you_to_bring_the_window_to_front`, `test_moving_the_mouse_*` |

## 7. Found live

| Found | Fix | Test that pins it |
| --- | --- | --- |
| At 125% scaling, the process saw a 1536×864 screen until `mss` took its first screenshot, then 1920×1080: `mss` makes the process DPI-aware on its first grab. Cursor positions and screen size changed units mid-run. | `Win32InputExecutor.__init__` calls `make_process_dpi_aware()` up front, so coordinates are always physical pixels | `tests/test_win32_executor.py` (verified to fail without the fix) |
| The browser opened its tab behind VS Code, so the colour blocks weren't on screen. Windows' foreground lock stops background programs from raising windows. | the page reports `document.hasFocus()`; the bench asks you to click the window and waits for a `focus` event | `test_waits_for_you_to_bring_the_window_to_front` |
| A hand on the touchpad kept events coming for 5 s after a step and wasn't noticed until the next step. | cursor checked right after each action and again after the page settles | `test_moving_the_mouse_while_a_step_settles_stops_the_run` |
| A test run hung for minutes: the fake page never reported focus, so every test waited 60 s. | `FakeBrowser` reports `focused`, and `focus_timeout` is configurable | the whole bench test file runs in ~3 s |

## 8. Exercises

1. Run the bench twice and compare the `gaps` columns. Which setting in
   `UIAutomator.scroll` controls them?
2. Zoom the page to 150% (Ctrl +) and run again. Does `ColorLocator`
   still find the blocks? Would `TemplateMatchLocator` have?
3. Add a `"contextmenu"` event to `page.html`. What else must change for
   the server to accept it? (Hint: `EVENT_TYPES`.)
4. Write a test in `test_testbench_report.py` for a scroll step where the
   wheel fired but the page didn't move. What should `ok` be?

**Self-check:** why does the bench judge a scroll by `window.scrollY`
and not only by the number of wheel events?

## References

**Official**

- §1, §4: Python docs, [`http.server`](https://docs.python.org/3/library/http.server.html) (`ThreadingHTTPServer`, `BaseHTTPRequestHandler`)
- §4: Python docs, [`threading.Condition`](https://docs.python.org/3/library/threading.html#condition-objects)
- §6: Python docs, [`secrets`](https://docs.python.org/3/library/secrets.html) and [`hmac.compare_digest`](https://docs.python.org/3/library/hmac.html#hmac.compare_digest)
- §3: MDN, [`WheelEvent.deltaY`](https://developer.mozilla.org/en-US/docs/Web/API/WheelEvent/deltaY), [`mousemove`](https://developer.mozilla.org/en-US/docs/Web/API/Element/mousemove_event), [`Window.devicePixelRatio`](https://developer.mozilla.org/en-US/docs/Web/API/Window/devicePixelRatio)
- §6: MDN, [Content-Security-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy)
- §7: Microsoft Learn, [High DPI desktop application development on Windows](https://learn.microsoft.com/en-us/windows/win32/hidpi/high-dpi-desktop-application-development-on-windows), [`SetProcessDpiAwarenessContext`](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setprocessdpiawarenesscontext), [`SetForegroundWindow`](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow) (the foreground-lock rules)
- §4: OpenCV docs, [`connectedComponentsWithStats`](https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html) and [`inRange`](https://docs.opencv.org/4.x/d2/de8/group__core__array.html)

**Other explanations**

- §4: Gary Bernhardt, [Functional Core, Imperative Shell](https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell)
- §6: Wikipedia, [DNS rebinding](https://en.wikipedia.org/wiki/DNS_rebinding)

### Further learning

- Real Python, [Python's http.server](https://realpython.com/python-http-server/)
- [Exercism Python track](https://exercism.org/tracks/python)
