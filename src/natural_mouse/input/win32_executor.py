"""Concrete InputExecutor that drives the cursor via the Win32 SendInput
API — the same API every legitimate Windows automation/RPA/testing tool
uses, rather than teleporting the cursor with SetCursorPos."""

from __future__ import annotations

import ctypes
import random
import time
from ctypes import wintypes

from ..geometry import Point
from ..path.base import PathGenerator
from .base import InputExecutor

_INPUT_MOUSE = 0
_MOUSEEVENTF_MOVE = 0x0001
_MOUSEEVENTF_ABSOLUTE = 0x8000
_MOUSEEVENTF_LEFTDOWN = 0x0002
_MOUSEEVENTF_LEFTUP = 0x0004
_MOUSEEVENTF_WHEEL = 0x0800
_WHEEL_DELTA = 120  # one notch, per the Win32 API
_PER_MONITOR_AWARE_V2 = -4  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 (a pseudo-handle)
_PROCESS_PER_MONITOR_DPI_AWARE = 2


def make_process_dpi_aware() -> None:
    """Make every coordinate in this process a real (physical) pixel.

    With display scaling above 100%, Windows hands a "DPI-unaware" process
    scaled coordinates (at 125%, a 1920x1080 screen reports as 1536x864),
    while screenshots from `mss` are always physical pixels. `mss` makes
    the process DPI-aware itself, but only on its first screenshot, so
    before that, cursor positions and screen size were in different units.
    Declaring it up front makes the units the same from the start.
    Found live with the test bench at 125% scaling (docs/TESTBENCH.md).

    Safe to call more than once: once awareness is set, Windows refuses
    to change it and the call simply returns False.
    """
    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(_PER_MONITOR_AWARE_V2)):
            return
    except AttributeError:  # Windows older than 10 1703
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(_PROCESS_PER_MONITOR_DPI_AWARE)
    except (AttributeError, OSError):  # Windows 7: no shcore
        user32.SetProcessDPIAware()


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class _INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [("mi", _MOUSEINPUT)]

    _anonymous_ = ("_i",)
    _fields_ = [("type", wintypes.DWORD), ("_i", _I)]


class Win32InputExecutor(InputExecutor):
    """Encapsulates all ctypes/SendInput plumbing behind the InputExecutor
    interface; callers never see a ctypes structure."""

    def __init__(self):
        make_process_dpi_aware()
        self._user32 = ctypes.windll.user32

    def get_cursor_position(self) -> Point:
        pt = wintypes.POINT()
        self._user32.GetCursorPos(ctypes.byref(pt))
        return Point(pt.x, pt.y)

    def move_to(self, target: Point, path_generator: PathGenerator) -> None:
        origin = self.get_cursor_position()
        path = path_generator.generate(origin, target)
        for path_point in path:
            self._send_absolute_move(round(path_point.x), round(path_point.y))
            time.sleep(path_point.delay)

    def click(
        self,
        target: Point | None = None,
        path_generator: PathGenerator | None = None,
        hold_range: tuple[float, float] = (0.06, 0.16),
    ) -> None:
        if target is not None:
            if path_generator is None:
                raise ValueError("path_generator is required when moving to a target.")
            self.move_to(target, path_generator)
        self._send_click(button_down=True)
        time.sleep(random.uniform(*hold_range))
        self._send_click(button_down=False)

    def scroll(
        self,
        amount: int,
        steps: int = 5,
        step_delay_range: tuple[float, float] = (0.05, 0.18),
    ) -> None:
        steps = max(1, min(steps, abs(amount)) or 1)
        notches = self._split_into_steps(amount, steps)
        for notch in notches:
            self._send_wheel(notch)
            time.sleep(random.uniform(*step_delay_range))

    @staticmethod
    def _split_into_steps(amount: int, steps: int) -> list[int]:
        """Split `amount` wheel notches into `steps` uneven chunks (humans
        don't scroll in perfectly equal increments) that still sum to
        `amount` exactly."""
        base = amount // steps
        remainder = amount - base * steps
        chunks = [base] * steps
        for i in range(abs(remainder)):
            chunks[i % steps] += 1 if remainder > 0 else -1
        random.shuffle(chunks)
        return [c for c in chunks if c != 0] or [amount]

    def _send_wheel(self, notches: int) -> None:
        # mouseData is a DWORD but Windows interprets it as a signed
        # multiple of WHEEL_DELTA; mask to its two's-complement bit
        # pattern since ctypes.DWORD rejects negative Python ints outright.
        delta = (notches * _WHEEL_DELTA) & 0xFFFFFFFF
        inp = _INPUT(type=_INPUT_MOUSE)
        inp.mi = _MOUSEINPUT(0, 0, delta, _MOUSEEVENTF_WHEEL, 0, None)
        self._user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))

    def _screen_size(self) -> tuple[int, int]:
        return self._user32.GetSystemMetrics(0), self._user32.GetSystemMetrics(1)

    def _send_absolute_move(self, x: int, y: int) -> None:
        width, height = self._screen_size()
        norm_x = int(x * 65535 / max(width - 1, 1))
        norm_y = int(y * 65535 / max(height - 1, 1))
        inp = _INPUT(type=_INPUT_MOUSE)
        inp.mi = _MOUSEINPUT(norm_x, norm_y, 0, _MOUSEEVENTF_MOVE | _MOUSEEVENTF_ABSOLUTE, 0, None)
        self._user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))

    def _send_click(self, button_down: bool) -> None:
        flag = _MOUSEEVENTF_LEFTDOWN if button_down else _MOUSEEVENTF_LEFTUP
        inp = _INPUT(type=_INPUT_MOUSE)
        inp.mi = _MOUSEINPUT(0, 0, 0, flag, 0, None)
        self._user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))
