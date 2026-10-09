"""Abstraction layer for path generation.

`PathGenerator` is the abstract contract: something that turns a start and
end point into a `Path`. `BezierPathGenerator` (in bezier.py) is the one
concrete strategy shipped today, but any class that implements `generate`
can be swapped in wherever a `PathGenerator` is expected (e.g. a simpler
linear generator for testing) without touching the code that consumes it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..geometry import Point


@dataclass(frozen=True)
class PathPoint:
    """A single stop along a path: a position plus the delay before moving
    there (encapsulates the two together so they can't drift apart)."""

    x: float
    y: float
    delay: float

    @property
    def point(self) -> Point:
        return Point(self.x, self.y)


class Path:
    """An ordered, immutable sequence of PathPoints with convenience
    accessors. Consumers iterate over it; they never touch the underlying
    list directly."""

    def __init__(self, points: list[PathPoint]):
        if not points:
            raise ValueError("A Path requires at least one point.")
        self._points = tuple(points)

    def __iter__(self):
        return iter(self._points)

    def __len__(self) -> int:
        return len(self._points)

    @property
    def end(self) -> Point:
        return self._points[-1].point

    @property
    def total_duration(self) -> float:
        return sum(p.delay for p in self._points)


class PathGenerator(ABC):
    """Abstract strategy: produce a Path between two points."""

    @abstractmethod
    def generate(self, start: Point, end: Point) -> Path:
        """Return a Path from `start` to `end`."""
        raise NotImplementedError
