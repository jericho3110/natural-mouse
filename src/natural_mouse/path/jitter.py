"""Micro-jitter: small, smooth wobble along a path, like hand tremor.

Plain random noise (a new random offset at every point) makes the path
look fuzzy and jagged. A hand's tremor is smoother: each offset is
close to the one before. So the noise is passed through a simple
low-pass filter (an exponential moving average):

    smooth[i] = smoothing · smooth[i-1] + (1 - smoothing) · noise[i]

`smoothing` = 0 gives plain noise; 0.7-0.9 gives a slow, tremor-like
drift. The wobble is also *tapered* by sin(π·i/(n-1)): zero at the
start and at the end, largest mid-way, so the path still begins and
lands exactly where it should.
"""

from __future__ import annotations

import math
import random


def micro_jitter(count: int, amplitude: float, smoothing: float, rng: random.Random) -> list[tuple[float, float]]:
    """`count` (dx, dy) offsets in pixels. `amplitude` is the standard
    deviation of the raw noise; smoothing reduces the spread, so it's
    scaled back up to keep `amplitude` meaningful."""
    if not 0 <= smoothing < 1:
        raise ValueError("smoothing must be in [0, 1)")
    if count <= 0 or amplitude <= 0:
        return [(0.0, 0.0)] * max(count, 0)
    # An EMA with factor s shrinks white noise's spread by sqrt((1-s)/(1+s)).
    gain = math.sqrt((1 + smoothing) / (1 - smoothing))
    sx = sy = 0.0
    offsets = []
    for i in range(count):
        sx = smoothing * sx + (1 - smoothing) * rng.gauss(0, amplitude)
        sy = smoothing * sy + (1 - smoothing) * rng.gauss(0, amplitude)
        taper = math.sin(math.pi * i / (count - 1)) if count > 1 else 0.0
        offsets.append((sx * gain * taper, sy * gain * taper))
    return offsets
