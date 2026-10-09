"""Saves what the screen looked like whenever a template isn't found.

When a click silently misses, the usual question is "what was actually on
screen?" — this answers it. Compare the saved image with the template to
see whether the layout changed, the theme changed, or the element simply
wasn't visible.
"""

from __future__ import annotations

import re
import time
from pathlib import Path as FsPath

import cv2

from ..screen import grab_screen
from .base import ActionContext, Plugin


class ScreenshotOnMissPlugin(Plugin):
    def __init__(self, directory: str = "misses"):
        super().__init__()
        self.directory = FsPath(directory)
        self.saved: list[FsPath] = []

    def after_locate(self, ctx: ActionContext) -> None:
        if ctx.match is not None:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{time.strftime('%Y%m%d-%H%M%S')}_{safe_stem(ctx.query)}.png"
        if not cv2.imwrite(str(path), grab_screen(ctx.region)):   # imwrite returns False instead of raising
            raise OSError(f"couldn't save the miss screenshot to {path}")
        ctx.extras["miss_screenshot"] = path
        self.saved.append(path)


def safe_stem(query: str | None, limit: int = 60) -> str:
    """A file-name-safe version of the query, e.g. 'templates/Save button.png'
    -> 'Save_button', '#ff00ff' -> 'ff00ff'. Only letters, digits, '-' and
    '_' survive, so the name can't contain a folder, a drive, or a
    character Windows refuses (: * ? " < > |), and it's never empty."""
    stem = FsPath(query or "").stem
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")[:limit]
    return cleaned or "query"
