"""Measure a generated path: the pure part of the path lab.

Every function takes a start point and a `Path` (or many) and returns
numbers; nothing draws or moves anything. What each number answers:

    curved?      deviation_px: how far the path bows off the straight line
                 straightness: path length / straight distance (1.0 = straight)
    distorted?   wobble_px: how much the path wiggles around its own smooth shape
                 overshoot_px: how far it went past the target before correcting
    continuous?  max_step_px: the biggest single jump between two cursor positions
                 max_gap_ms: the longest pause between two positions
    speed shape  peak_at: when the top speed happens (0 = start, 1 = end);
                 human reaching movements peak somewhere in the middle
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from natural_mouse import Path, Point


@dataclass(frozen=True)
class PathStats:
    duration_s: float
    straightness: float
    deviation_px: float
    wobble_px: float
    overshoot_px: float
    max_step_px: float
    max_gap_ms: float
    peak_at: float


def positions(start: Point, path: Path) -> list[tuple[float, float]]:
    return [(start.x, start.y)] + [(p.x, p.y) for p in path]


def speeds(start: Point, path: Path) -> list[tuple[float, float]]:
    """(time from start in s, speed in px/s) for each step."""
    out, t = [], 0.0
    prev = (start.x, start.y)
    for p in path:
        t += p.delay
        step = math.dist(prev, (p.x, p.y))
        out.append((t, step / p.delay if p.delay > 0 else 0.0))
        prev = (p.x, p.y)
    return out


def measure(start: Point, end: Point, path: Path) -> PathStats:
    pts = positions(start, path)
    dx, dy = end.x - start.x, end.y - start.y
    dist = math.hypot(dx, dy) or 1.0
    ux, uy = dx / dist, dy / dist                       # unit vector along the line

    def along(p):  # distance travelled along the line
        return (p[0] - start.x) * ux + (p[1] - start.y) * uy

    def across(p):  # distance off the line (signed)
        return -(p[0] - start.x) * uy + (p[1] - start.y) * ux

    steps = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    # Wobble: how far each point is from the average of its neighbours
    # (a smooth curve is close to that average; jitter isn't).
    wobble = [math.dist(b, ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)) for a, b, c in zip(pts, pts[1:], pts[2:])]
    speed = speeds(start, path)
    duration = sum(p.delay for p in path)
    peak_t = max(speed, key=lambda s: s[1])[0] if speed else 0.0
    return PathStats(
        duration_s=duration,
        straightness=sum(steps) / dist,
        deviation_px=max(abs(across(p)) for p in pts),
        wobble_px=statistics.mean(wobble) if wobble else 0.0,
        overshoot_px=max(0.0, max(along(p) for p in pts) - dist),
        max_step_px=max(steps) if steps else 0.0,
        max_gap_ms=max((p.delay for p in path), default=0.0) * 1000,
        peak_at=peak_t / duration if duration else 0.0,
    )


@dataclass(frozen=True)
class Summary:
    """Averages over many runs of one variant."""

    runs: int
    duration_s: float
    straightness: float
    deviation_px: float
    wobble_px: float
    overshoot_rate: float     # share of runs that went past the target
    max_step_px: float        # worst case over all runs
    max_gap_ms: float         # worst case over all runs
    peak_at: float


def summarize(stats: list[PathStats]) -> Summary:
    def mean(name):
        return statistics.mean(getattr(s, name) for s in stats)

    return Summary(
        runs=len(stats),
        duration_s=mean("duration_s"),
        straightness=mean("straightness"),
        deviation_px=mean("deviation_px"),
        wobble_px=mean("wobble_px"),
        overshoot_rate=sum(s.overshoot_px > 0.5 for s in stats) / len(stats),
        max_step_px=max(s.max_step_px for s in stats),
        max_gap_ms=max(s.max_gap_ms for s in stats),
        peak_at=mean("peak_at"),
    )
