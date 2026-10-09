"""Shared value objects used across the package.

Keeping these in one place means every layer (path generation, input
execution, vision) speaks the same small vocabulary instead of passing
raw tuples around.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # only for the type hint: importing it for real would be circular (path -> geometry)
    from .path.fitts import FittsLaw


@dataclass(frozen=True)
class Point:
    """An immutable 2D screen coordinate."""

    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return math.hypot(other.x - self.x, other.y - self.y)

    def angle_to(self, other: "Point") -> float:
        return math.atan2(other.y - self.y, other.x - self.x)

    def as_tuple(self) -> tuple[float, float]:
        return self.x, self.y

    def __add__(self, other: "Point") -> "Point":
        return Point(self.x + other.x, self.y + other.y)


@dataclass
class MovementProfile:
    """Tunable parameters describing how a "natural" movement should feel.

    This is deliberately just configuration data (no behavior) so it can be
    constructed, copied, and passed between unrelated components without
    coupling them to each other. The defaults reproduce the original
    behaviour (quadratic curve, cosine easing, random duration); the
    other options are explained in path/curves.py, easing.py, jitter.py
    and fitts.py, and compared visually by `python src/main.py pathlab`.
    """

    duration_range: tuple[float, float] = (0.25, 0.55)  # used when `fitts` is None
    curviness: float = 0.35          # how far control points sit off the line (x distance)
    jitter_px: float = 1.2           # micro-jitter strength (std dev, px); 0 = none
    jitter_smoothing: float = 0.0    # 0 = plain noise; 0.7-0.9 = smooth, tremor-like
    overshoot_chance: float = 0.25
    overshoot_px: tuple[float, float] = (4.0, 14.0)
    steps_per_100px: int = 18
    curve: str = "quadratic"         # "quadratic" or "cubic"
    easing: str = "cosine"           # "linear", "cosine" or "logistic"
    logistic_steepness: float = 10.0  # k for easing="logistic"
    fitts: FittsLaw | None = None    # set to time moves by Fitts's law instead of duration_range
    target_width_px: float = 24.0    # W in Fitts's law: a typical target's size
    fitts_variability: float = 0.15  # +/- this fraction of random spread on the Fitts time
