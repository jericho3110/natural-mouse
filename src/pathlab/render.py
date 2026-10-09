"""Draw the path lab's comparison as one PNG, with OpenCV (already a
dependency): one row per variant, the paths on the left and speed over
time on the right."""

from __future__ import annotations

import cv2
import numpy as np

from natural_mouse import Path, Point

from .stats import Summary, speeds

ROW_H, PATH_W, SPEED_W, PAD = 320, 620, 560, 30
BG, INK, GRID, FAINT = (250, 250, 248), (40, 40, 40), (225, 225, 225), (150, 150, 150)
COLOURS = [(180, 90, 30), (60, 140, 40), (40, 90, 200), (150, 60, 160), (20, 150, 170)]


def _text(img, s, xy, scale=0.5, colour=INK, bold=1):
    cv2.putText(img, s, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, colour, bold, cv2.LINE_AA)


def _bounds(results, start: Point, end: Point):
    xs = [start.x, end.x] + [p.x for paths, _ in results.values() for path in paths for p in path]
    ys = [start.y, end.y] + [p.y for paths, _ in results.values() for path in paths for p in path]
    return min(xs) - 20, max(xs) + 20, min(ys) - 20, max(ys) + 20


def save_comparison(results: dict[str, tuple[list[Path], Summary]], start: Point, end: Point, out: str) -> None:
    rows = len(results)
    img = np.full((rows * ROW_H + 40, PATH_W + SPEED_W + 3 * PAD, 3), BG, np.uint8)
    _text(img, "natural_mouse path lab: left = paths (start o, end x), right = speed over time",
          (PAD, 26), 0.6, INK, 1)
    x0, x1, y0, y1 = _bounds(results, start, end)
    scale = min((PATH_W - 20) / (x1 - x0), (ROW_H - 70) / (y1 - y0))
    vmax = max(v for paths, _ in results.values() for path in paths for _, v in speeds(start, path)) or 1
    tmax = max(path.total_duration for paths, _ in results.values() for path in paths) or 1

    for row, (name, (paths, summary)) in enumerate(results.items()):
        top = 40 + row * ROW_H
        colour = COLOURS[row % len(COLOURS)]
        _text(img, name, (PAD, top + 20), 0.6, colour, 2)
        _text(img, f"{summary.duration_s:.2f}s  bow {summary.deviation_px:.0f}px  wobble {summary.wobble_px:.2f}px  "
                   f"overshoot {summary.overshoot_rate:.0%}  max step {summary.max_step_px:.0f}px  "
                   f"peak at {summary.peak_at:.2f}", (PAD, top + 42), 0.45)

        def to_px(x, y, top=top):
            return int(PAD + (x - x0) * scale), int(top + 55 + (y - y0) * scale)

        for path in paths:  # the paths, drawn faintly so overlaps show the spread
            pts = np.array([to_px(start.x, start.y)] + [to_px(p.x, p.y) for p in path], np.int32)
            overlay = img.copy()
            cv2.polylines(overlay, [pts], False, colour, 1, cv2.LINE_AA)
            cv2.addWeighted(overlay, 0.35, img, 0.65, 0, img)
        cv2.circle(img, to_px(start.x, start.y), 6, INK, 2, cv2.LINE_AA)
        ex, ey = to_px(end.x, end.y)
        cv2.line(img, (ex - 6, ey - 6), (ex + 6, ey + 6), INK, 2, cv2.LINE_AA)
        cv2.line(img, (ex - 6, ey + 6), (ex + 6, ey - 6), INK, 2, cv2.LINE_AA)

        left, base, height = PATH_W + 2 * PAD, top + ROW_H - 30, ROW_H - 90
        cv2.rectangle(img, (left, base - height), (left + SPEED_W, base), GRID, 1)
        for path in paths:  # speed curves
            pts = np.array([(int(left + t / tmax * SPEED_W), int(base - v / vmax * height))
                            for t, v in speeds(start, path)], np.int32)
            overlay = img.copy()
            cv2.polylines(overlay, [pts], False, colour, 1, cv2.LINE_AA)
            cv2.addWeighted(overlay, 0.35, img, 0.65, 0, img)
        _text(img, "time", (left + SPEED_W - 40, base + 18), 0.4, FAINT)
        _text(img, f"speed (max {vmax:.0f} px/s)", (left, base - height - 6), 0.4, FAINT)

    if not cv2.imwrite(out, img):
        raise OSError(f"couldn't write {out}")
