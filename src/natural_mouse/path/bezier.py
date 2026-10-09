"""Concrete PathGenerator that produces a curved, eased, jittered path with
an occasional overshoot-and-correct — the "human-like" strategy.

It combines four small building blocks, each in its own module:

    shape     curves.py   quadratic or cubic Bézier, control points off the line
    speed     easing.py   cosine or logistic (S-curve) progress over time
    wobble    jitter.py   smooth, tapered micro-jitter
    duration  fitts.py    Fitts's law (or a random duration in a range)

plus overshoot: sometimes aim a few pixels past the target, then make a
short correction back to it.
"""

from __future__ import annotations

import math
import random
from dataclasses import replace

from ..geometry import MovementProfile, Point
from .base import Path, PathGenerator, PathPoint
from .curves import CURVES, control_points, point_on
from .easing import easing
from .jitter import micro_jitter

MIN_STEPS = 8


class BezierPathGenerator(PathGenerator):
    """All tuning lives in the injected `MovementProfile`, so behavior is
    configured, not hardcoded. `rng` (a `random.Random`) can be passed
    to make paths reproducible, e.g. `random.Random(7)` in tests."""

    def __init__(self, profile: MovementProfile | None = None, rng: random.Random | None = None):
        self._profile = profile or MovementProfile()
        self._rng = rng or random.Random()  # noqa: S311 - movement variety, not security
        easing(self._profile.easing, self._profile.logistic_steepness)   # fail early on a typo
        if self._profile.curve not in CURVES:
            raise ValueError(f"unknown curve {self._profile.curve!r}; use one of {CURVES}")

    @property
    def profile(self) -> MovementProfile:
        return self._profile

    def duration(self, distance: float) -> float:
        """Seconds for a move of `distance` px: Fitts's law with some
        spread when `profile.fitts` is set, else random in `duration_range`."""
        p, rng = self._profile, self._rng
        if p.fitts is None:
            return rng.uniform(*p.duration_range)
        spread = rng.uniform(1 - p.fitts_variability, 1 + p.fitts_variability)
        return p.fitts.movement_time(distance, p.target_width_px) * spread

    def generate(self, start: Point, end: Point) -> Path:
        p, rng = self._profile, self._rng
        distance = start.distance_to(end)

        target = end
        should_correct = rng.random() < p.overshoot_chance and distance > 20
        if should_correct:
            overshoot = rng.uniform(*p.overshoot_px)
            angle = start.angle_to(end)
            target = Point(end.x + math.cos(angle) * overshoot, end.y + math.sin(angle) * overshoot)

        controls = control_points(start, target, 2 if p.curve == "cubic" else 1, p.curviness, rng)
        ease = easing(p.easing, p.logistic_steepness)
        steps = max(MIN_STEPS, int(distance / 100 * p.steps_per_100px))
        step_time = self.duration(distance) / steps
        wobble = micro_jitter(steps, p.jitter_px, p.jitter_smoothing, rng)

        points: list[PathPoint] = []
        for i in range(1, steps + 1):
            x, y = point_on(p.curve, start, controls, target, ease(i / steps))
            dx, dy = wobble[i - 1]
            points.append(PathPoint(x + dx, y + dy, step_time))

        if should_correct:
            correction = replace(p, duration_range=(0.08, 0.18), curviness=0.15, jitter_px=p.jitter_px * 0.6,
                                 overshoot_chance=0.0, fitts=None)
            points.extend(BezierPathGenerator(correction, rng).generate(target, end))
        else:
            last = points[-1]
            points[-1] = PathPoint(end.x, end.y, last.delay)

        return Path(points)
