import unittest

from testbench.report import (
    StepResult,
    format_table,
    summarize_click,
    summarize_moves,
    summarize_wheel,
)


def move(t, x, y):
    return {"type": "mousemove", "t": t, "x": x, "y": y, "scrollY": 0}


class TestSummaries(unittest.TestCase):
    def test_moves_path_vs_straight(self):
        # An L shape: 30 px right then 40 px down; straight line is 50.
        s = summarize_moves([move(0, 0, 0), move(10, 30, 0), move(25, 30, 40)])

        self.assertEqual((s.events, s.duration_ms, s.path_px, s.straight_px), (3, 25, 70, 50))
        self.assertAlmostEqual(s.curviness, 1.4)

    def test_no_moves(self):
        s = summarize_moves([])
        self.assertEqual(s.events, 0)
        self.assertEqual(s.curviness, 1.0)

    def test_wheel_totals_gaps_and_page_movement(self):
        before = [{"type": "scroll", "t": 0, "scrollY": 100}]
        during = [
            {"type": "wheel", "t": 10, "deltaY": 200, "scrollY": 100},
            {"type": "wheel", "t": 70, "deltaY": 100, "scrollY": 180},
            {"type": "wheel", "t": 200, "deltaY": 200, "scrollY": 300},
            {"type": "scroll", "t": 400, "scrollY": 600},
        ]

        w = summarize_wheel(before, during)

        self.assertEqual(w.events, 3)
        self.assertEqual(w.total_delta_y, 500)
        self.assertEqual(w.gaps_ms, (60, 95, 130))
        self.assertEqual(w.scrolled_px, 500)

    def test_wheel_with_nothing_received(self):
        w = summarize_wheel([], [])
        self.assertEqual((w.events, w.gaps_ms, w.scrolled_px), (0, None, 0))

    def test_click_uses_last_click(self):
        c = summarize_click([
            {"type": "click", "t": 1, "target": None},
            {"type": "click", "t": 2, "target": "start", "dx": 0.1, "dy": -0.2},
        ])
        self.assertTrue(c.hit)
        self.assertEqual((c.target, c.dx, c.dy), ("start", 0.1, -0.2))
        self.assertIsNone(summarize_click([move(0, 1, 1)]))

    def test_table_lists_every_step(self):
        text = format_table([
            StepResult("click magenta", True, "hit"),
            StepResult("scroll down 5", False, "nothing"),
        ])
        self.assertIn("click magenta", text)
        self.assertIn("FAIL", text)
        self.assertEqual(len(text.splitlines()), 4)  # header, rule, 2 rows


if __name__ == "__main__":
    unittest.main()
