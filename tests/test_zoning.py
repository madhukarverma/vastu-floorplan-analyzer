import pytest

from vastu_analyzer.zoning import (
    SECTOR_TO_ZONE,
    SECTORS16,
    ZONES,
    MandalaGrid,
    dominant_zone,
    sector16,
    zone_fractions,
)

GRID = MandalaGrid(0.0, 0.0, 9.0, 12.0)


def test_cells_tile_the_grid() -> None:
    total = 0.0
    for z in ZONES:
        x0, y0, x1, y1 = GRID.cell(z)
        total += (x1 - x0) * (y1 - y0)
    assert total == pytest.approx(9.0 * 12.0)
    assert GRID.cell("NE") == pytest.approx((6.0, 8.0, 9.0, 12.0))
    assert GRID.cell("SW") == pytest.approx((0.0, 0.0, 3.0, 4.0))


@pytest.mark.parametrize(
    ("pt", "zone"),
    [((8, 11), "NE"), ((1, 1), "SW"), ((4.5, 6), "C"), ((8, 1), "SE"), ((1, 11), "NW"),
     ((-5, 50), "NW")],
)  # fmt: skip
def test_zone_of_point(pt: tuple[float, float], zone: str) -> None:
    assert GRID.zone_of(pt) == zone


def test_fractions_sum_to_one() -> None:
    room = [(2.0, 3.0), (7.0, 3.0), (7.0, 9.0), (2.0, 9.0)]
    f = zone_fractions(room, GRID)
    assert sum(f.values()) == pytest.approx(1.0)
    assert dominant_zone(f) == "C"
    assert all(v >= 0 for v in f.values())


def test_degenerate_room_has_zero_fractions() -> None:
    assert sum(zone_fractions([(0, 0), (1, 1), (2, 2)], GRID).values()) == 0.0


@pytest.mark.parametrize(
    ("bearing", "sector"),
    [(0, "N"), (11.2, "N"), (11.3, "NNE"), (45, "NE"), (90, "E"), (180, "S"), (225, "SW"),
     (348.7, "NNW"), (348.8, "N"), (359.9, "N"), (-90, "W")],
)  # fmt: skip
def test_sector16(bearing: float, sector: str) -> None:
    assert sector16(bearing) == sector


def test_sector_to_zone_covers_all_sectors() -> None:
    assert set(SECTOR_TO_ZONE) == set(SECTORS16)
    assert set(SECTOR_TO_ZONE.values()) <= set(ZONES)
