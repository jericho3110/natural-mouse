"""The shape of a movement: Bézier curves and their control points.

A Bézier curve runs from a start point to an end point and is *pulled
towards* (not through) its control points. `t` goes from 0 (start) to
1 (end):

    quadratic, 1 control point:   B(t) = (1-t)²·P0 + 2(1-t)t·P1 + t²·P2
    cubic,    2 control points:   B(t) = (1-t)³·P0 + 3(1-t)²t·P1 + 3(1-t)t²·P2 + t³·P3

A quadratic curve can only bow one way, in a single arc. A cubic can
also lean early or late, or make a gentle S, which gives more varied
paths. Everything here is a pure function (an `rng` is passed in), so
it's easy to test and plot.
"""

from __future__ import annotations

import random

from ..geometry import Point

CURVES = ("quadratic", "cubic")


def quadratic(p0: Point, p1: Point, p2: Point, t: float) -> tuple[float, float]:
    u = 1 - t
    return (u * u * p0.x + 2 * u * t * p1.x + t * t * p2.x,
            u * u * p0.y + 2 * u * t * p1.y + t * t * p2.y)


def cubic(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> tuple[float, float]:
    u = 1 - t
    a, b, c, d = u ** 3, 3 * u * u * t, 3 * u * t * t, t ** 3
    return (a * p0.x + b * p1.x + c * p2.x + d * p3.x,
            a * p0.y + b * p1.y + c * p2.y + d * p3.y)


def control_points(start: Point, end: Point, count: int, curviness: float, rng: random.Random) -> list[Point]:
    """`count` (1 or 2) control points, pushed sideways off the straight
    line by up to `curviness` x the distance.

    For a cubic curve the two points sit near 1/3 and 2/3 of the way and
    usually bow to the same side (one smooth arc); about one time in
    five they bow to opposite sides (a gentle S)."""
    if count not in (1, 2):
        raise ValueError("count must be 1 (quadratic) or 2 (cubic)")
    dist = start.distance_to(end) or 1.0
    dx, dy = end.x - start.x, end.y - start.y
    perp = (-dy / dist, dx / dist)               # unit vector at right angles to the line

    def at(fraction: float, bow: float) -> Point:
        return Point(start.x + dx * fraction + perp[0] * bow, start.y + dy * fraction + perp[1] * bow)

    if count == 1:
        return [at(0.5, dist * curviness * rng.uniform(-1, 1))]
    side = rng.choice((-1, 1))
    first = dist * curviness * rng.uniform(0.3, 1.0) * side
    second_side = -side if rng.random() < 0.2 else side
    second = dist * curviness * rng.uniform(0.3, 1.0) * second_side
    return [at(rng.uniform(0.2, 0.45), first), at(rng.uniform(0.55, 0.8), second)]


def point_on(curve: str, start: Point, controls: list[Point], end: Point, t: float) -> tuple[float, float]:
    if curve == "quadratic":
        return quadratic(start, controls[0], end, t)
    if curve == "cubic":
        return cubic(start, controls[0], controls[1], end, t)
    raise ValueError(f"unknown curve {curve!r}; use one of {CURVES}")
