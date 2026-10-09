"""Abstraction layer for locating a UI element on screen.

`ScreenLocator` is the contract: given some implementation-specific
`query` (an image path for pixel matching, an OCR search string, ...),
return where that element currently is on screen. `TemplateMatchLocator`
(OpenCV template matching) is the concrete strategy shipped today; a
different locator could implement the same interface and return the same
`Match` type without `UIAutomator` needing to know which one it's talking
to.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..geometry import Point


@dataclass(frozen=True)
class Match:
    """A located element's bounding box plus how confident the locator was.
    Encapsulates the "pick a believable click point inside me" logic so
    callers never poke at raw box coordinates themselves."""

    x: int
    y: int
    width: int
    height: int
    confidence: float

    @property
    def center(self) -> Point:
        return Point(self.x + self.width / 2, self.y + self.height / 2)

    def random_point(self, center_bias: float = 0.6) -> Point:
        """A point inside the box, weighted toward the center rather than
        always the exact centroid or a uniform random spot."""
        half_w, half_h = self.width / 2, self.height / 2
        spread = 1 - center_bias
        cx, cy = self.center.x, self.center.y
        x = cx + max(-half_w, min(half_w, random.gauss(0, half_w * spread)))
        y = cy + max(-half_h, min(half_h, random.gauss(0, half_h * spread)))
        return Point(x, y)


class ScreenLocator(ABC):
    """Abstract strategy for finding an element on screen.

    `query` means something different per implementation (a template image
    path, a CSS selector, ...) but every implementation returns the same
    `Match` value object, which is what keeps them interchangeable.
    """

    @abstractmethod
    def locate(
        self,
        query: str,
        region: tuple[int, int, int, int] | None,
        confidence: float,
    ) -> Match | None:
        raise NotImplementedError

    @abstractmethod
    def locate_all(
        self,
        query: str,
        region: tuple[int, int, int, int] | None,
        confidence: float,
    ) -> list[Match]:
        raise NotImplementedError
