"""Speed over time: easing functions.

An easing function maps *time* (0..1) to *progress along the path*
(0..1). The path's points are equally spaced in time, so where the
function is steep the cursor moves fast, and where it's flat the cursor
moves slowly.

    linear     constant speed (robotic: starts and stops instantly)
    cosine     0.5 - 0.5·cos(πt): smooth start and stop, peak speed at the middle
    logistic   the logistic "S-curve" 1 / (1 + e^(-k(t - 0.5))), rescaled so
               it runs exactly from 0 to 1. `k` (steepness) sets how gently it
               starts: low k ≈ linear, high k = slow start, fast middle,
               slow finish

Real reaching movements speed up, peak, then slow down for the landing,
giving a bell-shaped speed curve. Both cosine and logistic produce that
bell; logistic lets you tune how sharp it is.
"""

from __future__ import annotations

import math
from collections.abc import Callable

EASINGS = ("linear", "cosine", "logistic")


def linear(t: float) -> float:
    return t


def cosine(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)


def logistic(t: float, k: float = 10.0) -> float:
    """The logistic function, rescaled so logistic(0) = 0 and logistic(1) = 1."""
    if k <= 0:
        raise ValueError("steepness k must be positive")

    def s(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-k * (x - 0.5)))

    low, high = s(0.0), s(1.0)
    return (s(t) - low) / (high - low)


def easing(name: str, steepness: float = 10.0) -> Callable[[float], float]:
    """The easing function called `name` (see EASINGS)."""
    if name == "linear":
        return linear
    if name == "cosine":
        return cosine
    if name == "logistic":
        return lambda t: logistic(t, steepness)
    raise ValueError(f"unknown easing {name!r}; use one of {EASINGS}")
