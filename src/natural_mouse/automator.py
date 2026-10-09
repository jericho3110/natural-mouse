"""The orchestrator: composes a locator, an executor, and a path generator
to answer one question — "find this element and click it naturally."

`UIAutomator` depends only on the three abstract interfaces
(`ScreenLocator`, `InputExecutor`, `PathGenerator`), never on a concrete
implementation. This is dependency injection / the strategy pattern: any
combination of concrete strategies can be handed to it (e.g. swapping
`Win32InputExecutor` for a future `MacInputExecutor`) and `UIAutomator`
itself never has to change.
"""

from __future__ import annotations

from .geometry import Point
from .input.base import InputExecutor
from .path.base import PathGenerator
from .vision.base import ScreenLocator


class UIAutomator:
    def __init__(
        self,
        locator: ScreenLocator,
        executor: InputExecutor,
        path_generator: PathGenerator,
        click_hold_range: tuple[float, float] = (0.06, 0.16),
    ):
        self._locator = locator
        self._executor = executor
        self._path_generator = path_generator
        self._click_hold_range = click_hold_range

    def find_and_click(
        self,
        query: str,
        region: tuple[int, int, int, int] | None = None,
        confidence: float = 0.85,
        center_bias: float = 0.6,
    ) -> bool:
        """Locate `query` on screen and click a natural point inside it.
        Returns True if a match was found and clicked."""
        match = self._locator.locate(query, region, confidence)
        if match is None:
            return False

        target = match.random_point(center_bias)
        self._executor.click(target, self._path_generator, self._click_hold_range)
        return True

    def locate(
        self,
        query: str,
        region: tuple[int, int, int, int] | None = None,
        confidence: float = 0.85,
    ):
        """Expose a raw locate for callers that want the match without
        clicking (e.g. to just check whether something is on screen)."""
        return self._locator.locate(query, region, confidence)

    def scroll(
        self,
        amount: int,
        steps: int = 5,
        step_delay_range: tuple[float, float] = (0.05, 0.18),
        at: Point | None = None,
    ) -> None:
        """Scroll the mouse wheel (positive = up, negative = down).

        Windows delivers wheel events to whatever is under the cursor, not
        to whatever window you have in mind, so if `at` is given the
        cursor is moved there first (naturally, via the same path
        generator used for clicks) before scrolling. Without `at`, this
        scrolls wherever the cursor already happens to be.
        """
        if at is not None:
            self._executor.move_to(at, self._path_generator)
        self._executor.scroll(amount, steps, step_delay_range)
