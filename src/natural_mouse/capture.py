"""Save a fresh screenshot crop as a template image.

Pixel template matching (`natural_mouse/vision/template_locator.py`) only
works while the screen still looks like the saved crop, so refreshing a
stale template needs to be quick. This is that one step: grab a region of
the screen right now and save it, instead of taking a full screenshot and
cropping it by hand in an image editor.
"""

from __future__ import annotations

import cv2

from .screen import grab_screen


def capture_region(region: tuple[int, int, int, int], output_path: str) -> None:
    """Grab `region` = (left, top, width, height) off the screen right now
    and save it to `output_path`."""
    image = grab_screen(region)
    cv2.imwrite(output_path, image)
