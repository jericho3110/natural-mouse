"""Concrete ScreenLocator that finds solid blocks of one colour on screen.

Where `TemplateMatchLocator` needs a screenshot crop of the element (which
stops matching when the zoom level, theme, or DPI scaling changes), this
locator only needs a colour like ``"#ff00ff"``. A solid rectangle of that
colour is found at any size, which makes it a good fit for pages you
control (the test bench page uses it) and a poor fit for arbitrary apps,
where the same colour may appear in many places.

`confidence` here means *fill ratio*: how much of the block's bounding box
is actually that colour. A clean solid rectangle scores about 1.0; a few
scattered pixels of the colour score low and are ignored.
"""

from __future__ import annotations

import re
from typing import Callable

import cv2
import numpy as np

from ..screen import grab_screen
from .base import Match, ScreenLocator

_HEX_COLOUR = re.compile(r"^#?([0-9a-fA-F]{6})$")

Grab = Callable[[tuple[int, int, int, int] | None], np.ndarray]


def parse_hex_colour(text: str) -> tuple[int, int, int]:
    """``"#ff8800"`` -> ``(0, 136, 255)``: BGR order, which is what OpenCV
    images use. Raises ValueError for anything that isn't 6 hex digits."""
    found = _HEX_COLOUR.match(text.strip())
    if found is None:
        raise ValueError(f"Expected a colour like '#ff00ff', got {text!r}")
    digits = found.group(1)
    r, g, b = (int(digits[i:i + 2], 16) for i in (0, 2, 4))
    return b, g, r


class ColorLocator(ScreenLocator):
    """Finds solid-colour blocks. `query` is a hex colour string.

    `grab` is injected (it defaults to the real screen) so tests can hand
    in a synthetic image instead of reading the screen.
    """

    def __init__(self, tolerance: int = 12, min_area: int = 100, grab: Grab = grab_screen):
        self._tolerance = tolerance
        self._min_area = min_area
        self._grab = grab

    def locate(
        self,
        query: str,
        region: tuple[int, int, int, int] | None = None,
        confidence: float = 0.85,
    ) -> Match | None:
        """The largest block of that colour, or None."""
        matches = self.locate_all(query, region, confidence)
        return matches[0] if matches else None

    def locate_all(
        self,
        query: str,
        region: tuple[int, int, int, int] | None = None,
        confidence: float = 0.85,
    ) -> list[Match]:
        """Every block of that colour, largest first."""
        bgr = np.array(parse_hex_colour(query), dtype=np.int16)
        lower = np.clip(bgr - self._tolerance, 0, 255).astype(np.uint8)
        upper = np.clip(bgr + self._tolerance, 0, 255).astype(np.uint8)

        screen = self._grab(region)
        mask = cv2.inRange(screen, lower, upper)
        count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

        offset_x, offset_y = (region[0], region[1]) if region else (0, 0)
        matches: list[Match] = []
        for label in range(1, count):  # label 0 is the background
            x, y, w, h, area = (int(v) for v in stats[label])
            if area < self._min_area:
                continue
            fill = area / (w * h)
            if fill >= confidence:
                matches.append(Match(x + offset_x, y + offset_y, w, h, fill))
        matches.sort(key=lambda m: m.width * m.height, reverse=True)
        return matches
