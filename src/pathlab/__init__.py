"""The path lab: generate, measure, and draw movement variants side by
side, without moving the real mouse. `python src/main.py pathlab`.
Like gui/ and testbench/, an application built on the library, not
part of the installed package. See docs/MOVEMENT.md (section 8)."""

from .lab import VARIANTS, compare, run
from .stats import PathStats, Summary, measure, summarize

__all__ = ["VARIANTS", "compare", "run", "PathStats", "Summary", "measure", "summarize"]
