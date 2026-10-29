"""Classify a wand stroke as Tide, Flame, Frost, or Strike.

The four shapes are separated by geometry: a circle closes and turns all the
way around, a zigzag corners at least twice, a frost line is straight and
flat, and a strike is a straight diagonal.
"""

from __future__ import annotations

import math
from typing import Sequence

Point = tuple[float, float]

SPELLS = ("tide", "flame", "frost", "strike")
MIN_POINTS = 6
MIN_LENGTH = 28.0
CONFIDENCE_CUTOFF = 0.62
MARGIN = 0.12

# Keyboard sparkles are drawn in the same 320x240 space as the camera.
_PREVIEW_W = 320.0
_PREVIEW_H = 240.0


def classify(points: Sequence[Point]) -> tuple[str | None, float, dict[str, float]]:
    """Return (spell or None, confidence, per-spell scores)."""
    if len(points) < MIN_POINTS:
        return None, 0.0, {}
    pts = _resample(list(points), 48)
    feats = _features(pts)
    if feats["length"] < MIN_LENGTH:
        return None, 0.0, {}
    scores = {
        "tide": _score_tide(feats),
        "flame": _score_flame(feats),
        "frost": _score_frost(feats),
        "strike": _score_strike(feats),
    }
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_name, best = ranked[0]
    second = ranked[1][1]
    if best < CONFIDENCE_CUTOFF or (best - second) < MARGIN:
        return None, best, scores
    return best_name, best, scores


def sample_path(spell: str) -> list[Point]:
    """A clean camera-space path for keyboard feedback."""
    cx, cy = _PREVIEW_W * 0.42, _PREVIEW_H * 0.48
    if spell == "tide":
        return [
            (cx + math.cos(a) * 70, cy + math.sin(a) * 58)
            for a in (i / 36 * math.tau for i in range(37))
        ]
    if spell == "flame":
        return _polyline(
            [(cx - 80, cy - 40), (cx + 80, cy - 40), (cx - 70, cy + 45), (cx + 80, cy + 45)],
            12,
        )
    if spell == "frost":
        return [(cx - 100 + i * 5, cy + math.sin(i * 0.4) * 2) for i in range(40)]
    if spell == "strike":
        return [(cx - 70 + i * 4, cy - 60 + i * 3.4) for i in range(36)]
    return [(cx, cy)]


def _score_tide(feats: dict) -> float:
    closed = 1.0 - min(1.0, feats["closure"] / 0.7)
    loop = _smoothstep(feats["turn"], 2.4, 4.8)
    aspect = min(feats["w"], feats["h"]) / max(feats["w"], feats["h"], 1e-6)
    square = _smoothstep(aspect, 0.35, 0.75)
    not_line = 1.0 - _smoothstep(feats["straightness"], 0.45, 0.82)
    travel = _smoothstep(feats["length"] / feats["diag"], 1.5, 2.5)
    score = closed * 0.34 + loop * 0.28 + square * 0.14 + not_line * 0.12 + travel * 0.12
    if feats["reversals"] >= 4:
        score *= 0.45
    if feats["straightness"] > 0.75:
        score *= 0.2
    return _clamp(score)


def _score_flame(feats: dict) -> float:
    if feats["reversals"] < 2:
        return _clamp((1.0 - feats["straightness"]) * 0.2)
    if feats["closure"] < 0.28 and feats["turn"] > 5.0:
        return 0.15
    not_closed = _smoothstep(feats["closure"], 0.28, 0.6)
    not_line = 1.0 - _smoothstep(feats["straightness"], 0.62, 0.9)
    corners = min(1.0, feats["reversals"] / 2.0)
    score = corners * 0.55 + not_closed * 0.25 + not_line * 0.2
    return _clamp(score)


def _score_frost(feats: dict) -> float:
    straight = _smoothstep(feats["straightness"], 0.7, 0.92)
    horizontal = _smoothstep(feats["abs_cos"], 0.84, 0.97)
    flat = _smoothstep(feats["w"] / max(feats["h"], 1.0), 2.0, 4.5)
    score = straight * 0.42 + horizontal * 0.33 + flat * 0.25
    if feats["reversals"] >= 2:
        score *= 0.3
    if feats["abs_sin"] > feats["abs_cos"]:
        score *= 0.25
    return _clamp(score)


def _score_strike(feats: dict) -> float:
    straight = _smoothstep(feats["straightness"], 0.7, 0.92)
    balance = 1.0 - min(1.0, abs(feats["abs_cos"] - feats["abs_sin"]) / 0.45)
    diagonal = _smoothstep(balance, 0.4, 0.85)
    if feats["abs_cos"] > 0.92 or feats["abs_sin"] > 0.92:
        diagonal *= 0.12
    score = straight * 0.5 + diagonal * 0.5
    if feats["reversals"] >= 2:
        score *= 0.25
    return _clamp(score)


