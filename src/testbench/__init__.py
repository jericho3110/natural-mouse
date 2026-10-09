"""A live test bench for natural_mouse.

Opens a local test page in your browser, drives the real mouse over it
with natural_mouse (click, scroll, scroll-until-visible, click) and
reports what the browser actually received. Run it with
``python src/main.py testbench``; see docs/TESTBENCH.md.

Like gui/, this is an application built on the library, not part of the
installed package.
"""

from .bench import BenchConfig, run_bench
from .server import BenchServer

__all__ = ["BenchConfig", "BenchServer", "run_bench"]
