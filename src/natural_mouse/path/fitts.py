"""How long a movement takes: Fitts's law.

Fitts's law (Fitts, 1954; Shannon form by MacKenzie, 1992) predicts the
time to point at a target from its distance D and width W:

    ID = log2(D / W + 1)          index of difficulty, in bits
    MT = a + b · ID               movement time, in seconds

Far, small targets take longer than near, big ones, but time grows with
the *logarithm* of the distance: a move 8x as far takes nowhere near 8x
as long. `a` (start-up time) and `b` (seconds per bit) differ per person
and device; the defaults are in the range reported for a mouse.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FittsLaw:
    a: float = 0.08     # seconds: reaction / start-up time
    b: float = 0.11     # seconds per bit of difficulty

    def index_of_difficulty(self, distance: float, width: float) -> float:
        if width <= 0:
            raise ValueError("target width must be positive")
        return math.log2(max(distance, 0.0) / width + 1)

    def movement_time(self, distance: float, width: float) -> float:
        return self.a + self.b * self.index_of_difficulty(distance, width)
