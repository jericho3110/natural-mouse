"""Shared screen-capture helper.

Both `TemplateMatchLocator` (matching against a live screenshot) and
`capture_region` (saving a fresh template crop) need to grab pixels off
the screen the same way, so that logic lives here once instead of being
duplicated or reached into as a private method of an unrelated class.
"""

from __future__ import annotations

import cv2
import mss
import numpy as np


def grab_screen(region: tuple[int, int, int, int] | None = None) -> np.ndarray:
    """Capture the screen (or `region` = (left, top, width, height)) as a
    BGR numpy array, the format OpenCV expects."""
    with mss.mss() as sct:
        monitor = sct.monitors[0] if region is None else {
            "left": region[0], "top": region[1], "width": region[2], "height": region[3],
        }
        raw = np.array(sct.grab(monitor))
    return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
