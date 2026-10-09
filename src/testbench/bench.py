"""The bench scenario: open the test page, drive the real mouse, measure.

One call, `run_bench(...)`, does the whole run:

    1. start the local server and open the page in the browser
    2. wait for the page to load and for you to click the browser window
       (Windows won't let us bring it to the front), then find the magenta target
    3. move + click the magenta target
    4. scroll down, then back up
    5. scroll down until the cyan target is on screen
    6. move + click the cyan target
    7. print a table of what the *browser* received, and stop the server

The automator and the cursor reader are passed in (dependency injection),
so this module never picks concrete classes; `main.py` does. It's a
test run you start and watch: it does the steps above once and exits.
Moving the mouse yourself between steps stops it.
"""

from __future__ import annotations

import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from natural_mouse import Point, UIAutomator

from .report import (
    StepResult,
    format_table,
    summarize_click,
    summarize_moves,
    summarize_wheel,
)
from .server import BenchServer

START = "#ff00ff"   # magenta block near the top of the page
FINISH = "#00ffff"  # cyan block below the feed


class UserTookOver(Exception):
    """The cursor moved between steps: someone grabbed the mouse."""


@dataclass
class BenchConfig:
    load_timeout: float = 30.0     # seconds to wait for the page to load
    focus_timeout: float = 60.0    # seconds to wait for you to click the browser window
    find_timeout: float = 10.0     # seconds to look for the first target
    scroll_notches: int = 5        # size of the down/up scroll steps
    search_notches: int = 3        # size of each "scroll until found" nudge
    max_search_scrolls: int = 15   # give up looking for the cyan target after this many
    hands_off_px: float = 25.0     # cursor drift between steps that counts as "user moved it"
    settle_seconds: float = 1.0    # pause after the page loads, for the window to appear
    quiet_seconds: float = 0.6     # a step is over when no event arrived for this long
    search_quiet_seconds: float = 0.4  # same, between "scroll until found" nudges


def load_page() -> str:
    return (Path(__file__).parent / "page.html").read_text(encoding="utf-8")


def run_bench(
    automator: UIAutomator,
    cursor: Callable[[], Point],
    opener: Callable[[str], object] = webbrowser.open,
    out: Callable[[str], object] = print,
    config: BenchConfig | None = None,
) -> int:
    """Run the scenario once. Returns 0 if every step passed, else 1."""
    config = config or BenchConfig()
    server = BenchServer(load_page())
    url = server.start()
    steps: list[StepResult] = []
    try:
        out("Opening the test page. Keep the browser window in front, at 100% zoom.")
        out("Move the mouse yourself at any time to stop the run.")
        opener(url)
        ready = server.wait_for(lambda e: e["type"] == "ready", timeout=config.load_timeout)
        if ready is None:
            out(f"The page didn't load within {config.load_timeout:.0f} s. Stopped.")
            return 1
        out(f"Page loaded: viewport {ready.get('innerW')}x{ready.get('innerH')} CSS px, "
            f"devicePixelRatio {ready.get('dpr')} (1.25 = 125% display scaling or zoom).")
        if not ready.get("focused"):
            out(f"Click the browser window to bring it to the front (waiting up to "
                f"{config.focus_timeout:.0f} s). The run starts after you let go of the mouse.")
            if server.wait_for(lambda e: e["type"] == "focus", timeout=config.focus_timeout) is None:
                out("The browser window never came to the front. Stopped.")
                return 1
        time.sleep(config.settle_seconds)  # let the window finish appearing before reading the screen
        if _find(automator, START, config.find_timeout) is None:
            out("Couldn't see the magenta target on screen. Is the browser window in front "
                "and not covered? Stopped.")
            return 1
        _Run(server, automator, cursor, config, steps).all_steps()
    except UserTookOver:
        out("You moved the mouse, so the run stopped. Results so far:")
    finally:
        server.stop()

    out("")
    out(format_table(steps))
    passed = bool(steps) and all(s.ok for s in steps) and len(steps) == 5
    out("")
    out("All steps passed." if passed else "Not every step passed (see above).")
    return 0 if passed else 1


