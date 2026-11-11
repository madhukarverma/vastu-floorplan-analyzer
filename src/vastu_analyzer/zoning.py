"""Directional zoning: the discretised Vastu Purusha Mandala and 16-sector compass.

The classical texts subdivide a site into an ``n x n`` grid of *padas*. For a
dwelling the 9 x 9 *Paramasayika* mandala is customary; for direction-of-room
reasoning the common practitioner simplification is the 3 x 3 *Pitha* mandala,
whose eight outer cells are the eight directions (*dik*) and whose centre is the
*Brahmasthana*. This module implements the 3 x 3 grid and a 16-sector bearing
model (22.5 degrees per sector) used for entrances and reporting.

All functions here expect coordinates in a *cardinal frame*: +x = East, +y = North.
"""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import Point, Polygon, area, rect_overlap_area

#: The nine zones of the 3 x 3 mandala, listed row by row from the north-west.
ZONES: tuple[str, ...] = ("NW", "N", "NE", "W", "C", "E", "SW", "S", "SE")

#: Sanskrit names of the eight directions and the centre.
ZONE_SANSKRIT: dict[str, str] = {
    "N": "Uttara (Kubera)",
    "NE": "Ishanya (Ishana)",
    "E": "Purva (Indra)",
    "SE": "Agneya (Agni)",
    "S": "Dakshina (Yama)",
    "SW": "Nairutya (Nirriti)",
    "W": "Paschima (Varuna)",
    "NW": "Vayavya (Vayu)",
    "C": "Brahmasthana (Brahma)",
}

#: The 16 compass sectors, clockwise from north.
SECTORS16: tuple[str, ...] = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)  # fmt: skip

#: Map each 16-sector name to the 8-direction zone it belongs to (ties -> cardinal).
SECTOR_TO_ZONE: dict[str, str] = {
    "N": "N", "NNE": "N", "NE": "NE", "ENE": "E",
    "E": "E", "ESE": "E", "SE": "SE", "SSE": "S",
    "S": "S", "SSW": "S", "SW": "SW", "WSW": "W",
    "W": "W", "WNW": "W", "NW": "NW", "NNW": "N",
}  # fmt: skip


@dataclass(frozen=True)
class MandalaGrid:
    """A 3 x 3 grid laid over the bounding box of the site, aligned to the cardinal axes."""

    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @property
    def width(self) -> float:
        return self.xmax - self.xmin

    @property
    def height(self) -> float:
        return self.ymax - self.ymin

    @property
    def centre(self) -> Point:
        return ((self.xmin + self.xmax) / 2.0, (self.ymin + self.ymax) / 2.0)

    def cell(self, zone: str) -> tuple[float, float, float, float]:
        """Rectangle ``(xmin, ymin, xmax, ymax)`` of a zone."""
        idx = ZONES.index(zone)
        row, col = divmod(idx, 3)  # row 0 = north, col 0 = west
        dx, dy = self.width / 3.0, self.height / 3.0
        x0 = self.xmin + col * dx
        y1 = self.ymax - row * dy
        return (x0, y1 - dy, x0 + dx, y1)

    def cell_area(self) -> float:
        return self.width * self.height / 9.0

    def zone_of(self, p: Point) -> str:
        """Zone containing point ``p`` (points outside the box are clamped)."""
        fx = (p[0] - self.xmin) / self.width
        fy = (p[1] - self.ymin) / self.height
        col = min(2, max(0, int(fx * 3.0)))
        row = 2 - min(2, max(0, int(fy * 3.0)))
        return ZONES[row * 3 + col]


def zone_fractions(poly: Polygon, grid: MandalaGrid) -> dict[str, float]:
    """Fraction of the polygon's area lying in each of the nine zones.

    This is the *zone-membership vector* ``f`` of the paper; its components are
    non-negative and sum to 1 for a polygon contained in the grid.
    """
    total = area(poly)
    if total <= 0:
        return dict.fromkeys(ZONES, 0.0)
    return {z: rect_overlap_area(poly, *grid.cell(z)) / total for z in ZONES}


def zone_overlap_area(poly: Polygon, grid: MandalaGrid, zone: str) -> float:
    """Absolute area (m^2) of ``poly`` inside ``zone``."""
    return rect_overlap_area(poly, *grid.cell(zone))


def dominant_zone(fractions: dict[str, float]) -> str:
    """Zone holding the largest share of a membership vector.

    Shares are compared after rounding to 1e-9 so that floating-point noise cannot
    break exact ties; ties resolve in the fixed order of :data:`ZONES`.
    """
    return max(ZONES, key=lambda z: (round(fractions.get(z, 0.0), 9), -ZONES.index(z)))


def sector16(bearing_deg: float) -> str:
    """16-point compass sector for a bearing (degrees clockwise from north)."""
    return SECTORS16[int(((bearing_deg % 360.0) + 11.25) // 22.5) % 16]
