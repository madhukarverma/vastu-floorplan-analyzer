"""Planar computational-geometry primitives.

Everything here is deterministic, dependency-free Python. Polygons are lists of
``(x, y)`` tuples in metres; the closing vertex is implicit (do not repeat the
first point at the end).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterator, Sequence

Point = tuple[float, float]
Polygon = list[Point]

EPS = 1e-9


def as_polygon(points: Sequence[Sequence[float]]) -> Polygon:
    """Convert any sequence of pairs into a polygon, dropping a repeated closing vertex."""
    poly: Polygon = [(float(p[0]), float(p[1])) for p in points]
    if len(poly) > 1 and math.dist(poly[0], poly[-1]) < EPS:
        poly.pop()
    return poly


def signed_area(poly: Sequence[Point]) -> float:
    """Shoelace formula. Positive for counter-clockwise vertex order."""
    n = len(poly)
    s = 0.0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return 0.5 * s


def area(poly: Sequence[Point]) -> float:
    """Unsigned polygon area."""
    return abs(signed_area(poly))


def centroid(poly: Sequence[Point]) -> Point:
    """Area centroid of a simple polygon (falls back to the vertex mean if degenerate)."""
    a = signed_area(poly)
    n = len(poly)
    if abs(a) < EPS:
        return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)
    cx = cy = 0.0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    return (cx / (6.0 * a), cy / (6.0 * a))


def ensure_ccw(poly: Sequence[Point]) -> Polygon:
    """Return the polygon with counter-clockwise orientation."""
    out = list(poly)
    if signed_area(out) < 0:
        out.reverse()
    return out


def rotate_point(p: Point, angle_deg: float, origin: Point = (0.0, 0.0)) -> Point:
    """Rotate ``p`` counter-clockwise by ``angle_deg`` about ``origin``."""
    t = math.radians(angle_deg)
    c, s = math.cos(t), math.sin(t)
    x, y = p[0] - origin[0], p[1] - origin[1]
    return (origin[0] + c * x - s * y, origin[1] + s * x + c * y)


def rotate(poly: Sequence[Point], angle_deg: float, origin: Point = (0.0, 0.0)) -> Polygon:
    """Rotate every vertex counter-clockwise by ``angle_deg`` about ``origin``."""
    return [rotate_point(p, angle_deg, origin) for p in poly]


def bounds(polys: Sequence[Sequence[Point]]) -> tuple[float, float, float, float]:
    """Axis-aligned bounding box ``(xmin, ymin, xmax, ymax)`` of several polygons."""
    xs = [p[0] for poly in polys for p in poly]
    ys = [p[1] for poly in polys for p in poly]
    return (min(xs), min(ys), max(xs), max(ys))


def edges(poly: Sequence[Point]) -> Iterator[tuple[Point, Point]]:
    """Yield the directed edges ``(a, b)`` of a closed polygon."""
    n = len(poly)
    for i in range(n):
        yield poly[i], poly[(i + 1) % n]


def clip_to_rect(
    poly: Sequence[Point], xmin: float, ymin: float, xmax: float, ymax: float
) -> Polygon:
    """Sutherland-Hodgman clipping of a (possibly concave) polygon by an axis-aligned rectangle.

    The clip window is convex, so the algorithm is exact for the *area* of the
    intersection even when the subject polygon is concave (degenerate zero-width
    bridges may appear in the output, but they contribute no area).
    """
    out: list[Point] = list(poly)
    # Each clip boundary is a pair: (is_inside(p), intersection(p, q)).
    boundaries: tuple[tuple[Callable[[Point], bool], Callable[[Point, Point], Point]], ...] = (
        (lambda p: p[0] >= xmin, lambda p, q: _x_cut(p, q, xmin)),
        (lambda p: p[0] <= xmax, lambda p, q: _x_cut(p, q, xmax)),
        (lambda p: p[1] >= ymin, lambda p, q: _y_cut(p, q, ymin)),
        (lambda p: p[1] <= ymax, lambda p, q: _y_cut(p, q, ymax)),
    )
    for is_inside, cut in boundaries:
        if not out:
            break
        src, out = out, []
        prev = src[-1]
        for cur in src:
            if is_inside(cur):
                if not is_inside(prev):
                    out.append(cut(prev, cur))
                out.append(cur)
            elif is_inside(prev):
                out.append(cut(prev, cur))
            prev = cur
    return out


def _x_cut(p: Point, q: Point, x: float) -> Point:
    t = (x - p[0]) / (q[0] - p[0])
    return (x, p[1] + t * (q[1] - p[1]))


def _y_cut(p: Point, q: Point, y: float) -> Point:
    t = (y - p[1]) / (q[1] - p[1])
    return (p[0] + t * (q[0] - p[0]), y)


def rect_overlap_area(
    poly: Sequence[Point], xmin: float, ymin: float, xmax: float, ymax: float
) -> float:
    """Area of the intersection between ``poly`` and an axis-aligned rectangle."""
    clipped = clip_to_rect(poly, xmin, ymin, xmax, ymax)
    return area(clipped) if len(clipped) >= 3 else 0.0


def point_in_polygon(pt: Point, poly: Sequence[Point]) -> bool:
    """Even-odd ray-casting test (points exactly on an edge may go either way)."""
    x, y = pt
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            x_cross = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def point_segment_distance(p: Point, a: Point, b: Point) -> float:
    """Euclidean distance from point ``p`` to the closed segment ``ab``."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    if seg2 < EPS:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / seg2))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def distance_to_boundary(p: Point, poly: Sequence[Point]) -> float:
    """Distance from ``p`` to the nearest edge of ``poly``."""
    return min(point_segment_distance(p, a, b) for a, b in edges(poly))


def compass_bearing(dx: float, dy: float) -> float:
    """Bearing in degrees, clockwise from the +y axis, in ``[0, 360)``."""
    return math.degrees(math.atan2(dx, dy)) % 360.0


def angular_difference(a_deg: float, b_deg: float) -> float:
    """Smallest absolute difference between two bearings, in ``[0, 180]``."""
    d = abs(a_deg - b_deg) % 360.0
    return 360.0 - d if d > 180.0 else d
