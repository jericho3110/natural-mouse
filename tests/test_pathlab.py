"""The path lab: the measurements on hand-made paths, and a full run that
writes a real PNG (no screen, no mouse)."""

import os
import tempfile
import unittest

import cv2

from natural_mouse import MovementProfile, Path, PathPoint, Point
from pathlab import compare, measure, run, summarize
from pathlab.lab import fitts_table, table

START, END = Point(0, 0), Point(100, 0)


def path(*xy, delay=0.01):
    return Path([PathPoint(x, y, delay) for x, y in xy])


class TestMeasure(unittest.TestCase):
    def test_straight_line(self):
        s = measure(START, END, path((50, 0), (100, 0)))
        self.assertAlmostEqual(s.straightness, 1.0)
        self.assertEqual((s.deviation_px, s.overshoot_px), (0, 0))
        self.assertAlmostEqual(s.max_step_px, 50)
        self.assertAlmostEqual(s.max_gap_ms, 10)
        self.assertAlmostEqual(s.duration_s, 0.02)

    def test_bow_and_overshoot(self):
        s = measure(START, END, path((50, 30), (108, 2), (100, 0)))
        self.assertAlmostEqual(s.deviation_px, 30)
        self.assertAlmostEqual(s.overshoot_px, 8)
        self.assertGreater(s.straightness, 1.0)

    def test_wobble_is_zero_on_a_smooth_line_and_positive_on_a_zigzag(self):
        smooth = measure(START, END, path(*[(x, 0) for x in range(10, 101, 10)]))
        zigzag = measure(START, END, path(*[(x, 3 if x % 20 else -3) for x in range(10, 101, 10)]))
        self.assertAlmostEqual(smooth.wobble_px, 0)
        self.assertGreater(zigzag.wobble_px, 2)

    def test_peak_speed_time(self):
        # Slow, fast, slow: the fast step is the second of three.
        s = measure(START, END, path((10, 0), (90, 0), (100, 0)))
        self.assertAlmostEqual(s.peak_at, 2 / 3)

    def test_summary_overshoot_rate(self):
        a = measure(START, END, path((50, 0), (100, 0)))
        b = measure(START, END, path((110, 0), (100, 0)))
        self.assertEqual(summarize([a, b]).overshoot_rate, 0.5)


class TestLab(unittest.TestCase):
    def test_same_seed_same_numbers(self):
        variants = {"a": MovementProfile(curve="cubic", easing="logistic")}
        self.assertEqual(compare(variants, 5, seed=3)["a"][1], compare(variants, 5, seed=3)["a"][1])

    def test_tremor_smoothing_reduces_wobble(self):
        results = compare({"plain": MovementProfile(jitter_px=1.5),
                           "tremor": MovementProfile(jitter_px=1.5, jitter_smoothing=0.85)}, 20, seed=1)
        self.assertLess(results["tremor"][1].wobble_px, results["plain"][1].wobble_px)

    def test_full_run_writes_a_picture(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "lab.png")
            lines = []
            self.assertEqual(run(out=out, runs=3, seed=2, print_=lines.append), 0)
            image = cv2.imread(out)
            self.assertIsNotNone(image)
            self.assertGreater(image.shape[0], 1000)          # five rows
        text = "\n".join(lines)
        self.assertIn("classic: quadratic + cosine", text)
        self.assertIn("Fitts's law", text)

    def test_tables(self):
        self.assertIn("variant", table(compare({"x": MovementProfile()}, 2, 1)).splitlines()[0])
        self.assertEqual(len(fitts_table().splitlines()), 8)


if __name__ == "__main__":
    unittest.main()
