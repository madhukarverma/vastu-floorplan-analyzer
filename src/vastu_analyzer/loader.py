"""Read and validate floor-plan JSON files (schema documented in docs/input-schema.md)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .geometry import Polygon, area, as_polygon, centroid, ensure_ccw, point_in_polygon
from .models import Entrance, FloorPlan, Location, North, Room

UNIT_FACTORS = {"m": 1.0, "cm": 0.01, "mm": 0.001, "ft": 0.3048, "in": 0.0254}
SUPPORTED_SCHEMA = "1"


class PlanValidationError(ValueError):
    """Raised when a plan file is structurally invalid. ``errors`` lists every problem."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def _polygon(raw: Any, what: str, factor: float, errors: list[str]) -> Polygon:
    try:
        poly = as_polygon(raw)
    except (TypeError, ValueError, IndexError):
        errors.append(f"{what}: polygon must be a list of [x, y] pairs")
        return []
    if len(poly) < 3:
        errors.append(f"{what}: polygon needs at least 3 vertices")
        return []
    poly = [(x * factor, y * factor) for x, y in poly]
    if area(poly) <= 1e-6:
        errors.append(f"{what}: polygon has zero area")
        return []
    return ensure_ccw(poly)


def plan_from_dict(data: dict[str, Any]) -> FloorPlan:
    """Build a :class:`FloorPlan` from a parsed JSON mapping, collecting all errors."""
    errors: list[str] = []
    version = str(data.get("schema_version", SUPPORTED_SCHEMA)).split(".")[0]
    if version != SUPPORTED_SCHEMA:
        errors.append(f"unsupported schema_version {data.get('schema_version')!r}")
    units = str(data.get("units", "m")).lower()
    if units not in UNIT_FACTORS:
        errors.append(f"units must be one of {sorted(UNIT_FACTORS)}")
        units = "m"
    k = UNIT_FACTORS[units]

    footprint = _polygon(data.get("footprint"), "footprint", k, errors)

    n = data.get("north", {})
    if isinstance(n, (int, float)):
        n = {"angle_deg": n}
    reference = n.get("reference", "true")
    if reference not in ("true", "magnetic"):
        errors.append("north.reference must be 'true' or 'magnetic'")
        reference = "true"
    north = North(float(n.get("angle_deg", 0.0)), reference, float(n.get("declination_deg", 0.0)))

    loc = data.get("location")
    location = None
    if loc:
        lat, lon = float(loc["latitude"]), float(loc["longitude"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            errors.append("location: latitude/longitude out of range")
        location = Location(lat, lon, float(loc.get("timezone", 5.5)))

    rooms: list[Room] = []
    raw_rooms = data.get("rooms") or []
    if not raw_rooms:
        errors.append("plan must contain at least one room")
    for i, r in enumerate(raw_rooms):
        name = str(r.get("name", f"room-{i + 1}"))
        poly = _polygon(r.get("polygon"), f"room '{name}'", k, errors)
        if poly and footprint and not point_in_polygon(centroid(poly), footprint):
            errors.append(f"room '{name}': centroid lies outside the footprint")
        if "type" not in r:
            errors.append(f"room '{name}': missing 'type'")
        rooms.append(Room(name, str(r.get("type", "other")), poly))

    entrances: list[Entrance] = []
    for i, e in enumerate(data.get("entrances") or []):
        try:
            x, y = (float(v) * k for v in e["position"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"entrance {i + 1}: 'position' must be [x, y]")
            continue
        entrances.append(Entrance(str(e.get("name", f"door-{i + 1}")), (x, y), bool(e.get("main"))))
    if entrances and not any(e.main for e in entrances):
        entrances[0].main = True

    if errors:
        raise PlanValidationError(errors)
    return FloorPlan(
        name=str(data.get("name", "Untitled plan")),
        footprint=footprint,
        rooms=rooms,
        entrances=entrances,
        north=north,
        location=location,
        units="m",
        metadata=dict(data.get("metadata", {})),
    )


def load_plan(path: str | Path) -> FloorPlan:
    """Load a plan from a JSON file."""
    with Path(path).open(encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise PlanValidationError([f"invalid JSON: {exc}"]) from exc
    if not isinstance(data, dict):
        raise PlanValidationError(["top-level JSON value must be an object"])
    return plan_from_dict(data)


def plan_to_dict(plan: FloorPlan) -> dict[str, Any]:
    """Inverse of :func:`plan_from_dict` (always written in metres)."""
    out: dict[str, Any] = {
        "schema_version": "1.0",
        "name": plan.name,
        "units": "m",
        "north": {
            "angle_deg": plan.north.angle_deg,
            "reference": plan.north.reference,
            "declination_deg": plan.north.declination_deg,
        },
        "footprint": [list(p) for p in plan.footprint],
        "rooms": [
            {"name": r.name, "type": r.type, "polygon": [list(p) for p in r.polygon]}
            for r in plan.rooms
        ],
        "entrances": [
            {"name": e.name, "position": list(e.position), "main": e.main} for e in plan.entrances
        ],
    }
    if plan.location:
        out["location"] = {
            "latitude": plan.location.latitude,
            "longitude": plan.location.longitude,
            "timezone": plan.location.timezone,
        }
    if plan.metadata:
        out["metadata"] = plan.metadata
    return out
