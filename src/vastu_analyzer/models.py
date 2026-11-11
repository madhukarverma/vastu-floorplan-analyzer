"""Typed data model for floor plans and analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .geometry import Point, Polygon

NorthReference = Literal["true", "magnetic"]
Severity = Literal["critical", "major", "minor", "info"]


@dataclass(frozen=True)
class North:
    """Orientation of the drawing.

    ``angle_deg`` is the direction the plan's north arrow points, measured clockwise
    from the drawing's "up" (+y) axis. If the arrow shows *magnetic* north, give the
    local magnetic declination (east positive, e.g. from WMM2025) so that true north
    can be recovered: ``theta_true = angle_deg - declination_deg``.
    """

    angle_deg: float = 0.0
    reference: NorthReference = "true"
    declination_deg: float = 0.0

    @property
    def true_angle_deg(self) -> float:
        if self.reference == "magnetic":
            return self.angle_deg - self.declination_deg
        return self.angle_deg


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    timezone: float = 5.5


@dataclass
class Room:
    name: str
    type: str
    polygon: Polygon


@dataclass
class Entrance:
    name: str
    position: Point
    main: bool = False


@dataclass
class FloorPlan:
    name: str
    footprint: Polygon
    rooms: list[Room]
    entrances: list[Entrance] = field(default_factory=list)
    north: North = field(default_factory=North)
    location: Location | None = None
    units: str = "m"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Wall:
    """An exterior wall segment of a room."""

    length: float
    azimuth: float  # outward normal, degrees clockwise from true north
    sector: str


@dataclass
class RoomResult:
    name: str
    type: str
    label: str
    area: float
    centroid: Point  # cardinal frame (x = east, y = north)
    sector: str  # 16-sector bearing of the centroid from the site centre
    zone: str  # dominant 3 x 3 zone
    fractions: dict[str, float]
    score: float  # 0 .. 1
    weight: float
    walls: list[Wall] = field(default_factory=list)
    solar: dict[str, float] = field(default_factory=dict)


@dataclass
class EntranceResult:
    name: str
    main: bool
    bearing: float
    sector: str
    score: float
    weight: float


@dataclass
class SiteResult:
    area: float
    bbox_area: float
    rectangularity: float
    aspect_ratio: float
    shape_score: float
    corner_fill: dict[str, float]
    brahmasthana_blocked: float  # fraction of the central cell occupied by forbidden uses
    brahmasthana_score: float
    dipole_bearing: float
    dipole_magnitude: float  # normalised by half the bbox diagonal
    dipole_score: float
    orientation_skew: float  # deviation of the plan axes from the nearest cardinal (deg)


@dataclass
class Finding:
    severity: Severity
    category: str  # room | entrance | site | physics
    subject: str
    message: str
    suggestion: str
    traditional: str = ""
    physics: str = ""
    impact: float = 0.0  # potential VCI points recoverable


@dataclass
class Swap:
    room_a: str
    room_b: str
    type_a: str
    type_b: str
    vci_before: float
    vci_after: float

    @property
    def gain(self) -> float:
        return self.vci_after - self.vci_before


@dataclass
class AnalysisResult:
    plan_name: str
    vci: float  # Vastu Compliance Index, 0 .. 100
    components: dict[str, float]
    rooms: list[RoomResult]
    entrances: list[EntranceResult]
    site: SiteResult
    findings: list[Finding]
    swaps: list[Swap]
    solar_summary: dict[str, Any]
    optimised_vci: float | None = None
