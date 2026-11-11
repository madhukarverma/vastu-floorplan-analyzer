import math

import pytest

from vastu_analyzer import geometry as g

SQUARE = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]
L_SHAPE = [(0.0, 0.0), (4.0, 0.0), (4.0, 2.0), (2.0, 2.0), (2.0, 4.0), (0.0, 4.0)]


def test_shoelace_area_and_orientation() -> None:
    assert g.area(SQUARE) == pytest.approx(16.0)
    assert g.signed_area(SQUARE) > 0
    assert g.signed_area(list(reversed(SQUARE))) < 0
    assert g.area(L_SHAPE) == pytest.approx(12.0)


def test_centroid_of_l_shape() -> None:
    # Decompose: 4x2 rect (centroid 2,1; area 8) + 2x2 rect (centroid 1,3; area 4)
    cx, cy = g.centroid(L_SHAPE)
    assert cx == pytest.approx((2 * 8 + 1 * 4) / 12)
    assert cy == pytest.approx((1 * 8 + 3 * 4) / 12)


def test_as_polygon_drops_repeated_closing_vertex() -> None:
    poly = g.as_polygon([[0, 0], [1, 0], [1, 1], [0, 0]])
    assert len(poly) == 3


def test_rotation_quarter_turn() -> None:
    x, y = g.rotate_point((1.0, 0.0), 90.0)
    assert (x, y) == pytest.approx((0.0, 1.0))
    rotated = g.rotate(SQUARE, 37.0, (2.0, 2.0))
    assert g.area(rotated) == pytest.approx(16.0)


@pytest.mark.parametrize(
    ("rect", "expected"),
    [
        ((0, 0, 2, 2), 4.0),
        ((1, 1, 3, 3), 3.0),  # concave notch removes one unit square
        ((2, 2, 4, 4), 0.0),
        ((-5, -5, 10, 10), 12.0),
    ],
)
def test_clip_concave_polygon(rect: tuple[float, float, float, float], expected: float) -> None:
    assert g.rect_overlap_area(L_SHAPE, *rect) == pytest.approx(expected)


def test_point_in_polygon() -> None:
    assert g.point_in_polygon((1, 1), L_SHAPE)
    assert not g.point_in_polygon((3, 3), L_SHAPE)
    assert not g.point_in_polygon((-1, 1), SQUARE)


def test_distances_and_bearings() -> None:
    assert g.point_segment_distance((0, 1), (-1, 0), (1, 0)) == pytest.approx(1.0)
    assert g.point_segment_distance((3, 0), (-1, 0), (1, 0)) == pytest.approx(2.0)
    assert g.distance_to_boundary((2, 2), SQUARE) == pytest.approx(2.0)
    assert g.compass_bearing(0, 1) == pytest.approx(0.0)
    assert g.compass_bearing(1, 0) == pytest.approx(90.0)
    assert g.compass_bearing(-1, -1) == pytest.approx(225.0)
    assert g.angular_difference(350, 10) == pytest.approx(20.0)
    assert g.angular_difference(0, 180) == pytest.approx(180.0)


def test_bounds() -> None:
    assert g.bounds([SQUARE, [(5.0, -1.0), (6.0, 0.0), (5.0, 1.0)]]) == (0.0, -1.0, 6.0, 4.0)
    assert math.isclose(g.area(g.ensure_ccw(list(reversed(SQUARE)))), 16.0)
