"""The movement building blocks: curves, easing, jitter, Fitts's law, and
the generator that combines them. Seeded `random.Random` = repeatable."""

import math
import random
import statistics
import unittest

from natural_mouse.geometry import MovementProfile, Point
from natural_mouse.path.bezier import BezierPathGenerator
from natural_mouse.path.curves import control_points, cubic, quadratic
from natural_mouse.path.easing import cosine, easing, linear, logistic
from natural_mouse.path.fitts import FittsLaw
from natural_mouse.path.jitter import micro_jitter

A, B = Point(0, 0), Point(300, 0)


class TestCurves(unittest.TestCase):
    def test_endpoints_are_exact(self):
        c1, c2 = Point(100, 80), Point(200, -80)
        self.assertEqual(quadratic(A, c1, B, 0), (0, 0))
        self.assertEqual(quadratic(A, c1, B, 1), (300, 0))
        self.assertEqual(cubic(A, c1, c2, B, 0), (0, 0))
        self.assertEqual(cubic(A, c1, c2, B, 1), (300, 0))

    def test_cubic_with_controls_on_the_line_is_straight(self):
        x, y = cubic(A, Point(100, 0), Point(200, 0), B, 0.5)
        self.assertAlmostEqual(y, 0)
        self.assertAlmostEqual(x, 150)

    def test_cubic_s_curve_crosses_the_line(self):
        c1, c2 = Point(100, 60), Point(200, -60)
        self.assertGreater(cubic(A, c1, c2, B, 0.25)[1], 0)
        self.assertLess(cubic(A, c1, c2, B, 0.75)[1], 0)

    def test_control_points_stay_within_curviness(self):
        rng = random.Random(1)
        for count in (1, 2):
            for _ in range(200):
                for c in control_points(A, B, count, 0.35, rng):
                    self.assertLessEqual(abs(c.y), 300 * 0.35 + 1e-9)
        with self.assertRaises(ValueError):
            control_points(A, B, 3, 0.35, rng)


class TestEasing(unittest.TestCase):
    def test_every_easing_runs_from_0_to_1_and_never_goes_back(self):
        for name in ("linear", "cosine", "logistic"):
            ease = easing(name, 12)
            self.assertAlmostEqual(ease(0), 0, msg=name)
            self.assertAlmostEqual(ease(1), 1, msg=name)
            values = [ease(i / 100) for i in range(101)]
            self.assertTrue(all(b >= a - 1e-12 for a, b in zip(values, values[1:])), name)

    def test_logistic_is_slow_at_the_ends_fast_in_the_middle(self):
        # Speed ~ slope. Steeper k = slower start and faster middle.
        def slope(f, t, h=1e-4):
            return (f(t + h) - f(t)) / h
        gentle, steep = (lambda t: logistic(t, 4)), (lambda t: logistic(t, 16))
        self.assertLess(slope(steep, 0.02), slope(gentle, 0.02))
        self.assertGreater(slope(steep, 0.5), slope(gentle, 0.5))
        self.assertGreater(slope(steep, 0.5), slope(linear, 0.5))
        self.assertAlmostEqual(logistic(0.5, 10), 0.5)          # symmetric
        self.assertAlmostEqual(cosine(0.5), 0.5)

    def test_bad_names_and_steepness(self):
        with self.assertRaises(ValueError):
            easing("bouncy")
        with self.assertRaises(ValueError):
            logistic(0.5, 0)


class TestFitts(unittest.TestCase):
    def test_formula(self):
        law = FittsLaw(a=0.1, b=0.2)
        # D = 300, W = 20: ID = log2(16) = 4 bits; MT = 0.1 + 0.2 * 4 = 0.9 s
        self.assertAlmostEqual(law.index_of_difficulty(300, 20), 4)
        self.assertAlmostEqual(law.movement_time(300, 20), 0.9)

    def test_time_grows_with_log_of_distance(self):
        law = FittsLaw()
        near, far = law.movement_time(100, 24), law.movement_time(800, 24)
        self.assertGreater(far, near)
        self.assertLess(far, near * 8 / 3)              # nowhere near 8x as long
        self.assertGreater(law.movement_time(400, 10), law.movement_time(400, 80))   # smaller = harder

    def test_zero_distance_is_just_a_and_bad_width_fails(self):
        self.assertAlmostEqual(FittsLaw(a=0.08).movement_time(0, 24), 0.08)
        with self.assertRaises(ValueError):
            FittsLaw().movement_time(100, 0)


