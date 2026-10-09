# How a movement is made

`BezierPathGenerator` turns "from here to there" into a list of cursor
positions, each with a delay. Four independent building blocks decide
what that list looks like, plus overshoot. This guide explains each one,
shows how to pick them, and shows what the **path lab** measured.

## Contents

- [1. Quick start](#1-quick-start)
- [2. Shape: Bézier curves](#2-shape-bézier-curves)
- [3. Speed: easing](#3-speed-easing)
- [4. Wobble: micro-jitter](#4-wobble-micro-jitter)
- [5. Duration: Fitts's law](#5-duration-fittss-law)
- [6. Overshoot and correction](#6-overshoot-and-correction)
- [7. Is it curved, distorted, and continuous?](#7-is-it-curved-distorted-and-continuous)
- [8. The path lab](#8-the-path-lab)
  - [8.1 How `pathlab.png` is made](#81-how-pathlabpng-is-made)
  - [8.2 What each number means](#82-what-each-number-means)
- [9. One movement, end to end](#9-one-movement-end-to-end)
- [10. Design decisions](#10-design-decisions)
- [11. Exercises](#11-exercises)
- [References](#references)

## 1. Quick start

```python
from natural_mouse import BezierPathGenerator, FittsLaw, MovementProfile, UIAutomator, ColorLocator, Win32InputExecutor

profile = MovementProfile(
    curve="cubic",               # "quadratic" (default) or "cubic"
    easing="logistic",           # "linear", "cosine" (default) or "logistic"
    logistic_steepness=10,       # k: higher = gentler start, faster middle
    jitter_px=1.5,               # micro-jitter strength
    jitter_smoothing=0.85,       # 0 = plain noise (default); 0.7-0.9 = tremor-like
    fitts=FittsLaw(a=0.08, b=0.11),   # time moves by Fitts's law
    target_width_px=24,
)
automator = UIAutomator(ColorLocator(), Win32InputExecutor(), BezierPathGenerator(profile))
```

Every option has a default that reproduces the original behaviour, so
`MovementProfile()` alone still works as before.

| Option | Default | Module |
| --- | --- | --- |
| `curve` | `"quadratic"` | [path/curves.py](../src/natural_mouse/path/curves.py) |
| `curviness` | `0.35` | same |
| `easing`, `logistic_steepness` | `"cosine"`, `10.0` | [path/easing.py](../src/natural_mouse/path/easing.py) |
| `jitter_px`, `jitter_smoothing` | `1.2`, `0.0` | [path/jitter.py](../src/natural_mouse/path/jitter.py) |
| `fitts`, `target_width_px`, `fitts_variability` | `None`, `24`, `0.15` | [path/fitts.py](../src/natural_mouse/path/fitts.py) |
| `duration_range` | `(0.25, 0.55)` s | used when `fitts` is `None` |
| `overshoot_chance`, `overshoot_px` | `0.25`, `(4, 14)` | [path/bezier.py](../src/natural_mouse/path/bezier.py) |
| `steps_per_100px` | `18` | how many positions per 100 px |

`BezierPathGenerator(profile, rng=random.Random(7))` makes paths
repeatable, which the tests and the path lab rely on.

## 2. Shape: Bézier curves

A Bézier curve starts and ends at fixed points and is *pulled towards*
its control points, without passing through them. With `t` from 0 to 1:

```text
quadratic (1 control point):  B(t) = (1-t)²·P0 + 2(1-t)t·P1 + t²·P2
cubic    (2 control points):  B(t) = (1-t)³·P0 + 3(1-t)²t·P1 + 3(1-t)t²·P2 + t³·P3
```

- **Quadratic** gives one symmetric arc.
- **Cubic** has two control points, near 1/3 and 2/3 of the way. Usually
  they're on the same side (an arc that can lean early or late); about
  one time in five they're on opposite sides (a gentle S).
- Control points sit up to `curviness` x the distance off the straight
  line, in a random direction (`control_points`).

## 3. Speed: easing

The positions are spaced **equally in time**. An easing function maps
time (0..1) to progress along the curve (0..1), so where it's steep the
cursor moves fast:

| Easing | Formula | Speed over time |
| --- | --- | --- |
| `linear` | `t` | constant: instant start and stop (robotic) |
| `cosine` | `0.5 - 0.5·cos(πt)` | smooth bell, peak in the middle |
| `logistic` | `s(t) = 1/(1 + e^(-k(t-0.5)))`, rescaled to run exactly 0→1 | bell whose sharpness you set with `k` |

Reaching movements accelerate, peak, and decelerate into the target, a
bell-shaped speed profile. The logistic S-curve is the "logistic
transform for acceleration": low `k` is close to linear, high `k` means
a slower start and finish around a faster middle. `logistic(0.5) = 0.5`
for any `k`, so it's symmetric.

## 4. Wobble: micro-jitter

Raw random noise at every position makes a jagged, fuzzy line. Real
tremor is smoother: each offset is close to the previous one. So the
noise goes through an **exponential moving average** (a low-pass
filter):

```text
smooth[i] = s · smooth[i-1] + (1 - s) · noise[i]      s = jitter_smoothing
```

- Smoothing shrinks the noise's spread by `sqrt((1-s)/(1+s))`, so it's
  scaled back up. That way `jitter_px` keeps meaning "this strong".
- The offsets are **tapered** by `sin(π·i/(n-1))`: zero at the start
  and at the end, so the path still begins and lands exactly.

## 5. Duration: Fitts's law

```text
ID = log2(D / W + 1)       index of difficulty, bits   (D = distance, W = target width)
MT = a + b · ID            movement time, seconds
```

Long moves take longer, but only logarithmically. From
`python src/main.py pathlab` with the defaults `a=0.08`, `b=0.11`,
`W=24`:

| Distance px | ID bits | Time s |
| --- | --- | --- |
| 50 | 1.62 | 0.259 |
| 100 | 2.37 | 0.341 |
| 200 | 3.22 | 0.434 |
| 400 | 4.14 | 0.536 |
| 800 | 5.10 | 0.641 |
| 1600 | 6.08 | 0.749 |

A move 32x as far takes under 3x as long. `fitts_variability` adds
±15% spread so identical moves don't take identical times. Without
`fitts`, the duration is random in `duration_range`, the same for near
and far moves.

The older `FittsPathGenerator` ([EXTENSIONS_AND_PLUGINS.md](EXTENSIONS_AND_PLUGINS.md))
does the same as a wrapper that re-times *any* generator; the built-in
option is simpler when you use `BezierPathGenerator`.

## 6. Overshoot and correction

With probability `overshoot_chance` (for moves over 20 px), the curve
aims `overshoot_px` past the target along the direction of travel, then
a short, small correction curve goes back to it. The correction uses
the same curve and easing settings, with less jitter and no further
overshoot.

## 7. Is it curved, distorted, and continuous?

Yes. Measured by the path lab (25 paths per variant, a 760 px move,
seed 1):

| Variant | Time s | Bow px | Straightness | Wobble px | Overshoot | Max step px | Max gap ms | Peak at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| classic: quadratic + cosine | 0.37 | 68 | 1.050 | 1.18 | 20% | 14.0 | 18.4 | 0.48 |
| cubic + cosine | 0.43 | 116 | 1.094 | 1.16 | 24% | 14.1 | 22.1 | 0.47 |
| cubic + logistic (k=10) | 0.43 | 116 | 1.099 | 1.16 | 24% | 20.4 | 22.1 | 0.47 |
| cubic + logistic + tremor | 0.43 | 116 | 1.082 | 0.49 | 24% | 18.3 | 22.1 | 0.47 |
| cubic + logistic + tremor + Fitts | 0.66 | 116 | 1.082 | 0.49 | 24% | 18.3 | 22.1 | 0.48 |

- **Curved:** every variant bows off the straight line (68-116 px on
  average); cubic curves bow more and vary more.
- **Distorted:** "wobble" (distance from the average of neighbouring
  points) is about 1.2 px with plain noise. Tremor smoothing brings it
  to 0.5 px: still uneven, but no longer jagged, as the speed curves in
  the picture show. About a quarter of moves overshoot and correct.
- **Continuous:** the largest jump between two positions is 14-20 px,
  and the longest pause 22 ms, about one frame of a 60 Hz screen. The
  executor moves through every position with `SendInput`, so the cursor
  glides rather than teleporting.
- **Speed shape:** the top speed comes at 47-48% of the movement (a
  bell), never at the start.

![Path lab: paths and speed over time per variant](images/pathlab.png)

## 8. The path lab

```powershell
python src/main.py pathlab                                # table + pathlab.png
python src/main.py pathlab --runs 40 --seed 3 --out compare.png
```

| Option | Meaning |
| --- | --- |
| `--out FILE` | where to save the picture (default `pathlab.png`, gitignored) |
| `--runs N` | paths per variant (default 25) |
| `--seed S` | random seed: the same seed draws the same picture |

It never moves the mouse: it generates paths, measures them
([src/pathlab/stats.py](../src/pathlab/stats.py), pure functions) and
draws them with OpenCV ([render.py](../src/pathlab/render.py)). To try
an idea, add a `MovementProfile` to `VARIANTS` in
[lab.py](../src/pathlab/lab.py). To see how the *browser* receives a
movement, use the live test bench ([TESTBENCH.md](TESTBENCH.md)).

### 8.1 How `pathlab.png` is made

The picture in the README and above comes from the same command, in
four steps. Nothing touches the real mouse or screen.

```text
lab.run(out, runs=25, seed=1)
  1. generate   for each variant in VARIANTS (5 MovementProfiles):
                  rng = random.Random(seed)                  # same seed -> same paths
                  BezierPathGenerator(profile, rng).generate(START, END) x 25
                START = (150, 450), END = (850, 150): a 760 px move up and right
  2. measure    stats.measure(START, END, path) for every path -> PathStats
                stats.summarize(...) per variant -> Summary (averages, worst cases)
  3. print      lab.table(...) and lab.fitts_table()          # the console tables
  4. draw       render.save_comparison(results, START, END, out)
```

Step 4, the drawing, in `src/pathlab/render.py`:

| Step | OpenCV / NumPy call | Why |
| --- | --- | --- |
| A blank canvas | `np.full((height, width, 3), BG, np.uint8)` | an OpenCV image *is* a NumPy array of rows × columns × 3 colour channels (blue, green, red) |
| Fit every path in a panel | `_bounds(...)`, then one `scale` for all rows | the same scale everywhere, so the rows can be compared by eye |
| Draw each path | `cv2.polylines(overlay, [points], False, colour, 1, cv2.LINE_AA)` | connects the path's positions; `LINE_AA` = smooth (anti-aliased) lines |
| Make it see-through | `cv2.addWeighted(overlay, 0.35, img, 0.65, 0, img)` | draws at 35% opacity: where many of the 25 paths overlap the colour builds up, so you see the *spread* of the paths, not just one |
| Start and end marks | `cv2.circle` (start), two `cv2.line`s (the end's x) | |
| Speed panel | for each step: time from start vs `distance / delay`, drawn the same way | the same `vmax` and `tmax` for every row, so heights and lengths compare fairly (that's why the Fitts row looks longer) |
| Labels | `cv2.putText(..., cv2.FONT_HERSHEY_SIMPLEX, ...)` | OpenCV's built-in font, no font files needed |
| Save | `cv2.imwrite(out, img)`; raises `OSError` if it returns `False` | `imwrite` reports failure by returning `False`, not by raising |

The README's copy (`docs/images/pathlab.png`) is the same picture (same
seed) shrunk to 900 px wide with `cv2.resize(..., interpolation=cv2.INTER_AREA)`
(the best method for shrinking: it averages pixels instead of skipping
them) and saved with `cv2.IMWRITE_PNG_COMPRESSION, 9`: 737 KB → 353 KB.
To re-create it:

```powershell
python src/main.py pathlab --out docs/images/full.png    # then shrink as above
```

### 8.2 What each number means

All from [src/pathlab/stats.py](../src/pathlab/stats.py), pure functions:

| Column | How it's computed | Answers |
| --- | --- | --- |
| time s | sum of the path's delays | how long the move takes |
| curve px (bow) | the largest distance of any position from the straight start→end line (a cross product with the line's unit vector) | curved? |
| straight | path length ÷ straight distance; 1.000 = a straight line | curved? |
| wobble px | average distance of each position from the midpoint of its two neighbours: 0 on a smooth curve, bigger with jitter | distorted? |
| overshoot | share of paths whose furthest point *along* the line goes > 0.5 px past the end | distorted? |
| max step px | the biggest jump between two consecutive positions (worst over all paths) | continuous? |
| max gap ms | the longest delay between two positions (worst over all paths) | continuous? |
| peak at | when the fastest step happens, as a fraction of the duration | bell-shaped speed? |

## 9. One movement, end to end

What happens between your call and the cursor arriving:

```text
automator.find_and_click("#ff00ff")                           automator.py
  1. locator.locate(query) -> Match(x, y, width, height)      vision/color_locator.py (screen.py: mss screenshot)
  2. match.random_point(center_bias=0.6)                      vision/base.py: a point near the centre, not exactly on it
  3. executor.click(target, path_generator, hold_range)       input/win32_executor.py
       move_to(target):
         origin = GetCursorPos()
         path = path_generator.generate(origin, target)       path/bezier.py:
             overshoot?  -> aim past the target (6)
             controls    = curves.control_points(...)         (2)
             ease        = easing.easing(name, k)             (3)
             steps       = max(8, distance/100 * 18)
             duration    = Fitts's law or duration_range      (5)
             wobble      = jitter.micro_jitter(steps, ...)    (4)
             for i in 1..steps: point_on(curve, ease(i/steps)) + wobble[i]
             overshoot?  -> append a short correction path
         for each PathPoint:
             SendInput(absolute move to round(x), round(y))   # one OS mouse event
             sleep(point.delay)                               # step_time = duration / steps
       SendInput(left button down); sleep(random hold 60-160 ms); SendInput(left button up)
```

- `SendInput` takes *absolute* coordinates scaled to 0..65535 across
  the screen, so `_send_absolute_move` divides by the screen size first.
  The process is DPI-aware (set when `Win32InputExecutor` is created),
  so the screen size and screenshot pixels are the same units.
- Positions are spaced equally in **time** (`step_time`); the easing
  decides how far apart they are in space. That's what creates the
  bell-shaped speed.
- With `FailSafeExecutor` wrapped around the executor, the mouse's
  position is checked between points, and the move stops if you grab
  the mouse ([EXTENSIONS_AND_PLUGINS.md](EXTENSIONS_AND_PLUGINS.md)).

## 10. Design decisions

| Decision | Alternatives | Why | Cost |
| --- | --- | --- | --- |
| One module per building block, pure functions | everything inside the generator | each part is testable and plottable on its own | more files |
| Options on `MovementProfile` with old defaults | new generator classes | existing code keeps working unchanged | one bigger settings object |
| Injected `rng` | the global `random` | reproducible tests and pictures | one extra parameter |
| EMA low-pass for tremor | Perlin noise, sums of sines | one line, one parameter, easy to reason about | less "natural" spectrum than Perlin |
| Taper jitter to zero at the ends | clamp the last point only | no kink right before landing | slightly less wobble near the ends |
| `TYPE_CHECKING` import of `FittsLaw` in geometry.py | a module-level import | avoids an import cycle (path → geometry → path) | the name only exists for type checkers |

## 11. Exercises

1. Add a variant with `easing="linear"` to the path lab. Where does its
   speed peak, and why does it look robotic?
2. Change `logistic_steepness` to 4 and to 20. Predict the "peak at"
   and max step before you run it.
3. Make the cubic S-curve more common (it's 1 in 5 now). Which line in
   `curves.py` controls it, and what should a test check?
4. Use `target_width_px` from the found element: `find_and_click`
   knows the match's width. What would have to change in `UIAutomator`?

**Self-check:** why are the positions spaced equally in *time*, rather
than equally in *distance*?

## References

**Official and primary**

- §2: Wikipedia, [Bézier curve](https://en.wikipedia.org/wiki/B%C3%A9zier_curve) (definitions of quadratic and cubic curves)
- §3: Wikipedia, [Logistic function](https://en.wikipedia.org/wiki/Logistic_function)
- §4: Wikipedia, [Exponential smoothing](https://en.wikipedia.org/wiki/Exponential_smoothing)
- §5: Fitts, P. M. (1954), "The information capacity of the human motor system in controlling the amplitude of movement", *Journal of Experimental Psychology* 47(6); MacKenzie, I. S. (1992), "Fitts' law as a research and design tool in human-computer interaction", *Human-Computer Interaction* 7: [MacKenzie's Fitts's law page](https://www.yorku.ca/mack/hci1992.pdf)
- §5: Wikipedia, [Fitts's law](https://en.wikipedia.org/wiki/Fitts%27s_law)
- §7: Microsoft Learn, [`SendInput`](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)
- §8: OpenCV docs, [drawing functions](https://docs.opencv.org/4.x/d6/d6e/group__imgproc__draw.html)
- Python docs: [`random.Random`](https://docs.python.org/3/library/random.html#random.Random), [`typing.TYPE_CHECKING`](https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING)

**Other explanations**

- Flash, T. & Hogan, N. (1985), "The coordination of arm movements: an experimentally confirmed mathematical model" (the minimum-jerk model behind bell-shaped speed): [Journal of Neuroscience](https://www.jneurosci.org/content/5/7/1688) (the site blocks automated link checks; DOI 10.1523/JNEUROSCI.05-07-01688.1985)
- Freya Holmér, [The Beauty of Bézier Curves](https://www.youtube.com/watch?v=aVwxzDHniEw) (video)

### Further learning

- [A Primer on Bézier Curves](https://pomax.github.io/bezierinfo/) (free online book)
- [Exercism Python track](https://exercism.org/tracks/python)
