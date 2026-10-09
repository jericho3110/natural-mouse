"""The whole bench scenario, with a fake browser instead of a real one.

`FakeBrowser` plays both parts the real run needs: it is the automator
(locate/click/scroll) *and* the page, posting the events a browser would
send to the bench's real local server over HTTP. So everything except
the real mouse and screen is exercised: server, waiting, judging, table.
"""

import json
import unittest
import urllib.request

from natural_mouse import Point
from natural_mouse.vision.base import Match
from testbench.bench import FINISH, START, BenchConfig, run_bench

FAST = BenchConfig(
    load_timeout=2, find_timeout=0.5, settle_seconds=0, quiet_seconds=0.05, search_quiet_seconds=0.05,
)


class FakeBrowser:
    def __init__(self, finish_at_scroll_y=1500, click_misses=False, focused=True):
        self.focused = focused
        self.url = None
        self.scroll_y = 0
        self.finish_at = finish_at_scroll_y
        self.click_misses = click_misses
        self.cursor = Point(10, 10)

    # --- the page side -----------------------------------------------------

    def post(self, *events):
        base = self.url.split("?")[0].rstrip("/")
        token = self.url.split("t=")[1]
        body = json.dumps([dict(e, scrollY=self.scroll_y) for e in events]).encode()
        req = urllib.request.Request(f"{base}/events?t={token}", data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5).close()

    def open(self, url):
        self.url = url
        self.post({"type": "ready", "t": 0, "focused": self.focused})

    # --- the automator side ------------------------------------------------

    def locate(self, colour, region=None, confidence=0.85):
        if colour == START:
            return Match(100, 100, 240, 80, 1.0)
        if colour == FINISH and self.scroll_y >= self.finish_at:
            return Match(100, 700, 240, 80, 1.0)
        return None

    def find_and_click(self, colour, **_):
        match = self.locate(colour)
        if match is None:
            return False
        self.cursor = match.center
        target = None if self.click_misses else {START: "start", FINISH: "finish"}[colour]
        self.post({"type": "mousemove", "t": 1, "x": 0, "y": 0},
                  {"type": "mousemove", "t": 50, "x": 30, "y": 40},
                  {"type": "click", "t": 60, "target": target, "dx": 0.1, "dy": -0.1})
        return True

    def scroll(self, amount, **_):
        self.post({"type": "wheel", "t": 100, "deltaY": -amount * 100})
        self.scroll_y = max(0, self.scroll_y - amount * 100)
        self.post({"type": "scroll", "t": 150})


def run(browser, cursor=None):
    lines = []
    code = run_bench(browser, cursor or (lambda: browser.cursor), opener=browser.open,
                     out=lines.append, config=FAST)
    return code, "\n".join(lines)


class TestRunBench(unittest.TestCase):
    def test_full_run_passes(self):
        code, text = run(FakeBrowser())

        self.assertEqual(code, 0, text)
        for step in ("click magenta", "scroll down 5", "scroll up 5", "scroll to cyan", "click cyan"):
            self.assertIn(step, text)
        self.assertIn("All steps passed.", text)
        self.assertIn("in view after 5 nudge(s)", text)  # 5 x 3 notches x 100 px = 1500

    def test_page_never_loads(self):
        browser = FakeBrowser()
        lines = []
        code = run_bench(browser, lambda: browser.cursor, opener=lambda url: None,
                         out=lines.append, config=BenchConfig(load_timeout=0.1))
        self.assertEqual(code, 1)
        self.assertIn("didn't load", "\n".join(lines))

    def test_waits_for_you_to_bring_the_window_to_front(self):
        # Found live: the browser opened its tab behind VS Code, because
        # Windows won't let a background program take the foreground.
        browser = FakeBrowser(focused=False)
        lines = []
        code = run_bench(browser, lambda: browser.cursor, opener=browser.open, out=lines.append,
                         config=BenchConfig(focus_timeout=0.1, settle_seconds=0))
        text = "\n".join(lines)
        self.assertEqual(code, 1)
        self.assertIn("Click the browser window", text)
        self.assertIn("never came to the front", text)

    def test_missed_click_fails(self):
        code, text = run(FakeBrowser(click_misses=True))
        self.assertEqual(code, 1)
        self.assertIn("click landed outside the target", text)

    def test_target_never_scrolls_into_view(self):
        code, text = run(FakeBrowser(finish_at_scroll_y=10**9))
        self.assertEqual(code, 1)
        self.assertIn("never came into view", text)

    def test_moving_the_mouse_stops_the_run(self):
        browser = FakeBrowser()
        positions = iter([Point(10, 10), Point(500, 500)])
        # First read is the start position; the next one is far away, as
        # if the user grabbed the mouse before the first step.
        code, text = run(browser, cursor=lambda: next(positions, Point(500, 500)))
        self.assertEqual(code, 1)
        self.assertIn("You moved the mouse", text)

    def test_moving_the_mouse_while_a_step_settles_stops_the_run(self):
        # Regression (found live): a hand on the touchpad kept the page busy
        # for 5 s after the first click and wasn't noticed until a step later.
        # Reads: start, before step 1, right after the click, after settling.
        positions = iter([Point(10, 10), Point(10, 10), Point(220, 140)])
        code, text = run(FakeBrowser(), cursor=lambda: next(positions, Point(900, 900)))
        self.assertEqual(code, 1)
        self.assertIn("You moved the mouse", text)
        self.assertNotIn("click magenta", text)  # the disturbed step isn't reported as a result


if __name__ == "__main__":
    unittest.main()
