"""Makes `natural_mouse`/`gui` importable from the tests without needing
the package installed or a PYTHONPATH set manually.

The project uses a "src layout" — main.py, natural_mouse/, and gui/ live
under src/, separate from tests/ and docs/. Running a script directly
(`python src/main.py`) puts src/ on sys.path automatically, since Python
always adds the directory containing the script being run. Running the
test suite (`python -m unittest discover tests`) has no such script to
anchor to, so this package's __init__ does the equivalent by hand, once,
before any test module tries to import natural_mouse or gui.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
