import unittest

from natural_mouse.automator import UIAutomator
from natural_mouse.geometry import Point
from natural_mouse.input.fake_executor import FakeInputExecutor
from natural_mouse.path.bezier import BezierPathGenerator
from natural_mouse.vision.base import Match, ScreenLocator


class FakeScreenLocator(ScreenLocator):
    """Always reports the same fixed Match, regardless of query — a
    stand-in for real screen matching so UIAutomator's own logic can be
    tested in isolation."""

    def __init__(self, match: Match | None):
        self._match = match

    def locate(self, query, region=None, confidence=0.85):
        return self._match

    def locate_all(self, query, region=None, confidence=0.85):
        return [self._match] if self._match else []


class TestUIAutomator(unittest.TestCase):
    def setUp(self):
        self.fixed_match = Match(x=100, y=200, width=40, height=20, confidence=1.0)
        self.executor = FakeInputExecutor()
        self.automator = UIAutomator(
            locator=FakeScreenLocator(self.fixed_match),
            executor=self.executor,
            path_generator=BezierPathGenerator(),
        )

    def test_find_and_click_returns_true_and_clicks_when_match_found(self):
        result = self.automator.find_and_click("anything.png")

        self.assertTrue(result)
        self.assertEqual(len(self.executor.calls), 1)
        call_type, target = self.executor.calls[0]
        self.assertEqual(call_type, "click")
        # The click point should land inside the match's bounding box.
        self.assertTrue(80 <= target.x <= 140)
        self.assertTrue(180 <= target.y <= 220)

    def test_find_and_click_returns_false_when_no_match(self):
        automator = UIAutomator(
            locator=FakeScreenLocator(None),
            executor=self.executor,
            path_generator=BezierPathGenerator(),
        )

        result = automator.find_and_click("anything.png")

        self.assertFalse(result)
        self.assertEqual(self.executor.calls, [])

    def test_scroll_forwards_to_executor(self):
        self.automator.scroll(5, steps=2)

        self.assertEqual(self.executor.calls, [("scroll", 5)])

    def test_scroll_with_at_moves_there_before_scrolling(self):
        # Regression test: scroll() used to fire the wheel event wherever
        # the cursor already happened to be, since Windows delivers wheel
        # events to whatever's under the cursor rather than to a specific
        # window. `at` must move the cursor there first.
        target = Point(300, 400)

        self.automator.scroll(-5, steps=2, at=target)

        self.assertEqual(
            self.executor.calls,
            [("move_to", target), ("scroll", -5)],
        )


if __name__ == "__main__":
    unittest.main()
