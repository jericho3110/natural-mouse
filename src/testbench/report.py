"""Turn the page's raw events into numbers: the pure core of the bench.

No screen, no mouse, no network: every function takes a list of event
dicts (as page.html sends them) and returns plain values, so they're
unit-tested with hand-written events (tests/test_testbench_report.py).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MoveSummary:
    """The pointer trail the browser saw during one step."""

    events: int
    duration_ms: float
    path_px: float      # length of the trail, point to point
    straight_px: float  # distance from first to last point

    @property
    def curviness(self) -> float:
        """path / straight: 1.0 = a straight line, higher = more curved."""
        return self.path_px / self.straight_px if self.straight_px else 1.0


@dataclass(frozen=True)
class WheelSummary:
    """What a scroll step delivered."""

    events: int
    total_delta_y: float  # positive = down, as browsers report it
    gaps_ms: tuple[float, float, float] | None  # min, mean, max between wheel events
    scroll_before: float
    scroll_after: float

    @property
    def scrolled_px(self) -> float:
        return self.scroll_after - self.scroll_before


@dataclass(frozen=True)
class ClickSummary:
    target: str | None
    dx: float | None  # -1..1 across the target, 0 = centre
    dy: float | None

    @property
    def hit(self) -> bool:
        return self.target is not None


@dataclass
class StepResult:
    """One step of the scenario, for the final table."""

    name: str
    ok: bool
    detail: str
    moves: MoveSummary | None = None
    extra: dict = field(default_factory=dict)


def of_type(events: list[dict], kind: str) -> list[dict]:
    return [e for e in events if e.get("type") == kind]


def summarize_moves(events: list[dict]) -> MoveSummary:
    moves = of_type(events, "mousemove")
    if not moves:
        return MoveSummary(0, 0.0, 0.0, 0.0)
    path = sum(
        math.hypot(b["x"] - a["x"], b["y"] - a["y"]) for a, b in zip(moves, moves[1:])
    )
    first, last = moves[0], moves[-1]
    straight = math.hypot(last["x"] - first["x"], last["y"] - first["y"])
    return MoveSummary(len(moves), last["t"] - first["t"], path, straight)


def last_scroll_y(events: list[dict], default: float = 0.0) -> float:
    for event in reversed(events):
        if "scrollY" in event:
            return float(event["scrollY"])
    return default


def summarize_wheel(before: list[dict], during: list[dict]) -> WheelSummary:
    """`before` = every event up to the step, `during` = the step's events
    (including the smooth-scroll tail after the last wheel event)."""
    wheels = of_type(during, "wheel")
    gaps = [b["t"] - a["t"] for a, b in zip(wheels, wheels[1:])]
    gap_stats = (min(gaps), sum(gaps) / len(gaps), max(gaps)) if gaps else None
    start = last_scroll_y(before)
    return WheelSummary(
        events=len(wheels),
        total_delta_y=sum(float(w.get("deltaY", 0)) for w in wheels),
        gaps_ms=gap_stats,
        scroll_before=start,
        scroll_after=last_scroll_y(during, start),
    )


def summarize_click(during: list[dict]) -> ClickSummary | None:
    clicks = of_type(during, "click")
    if not clicks:
        return None
    c = clicks[-1]
    return ClickSummary(c.get("target"), c.get("dx"), c.get("dy"))


def format_table(steps: list[StepResult]) -> str:
    """A plain-text table, one row per step, for the console."""
    rows = [("step", "result", "moves", "curviness", "details")]
    for s in steps:
        moves = s.moves
        rows.append((
            s.name,
            "ok" if s.ok else "FAIL",
            "-" if moves is None else f"{moves.events} in {moves.duration_ms:.0f} ms",
            "-" if moves is None or moves.events < 2 else f"{moves.curviness:.2f}",
            s.detail,
        ))
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]) - 1)]
    lines = []
    for r in rows:
        cells = [r[i].ljust(widths[i]) for i in range(len(widths))] + [r[-1]]
        lines.append("  ".join(cells).rstrip())
    lines.insert(1, "  ".join("-" * w for w in widths) + "  -------")
    return "\n".join(lines)
