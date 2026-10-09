import unittest

from natural_mouse.geometry import MovementProfile, Point
from natural_mouse.path.bezier import BezierPathGenerator

ITERATIONS = 50


class TestBezierPathGenerator(unittest.TestCase):
    def setUp(self):
        self.profile = MovementProfile(duration_range=(0.2, 0.4))
        self.generator = BezierPathGenerator(self.profile)
        self.start = Point(0, 0)
        self.end = Point(400, 250)

    def test_path_ends_exactly_at_target(self):
        for _ in range(ITERATIONS):
            path = self.generator.generate(self.start, self.end)
            self.assertEqual(path.end, self.end)

    def test_path_has_minimum_step_count(self):
        for _ in range(ITERATIONS):
            path = self.generator.generate(self.start, self.end)
            self.assertGreaterEqual(len(path), 8)

    def test_total_duration_within_expected_bounds(self):
        # A run with no overshoot correction falls within duration_range
        # (plus floating point slack). A run WITH a correction segment adds
        # at most the correction segment's own duration_range on top.
        min_duration, max_duration = self.profile.duration_range
        max_correction = 0.18

        for _ in range(ITERATIONS):
            path = self.generator.generate(self.start, self.end)
            self.assertGreaterEqual(path.total_duration, min_duration - 1e-6)
            self.assertLessEqual(path.total_duration, max_duration + max_correction + 1e-6)

    def test_zero_distance_path_is_still_valid(self):
        # Start and end at the same point shouldn't raise or produce a
        # degenerate/empty path.
        same_point = Point(100, 100)
        path = self.generator.generate(same_point, same_point)
        self.assertEqual(path.end, same_point)
        self.assertGreaterEqual(len(path), 8)


if __name__ == "__main__":
    unittest.main()
