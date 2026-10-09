"""The path lab: compare movement variants without touching the mouse.

    python src/main.py pathlab                    # writes pathlab.png, prints a table
    python src/main.py pathlab --runs 40 --seed 3 --out compare.png

Each variant is just a `MovementProfile`. The lab generates `runs`
paths per variant (seeded, so the same command gives the same picture),
measures them (stats.py), prints a table and draws them (render.py).
Add your own variant to VARIANTS to try an idea.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from natural_mouse import BezierPathGenerator, FittsLaw, MovementProfile, Path, Point

from .stats import Summary, measure, summarize

START, END = Point(150, 450), Point(850, 150)

VARIANTS: dict[str, MovementProfile] = {
    "classic: quadratic + cosine": MovementProfile(),
    "cubic + cosine": MovementProfile(curve="cubic"),
    "cubic + logistic (k=10)": MovementProfile(curve="cubic", easing="logistic"),
    "cubic + logistic + tremor": MovementProfile(curve="cubic", easing="logistic", jitter_smoothing=0.85,
                                                 jitter_px=1.5),
    "cubic + logistic + tremor + Fitts": MovementProfile(curve="cubic", easing="logistic", jitter_smoothing=0.85,
                                                         jitter_px=1.5, fitts=FittsLaw()),
}


def generate(profile: MovementProfile, runs: int, seed: int) -> list[Path]:
    rng = random.Random(seed)   # noqa: S311 - reproducible experiments, not security
    generator = BezierPathGenerator(profile, rng)
    return [generator.generate(START, END) for _ in range(runs)]


def compare(variants: dict[str, MovementProfile], runs: int, seed: int) -> dict[str, tuple[list[Path], Summary]]:
    results = {}
    for name, profile in variants.items():
        paths = generate(profile, runs, seed)
        results[name] = (paths, summarize([measure(START, END, p) for p in paths]))
    return results


def table(results: dict[str, tuple[list[Path], Summary]]) -> str:
    head = ("variant", "time s", "curve px", "straight", "wobble px", "overshoot", "max step px",
            "max gap ms", "peak at")
    rows = [head] + [(
        name, f"{s.duration_s:.2f}", f"{s.deviation_px:.0f}", f"{s.straightness:.3f}", f"{s.wobble_px:.2f}",
        f"{s.overshoot_rate:.0%}", f"{s.max_step_px:.1f}", f"{s.max_gap_ms:.1f}", f"{s.peak_at:.2f}",
    ) for name, (_, s) in results.items()]
    widths = [max(len(r[i]) for r in rows) for i in range(len(head))]
    lines = ["  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(lines)


def fitts_table(law: FittsLaw = FittsLaw(), width: float = 24.0) -> str:
    lines = [f"Fitts's law, a={law.a}s b={law.b}s, target {width:g}px wide:", "  distance px  ID bits  time s"]
    for d in (50, 100, 200, 400, 800, 1600):
        lines.append(f"  {d:>11}  {law.index_of_difficulty(d, width):>7.2f}  {law.movement_time(d, width):>6.3f}")
    return "\n".join(lines)


def run(out: str = "pathlab.png", runs: int = 25, seed: int = 1,
        print_: Callable[[str], object] = print) -> int:
    from .render import save_comparison   # imported here: drawing needs OpenCV, the stats don't

    results = compare(VARIANTS, runs, seed)
    print_(f"{runs} paths per variant, from {START.as_tuple()} to {END.as_tuple()}, seed {seed}:\n")
    print_(table(results))
    print_("")
    print_(fitts_table())
    save_comparison(results, START, END, out)
    print_(f"\nPicture saved: {out}")
    return 0
