# Glossary

Every concept this project uses, in one table, with where it's
explained and where it's used. Alphabetical.

| Term | Meaning | Explained in | Used in |
| --- | --- | --- | --- |
| Abstract base class (ABC) | a class that only declares methods; subclasses must implement them | [ARCHITECTURE.md](ARCHITECTURE.md) | `input/base.py`, `path/base.py`, `vision/base.py` |
| Anti-aliasing | smoothing a drawn line's edges by blending pixels | [MOVEMENT.md §8.1](MOVEMENT.md#81-how-pathlabpng-is-made) | `pathlab/render.py` (`LINE_AA`) |
| Alpha blending | mixing two images by weights (here 35% / 65%) to draw see-through lines | [MOVEMENT.md §8.1](MOVEMENT.md#81-how-pathlabpng-is-made) | `pathlab/render.py` (`addWeighted`) |
| Bézier curve (quadratic, cubic) | a smooth curve from start to end pulled towards 1 or 2 control points | [MOVEMENT.md §2](MOVEMENT.md#2-shape-bézier-curves) | `path/curves.py` |
| Bell-shaped speed | accelerate, peak mid-way, decelerate: how reaching movements look | [MOVEMENT.md §3](MOVEMENT.md#3-speed-easing) | `path/easing.py` |
| Check gate | one command whose exit code decides if a commit is allowed | [SECURITY.md](SECURITY.md), [README](../README.md) | `scripts/check.py` |
| Composition root | the one place concrete classes are chosen and wired together | [ARCHITECTURE.md](ARCHITECTURE.md) | `main.py` |
| Constant-time comparison | comparing secrets so the time taken doesn't leak how much matched | [TESTBENCH.md §6](TESTBENCH.md#6-security) | `testbench/server.py` (`hmac.compare_digest`) |
| Continuous movement | many small moves with short gaps, no jumps | [MOVEMENT.md §7](MOVEMENT.md#7-is-it-curved-distorted-and-continuous) | `input/win32_executor.py` |
| Control point | a point a Bézier curve is pulled towards (not through) | [MOVEMENT.md §2](MOVEMENT.md#2-shape-bézier-curves) | `path/curves.py` (`control_points`) |
| Decorator (pattern) | a wrapper with the same interface that adds behaviour | [EXTENSIONS_AND_PLUGINS.md](EXTENSIONS_AND_PLUGINS.md) | `extensions/*` |
| Dependency injection | handing a class its collaborators instead of it creating them | [ARCHITECTURE.md](ARCHITECTURE.md) | `UIAutomator(locator, executor, path_generator)`, `BezierPathGenerator(profile, rng)` |
| DNS rebinding | a website re-pointing its name at 127.0.0.1 to reach local servers | [TESTBENCH.md §6](TESTBENCH.md#6-security) | `testbench/server.py` (Host check) |
| DPI awareness | telling Windows the program handles display scaling, so coordinates are real pixels | [TESTBENCH.md §7](TESTBENCH.md#7-found-live) | `input/win32_executor.py` |
| Easing function | maps time (0..1) to progress (0..1), which sets speed over time | [MOVEMENT.md §3](MOVEMENT.md#3-speed-easing) | `path/easing.py` |
| Entry point (plugin) | a name in `pyproject.toml` that lets other packages advertise plugins | [EXTENSIONS_AND_PLUGINS.md](EXTENSIONS_AND_PLUGINS.md) | `plugins/manager.py`, `pyproject.toml` |
| Exponential moving average (EMA) | a low-pass filter: each value mostly keeps the previous one | [MOVEMENT.md §4](MOVEMENT.md#4-wobble-micro-jitter) | `path/jitter.py` |
| Fail-safe | stop at once when the user moves the mouse | [EXTENSIONS_AND_PLUGINS.md](EXTENSIONS_AND_PLUGINS.md) | `extensions/executors.py` |
| Fill ratio | share of a block's bounding box that is the searched colour | [TESTBENCH.md §4](TESTBENCH.md#4-how-its-built) | `vision/color_locator.py` |
| Fitts's law | movement time = a + b·log2(D/W + 1) | [MOVEMENT.md §5](MOVEMENT.md#5-duration-fittss-law) | `path/fitts.py` |
| Frozen dataclass | an immutable value object | [LIBRARIES_AND_BUILTINS.md §3](LIBRARIES_AND_BUILTINS.md#3-standard-library-modules) | `Point`, `FittsLaw`, `Match` |
| Functional core, imperative shell | pure logic in the middle, I/O at the edges | [TESTBENCH.md §4](TESTBENCH.md#4-how-its-built) | `pathlab/stats.py`, `testbench/report.py` |
| Hook | a method a plugin overrides to run at a point in an action | [EXTENSIONS_AND_PLUGINS.md](EXTENSIONS_AND_PLUGINS.md) | `plugins/base.py` |
| Index of difficulty (ID) | log2(D/W + 1), in bits | [MOVEMENT.md §5](MOVEMENT.md#5-duration-fittss-law) | `path/fitts.py` |
| Import cycle | two modules importing each other, directly or via others | [LIBRARIES_AND_BUILTINS.md §7](LIBRARIES_AND_BUILTINS.md#7-language-features-worth-knowing) | `geometry.py` (`TYPE_CHECKING`) |
| Logistic function (S-curve) | 1/(1 + e^(−k(t − 0.5))): slow, fast, slow | [MOVEMENT.md §3](MOVEMENT.md#3-speed-easing) | `path/easing.py` |
| Micro-jitter / tremor | small, smooth wobble added along a path | [MOVEMENT.md §4](MOVEMENT.md#4-wobble-micro-jitter) | `path/jitter.py` |
| Overshoot and correction | going slightly past the target, then back | [MOVEMENT.md §6](MOVEMENT.md#6-overshoot-and-correction) | `path/bezier.py` |
| Path lab | compares movement variants as a table and a picture | [MOVEMENT.md §8](MOVEMENT.md#8-the-path-lab) | `pathlab/` |
| Plugin | an object with hooks around every action | [EXTENSIONS_AND_PLUGINS.md](EXTENSIONS_AND_PLUGINS.md) | `plugins/` |
| Pure function | output depends only on input; no I/O, no hidden state | [MOVEMENT.md §10](MOVEMENT.md#10-design-decisions) | `curves.py`, `easing.py`, `jitter.py`, `fitts.py`, `pathlab/stats.py` |
| Relative import | `from ..geometry import Point`: import by position in the package | [LIBRARIES_AND_BUILTINS.md §7](LIBRARIES_AND_BUILTINS.md#7-language-features-worth-knowing) | everything in `natural_mouse/` |
| Reproducibility (seed) | the same seed gives the same "random" results | [MOVEMENT.md §1](MOVEMENT.md#1-quick-start) | `BezierPathGenerator(rng=...)`, `pathlab` |
| `SendInput` | the Windows function that synthesises mouse/keyboard input | [MOVEMENT.md §9](MOVEMENT.md#9-one-movement-end-to-end) | `input/win32_executor.py` |
| Strategy pattern | interchangeable implementations behind one interface | [ARCHITECTURE.md](ARCHITECTURE.md) | locators, executors, path generators |
| Taper | fading the jitter to zero at both ends with a sine | [MOVEMENT.md §4](MOVEMENT.md#4-wobble-micro-jitter) | `path/jitter.py` |
| Template matching | finding a small image inside a screenshot | [ARCHITECTURE.md](ARCHITECTURE.md) | `vision/template_locator.py` |
| Wobble (metric) | average distance of each position from the midpoint of its neighbours | [MOVEMENT.md §8.2](MOVEMENT.md#82-what-each-number-means) | `pathlab/stats.py` |

## References

- Definitions are checked against the files listed in the table; see
  each linked doc's own References for the sources behind each concept.
