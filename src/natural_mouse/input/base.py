"""Abstraction layer for driving the OS cursor.

`InputExecutor` is the contract the rest of the package programs against.
`Win32InputExecutor` is the only concrete implementation today, but the
interface is OS-agnostic on purpose: a future `MacInputExecutor` or a
`FakeInputExecutor` for tests could implement the same three methods and
drop in anywhere an `InputExecutor` is expected.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..geometry import Point
from ..path.base import PathGenerator


class InputExecutor(ABC):
    """Abstract strategy for moving the cursor and clicking."""

    @abstractmethod
    def get_cursor_position(self) -> Point:
        raise NotImplementedError

    @abstractmethod
    def move_to(self, target: Point, path_generator: PathGenerator) -> None:
        """Move the cursor from its current position to `target`, following
        the path produced by `path_generator`."""
        raise NotImplementedError

    @abstractmethod
    def click(
        self,
        target: Point | None,
        path_generator: PathGenerator,
        hold_range: tuple[float, float],
    ) -> None:
        """Optionally move to `target`, then perform a click held for a
        randomized duration within `hold_range`."""
        raise NotImplementedError

    @abstractmethod
    def scroll(self, amount: int, steps: int, step_delay_range: tuple[float, float]) -> None:
        """Scroll the mouse wheel. `amount` is the total number of wheel
        notches (positive = up, negative = down), split into `steps`
        individual wheel events with randomized delays between them so a
        scroll reads as several small nudges rather than one instant jump."""
        raise NotImplementedError