class TestMicroJitter(unittest.TestCase):
    def test_tapers_to_zero_at_both_ends(self):
        offsets = micro_jitter(50, 2.0, 0.8, random.Random(3))
        self.assertEqual(offsets[0], (0.0, 0.0))
        self.assertAlmostEqual(offsets[-1][0], 0.0)
        self.assertAlmostEqual(offsets[-1][1], 0.0)

    def test_smoothing_makes_neighbours_closer(self):
        def roughness(smoothing):
            o = micro_jitter(400, 2.0, smoothing, random.Random(5))
            mid = o[100:300]                                   # away from the tapered ends
            return statistics.mean(abs(b[0] - a[0]) for a, b in zip(mid, mid[1:]))
        self.assertLess(roughness(0.85), roughness(0.0) / 2)

    def test_amplitude_is_kept_after_smoothing(self):
        o = micro_jitter(4000, 2.0, 0.8, random.Random(9))
        mid = [x for x, _ in o[1500:2500]]                     # taper ~ 1 here
        self.assertAlmostEqual(statistics.pstdev(mid), 2.0, delta=0.6)

    def test_off_and_bad_values(self):
        self.assertEqual(micro_jitter(5, 0, 0.5, random.Random()), [(0.0, 0.0)] * 5)
        with self.assertRaises(ValueError):
            micro_jitter(5, 1, 1.0, random.Random())


class TestGenerator(unittest.TestCase):
    def path(self, seed=1, **options):
        profile = MovementProfile(**options)
        return BezierPathGenerator(profile, random.Random(seed)).generate(Point(100, 500), Point(900, 200))

    def test_same_seed_same_path(self):
        a = [(p.x, p.y, p.delay) for p in self.path(seed=4, curve="cubic", easing="logistic")]
        b = [(p.x, p.y, p.delay) for p in self.path(seed=4, curve="cubic", easing="logistic")]
        self.assertEqual(a, b)

    def test_every_combination_lands_exactly(self):
        for curve in ("quadratic", "cubic"):
            for ease in ("linear", "cosine", "logistic"):
                for seed in range(20):
                    path = self.path(seed, curve=curve, easing=ease, jitter_smoothing=0.8, overshoot_chance=0.5)
                    self.assertEqual(path.end, Point(900, 200), f"{curve}/{ease}/{seed}")

    def test_fitts_sets_the_duration(self):
        law = FittsLaw(a=0.1, b=0.1)
        expected = law.movement_time(Point(100, 500).distance_to(Point(900, 200)), 24)
        for seed in range(20):
            path = self.path(seed, fitts=law, fitts_variability=0.0, overshoot_chance=0.0)
            self.assertAlmostEqual(path.total_duration, expected)

    def test_logistic_peak_speed_is_mid_movement(self):
        path = list(self.path(2, easing="logistic", logistic_steepness=12, jitter_px=0, overshoot_chance=0))
        steps = [math.dist((a.x, a.y), (b.x, b.y)) for a, b in zip(path, path[1:])]
        peak = steps.index(max(steps)) / len(steps)
        self.assertTrue(0.35 < peak < 0.65, peak)
        self.assertLess(steps[0], max(steps) / 4)              # slow start

    def test_typos_fail_at_once(self):
        with self.assertRaises(ValueError):
            BezierPathGenerator(MovementProfile(curve="cubik"))
        with self.assertRaises(ValueError):
            BezierPathGenerator(MovementProfile(easing="fast"))


if __name__ == "__main__":
    unittest.main()
