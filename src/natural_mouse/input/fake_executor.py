"""Concrete InputExecutor that records calls instead of touching the real
cursor — lets UIAutomator's orchestration logic be tested without
hijacking the mouse."""

from __future__ import annotations

from ..geometry import Point
from ..path.base import PathGenerator
from .base import InputExecutor


class FakeInputExecutor(InputExecutor):
    """Records every call it receives in `self.calls` and tracks a fake
    cursor position, without ever touching the real OS cursor."""

    def __init__(self, start_position: Point = Point(0, 0)):
        self._position = start_position
        self.calls: list[tuple] = []

    def get_cursor_position(self) -> Point:
        return self._position

    def move_to(self, target: Point, path_generator: PathGenerator) -> None:
        self.calls.append(("move_to", target))
        self._position = target

    def click(
        self,
        target: Point | None = None,
        path_generator: PathGenerator | None = None,
        hold_range: tuple[float, float] = (0.06, 0.16),
    ) -> None:
        if target is not None:
            self._position = target
        self.calls.append(("click", target))

    def scroll(
        self,
        amount: int,
        steps: int = 5,
        step_delay_range: tuple[float, float] = (0.05, 0.18),
    ) -> None:
        self.calls.append(("scroll", amount))
