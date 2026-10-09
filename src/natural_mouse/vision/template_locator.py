"""Concrete ScreenLocator that finds a reference image on screen via OpenCV
template matching against a live screenshot."""

from __future__ import annotations

import cv2
import numpy as np

from ..screen import grab_screen
from .base import Match, ScreenLocator


class TemplateMatchLocator(ScreenLocator):
    """Encapsulates screen capture (mss) and template matching (OpenCV)
    behind the ScreenLocator interface."""

    def locate(
        self,
        query: str,
        region: tuple[int, int, int, int] | None = None,
        confidence: float = 0.85,
    ) -> Match | None:
        template = self._load_template(query)
        screen = grab_screen(region)
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < confidence:
            return None

        h, w = template.shape[:2]
        offset_x, offset_y = (region[0], region[1]) if region else (0, 0)
        return Match(
            x=max_loc[0] + offset_x,
            y=max_loc[1] + offset_y,
            width=w,
            height=h,
            confidence=float(max_val),
        )

    def locate_all(
        self,
        query: str,
        region: tuple[int, int, int, int] | None = None,
        confidence: float = 0.85,
    ) -> list[Match]:
        template = self._load_template(query)
        screen = grab_screen(region)
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        h, w = template.shape[:2]
        offset_x, offset_y = (region[0], region[1]) if region else (0, 0)

        locations = np.where(result >= confidence)
        matches: list[Match] = []
        for pt_y, pt_x in zip(*locations):
            candidate = Match(int(pt_x + offset_x), int(pt_y + offset_y), w, h, float(result[pt_y, pt_x]))
            if not any(
                abs(candidate.x - m.x) < w // 2 and abs(candidate.y - m.y) < h // 2
                for m in matches
            ):
                matches.append(candidate)
        return matches

    @staticmethod
    def _load_template(template_path: str) -> np.ndarray:
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            raise FileNotFoundError(f"Could not load template image: {template_path}")
        return template
