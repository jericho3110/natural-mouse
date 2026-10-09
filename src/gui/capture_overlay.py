"""Full-screen click-and-drag region selector.

Shows a translucent overlay covering the screen; the user drags a
rectangle over the element they want, and the selected region (in screen
pixel coordinates, the same convention `capture_region`/`ScreenLocator`
already use) is reported back via a callback. The overlay always closes
itself (drag-complete or Escape-to-cancel) before the callback fires, and
with a short delay, so the overlay's own translucent tint is never present
in a screenshot taken as a result of the capture.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

RegionCallback = Callable[[tuple[int, int, int, int] | None], None]

_MIN_SELECTION_PX = 5
_SCREENSHOT_SETTLE_MS = 150


class CaptureOverlay:
    """Pops up a full-screen overlay for one region selection, then tears
    itself down and reports the result through `on_region`."""

    def __init__(self, parent: tk.Misc, on_region: RegionCallback):
        self._parent = parent
        self._on_region = on_region
        self._start: tuple[int, int] | None = None
        self._rect_id: int | None = None

        screen_w = parent.winfo_screenwidth()
        screen_h = parent.winfo_screenheight()

        self._window = tk.Toplevel(parent)
        self._window.geometry(f"{screen_w}x{screen_h}+0+0")
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._window.attributes("-alpha", 0.3)
        self._window.configure(bg="gray")
        self._window.config(cursor="cross")

        self._canvas = tk.Canvas(self._window, bg="gray", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)

        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._window.bind("<Escape>", self._on_cancel)
        self._window.focus_force()

    def _on_press(self, event: tk.Event) -> None:
        self._start = (event.x, event.y)
        self._rect_id = self._canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline="red", width=2
        )

    def _on_drag(self, event: tk.Event) -> None:
        if self._start is None or self._rect_id is None:
            return
        start_x, start_y = self._start
        self._canvas.coords(self._rect_id, start_x, start_y, event.x, event.y)

    def _on_release(self, event: tk.Event) -> None:
        if self._start is None:
            self._finish(None)
            return

        start_x, start_y = self._start
        left, top = min(start_x, event.x), min(start_y, event.y)
        width, height = abs(event.x - start_x), abs(event.y - start_y)

        if width < _MIN_SELECTION_PX or height < _MIN_SELECTION_PX:
            self._finish(None)
            return

        self._finish((int(left), int(top), int(width), int(height)))

    def _on_cancel(self, _event: tk.Event) -> None:
        self._finish(None)

    def _finish(self, region: tuple[int, int, int, int] | None) -> None:
        self._window.destroy()
        # Give the OS a moment to actually remove the overlay's pixels
        # before any screenshot is taken as a result of this callback.
        self._parent.after(_SCREENSHOT_SETTLE_MS, lambda: self._on_region(region))