def _find(automator: UIAutomator, colour: str, timeout: float):
    deadline = time.monotonic() + timeout
    while True:
        match = automator.locate(colour)
        if match is not None or time.monotonic() >= deadline:
            return match
        time.sleep(0.3)


class _Run:
    """Holds the shared state of one run so each step is a short method."""

    def __init__(self, server: BenchServer, automator: UIAutomator, cursor, config: BenchConfig, steps):
        self._server = server
        self._automator = automator
        self._cursor = cursor
        self._config = config
        self.steps: list[StepResult] = steps
        self._last_cursor = cursor()

    def all_steps(self) -> None:
        n = self._config.scroll_notches
        self._step("click magenta", lambda: self._automator.find_and_click(START), self._judge_click("start"))
        self._step(f"scroll down {n}", lambda: self._automator.scroll(-n), self._judge_scroll(down=True))
        self._step(f"scroll up {n}", lambda: self._automator.scroll(n), self._judge_scroll(down=False))
        self._step("scroll to cyan", self._scroll_until_finish_visible, self._judge_search)
        self._step("click cyan", lambda: self._automator.find_and_click(FINISH), self._judge_click("finish"))

    # --- running one step --------------------------------------------------

    def _check_hands_off(self) -> None:
        now = self._cursor()
        if now.distance_to(self._last_cursor) > self._config.hands_off_px:
            raise UserTookOver()

    def _step(self, name: str, action: Callable[[], object], judge) -> None:
        self._check_hands_off()
        before = self._server.events()
        outcome = action()
        self._last_cursor = self._cursor()
        self._server.wait_quiet(quiet=self._config.quiet_seconds)
        self._check_hands_off()  # moved while we waited for the page to settle?
        during = self._server.events()[len(before):]
        result = judge(name, outcome, before, during)
        result.moves = summarize_moves(during)
        self.steps.append(result)
        self._last_cursor = self._cursor()

    def _scroll_until_finish_visible(self) -> int | None:
        """Scroll down in small nudges until the cyan target is at least
        half on screen. Returns how many nudges it took, or None."""
        for nudges in range(self._config.max_search_scrolls + 1):
            match = self._automator.locate(FINISH)
            if match is not None and match.height >= 40:
                return nudges
            if nudges == self._config.max_search_scrolls:
                return None
            self._check_hands_off()
            self._automator.scroll(-self._config.search_notches)
            self._server.wait_quiet(quiet=self._config.search_quiet_seconds)
        return None

    # --- judging what the browser saw ----------------------------------------

    @staticmethod
    def _judge_click(expected: str):
        def judge(name, found, before, during):
            click = summarize_click(during)
            if not found:
                return StepResult(name, False, "target not found on screen")
            if click is None:
                return StepResult(name, False, "the page saw no click")
            if click.target != expected:
                return StepResult(name, False, f"click landed outside the target ({click.target})")
            return StepResult(name, True, f"hit, offset from centre dx={click.dx:+.2f} dy={click.dy:+.2f}",
                              extra={"dx": click.dx, "dy": click.dy})
        return judge

    @staticmethod
    def _judge_scroll(down: bool):
        def judge(name, _outcome, before, during):
            w = summarize_wheel(before, during)
            sign = 1 if down else -1
            ok = w.events > 0 and w.total_delta_y * sign > 0 and w.scrolled_px * sign > 0
            gaps = "-" if w.gaps_ms is None else f"{w.gaps_ms[0]:.0f}/{w.gaps_ms[1]:.0f}/{w.gaps_ms[2]:.0f} ms"
            detail = (f"{w.events} wheel events, deltaY {w.total_delta_y:+.0f}, "
                      f"page moved {w.scrolled_px:+.0f} px, gaps min/mean/max {gaps}")
            return StepResult(name, ok, detail, extra={"wheel": w})
        return judge

    @staticmethod
    def _judge_search(name, nudges, before, during):
        w = summarize_wheel(before, during)
        if nudges is None:
            return StepResult(name, False, "cyan target never came into view")
        return StepResult(name, True, f"in view after {nudges} nudge(s), page moved {w.scrolled_px:+.0f} px",
                          extra={"wheel": w})