def _features(pts: list[Point]) -> dict:
    length = _polyline_length(pts)
    start, end = pts[0], pts[-1]
    chord = _dist(start, end)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    diag = math.hypot(width, height) or 1.0
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    return {
        "length": length,
        "straightness": chord / length if length else 0.0,
        "closure": chord / diag,
        "w": width,
        "h": height,
        "diag": diag,
        "abs_cos": abs(math.cos(angle)),
        "abs_sin": abs(math.sin(angle)),
        "reversals": _reversals(pts),
        "turn": _total_turn(pts),
    }


def _reversals(pts: list[Point]) -> int:
    """Count sharp corners, ignoring the gentle heading change of a circle."""
    headings = _headings(pts, span=1)
    if len(headings) < 4:
        return 0
    count = 0
    calm = 0
    in_corner = False
    prev = headings[0]
    for heading in headings[1:]:
        delta = abs(_angle_diff(heading, prev))
        prev = heading
        if delta > 0.75:
            if not in_corner and calm >= 3:
                count += 1
            in_corner = True
            calm = 0
        else:
            calm += 1
            if delta < 0.35:
                in_corner = False
    return count


def _total_turn(pts: list[Point]) -> float:
    headings = _headings(pts, span=2)
    total = 0.0
    for a, b in zip(headings, headings[1:]):
        total += abs(_angle_diff(b, a))
    return total


def _headings(pts: list[Point], span: int) -> list[float]:
    headings = []
    for i in range(len(pts) - span):
        dx = pts[i + span][0] - pts[i][0]
        dy = pts[i + span][1] - pts[i][1]
        if dx * dx + dy * dy < 1.0:
            continue
        headings.append(math.atan2(dy, dx))
    return headings


def _resample(points: list[Point], count: int) -> list[Point]:
    if len(points) == 1:
        return points * count
    lengths = [0.0]
    for a, b in zip(points, points[1:]):
        lengths.append(lengths[-1] + _dist(a, b))
    total = lengths[-1]
    if total < 1e-6:
        return [points[0]] * count
    out = []
    segment = 0
    for i in range(count):
        target = total * i / (count - 1)
        while segment < len(lengths) - 2 and lengths[segment + 1] < target:
            segment += 1
        span = lengths[segment + 1] - lengths[segment]
        t = 0.0 if span < 1e-6 else (target - lengths[segment]) / span
        ax, ay = points[segment]
        bx, by = points[min(segment + 1, len(points) - 1)]
        out.append((ax + (bx - ax) * t, ay + (by - ay) * t))
    return out


def _polyline(corners: list[Point], steps: int) -> list[Point]:
    points: list[Point] = []
    for a, b in zip(corners, corners[1:]):
        for i in range(steps):
            t = i / steps
            points.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    points.append(corners[-1])
    return points


def _smoothstep(value: float, edge0: float, edge1: float) -> float:
    if edge1 == edge0:
        return 1.0 if value >= edge1 else 0.0
    t = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _polyline_length(pts: Sequence[Point]) -> float:
    return sum(_dist(a, b) for a, b in zip(pts, pts[1:]))


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _angle_diff(a: float, b: float) -> float:
    delta = a - b
    while delta > math.pi:
        delta -= math.tau
    while delta < -math.pi:
        delta += math.tau
    return delta


def _self_check() -> None:
    samples = {
        "tide": sample_path("tide"),
        "flame": sample_path("flame"),
        "frost": sample_path("frost"),
        "strike": sample_path("strike"),
    }
    samples["gapped_circle"] = [
        (
            160 + math.cos(i / 28 * math.tau * 0.85) * 75,
            120 + math.sin(i / 28 * math.tau * 0.85) * 62,
        )
        for i in range(29)
    ]
    samples["vertical"] = [(100, 20 + i * 4) for i in range(40)]
    samples["wobble"] = [(20 + i * 4, 80 + math.sin(i * 0.7) * 6) for i in range(50)]
    expected = {
        "tide": "tide",
        "flame": "flame",
        "frost": "frost",
        "strike": "strike",
        "gapped_circle": "tide",
        "vertical": None,
        "wobble": "frost",
    }
    failed = False
    for name, path in samples.items():
        spell, confidence, scores = classify(path)
        ok = spell == expected[name]
        failed = failed or not ok
        rounded = {key: round(value, 2) for key, value in scores.items()}
        print(f"{'ok' if ok else 'FAIL'} {name}: got {spell} ({confidence:.2f}) {rounded}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _self_check()
