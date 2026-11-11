"""Loading and querying the Vastu knowledge base (a plain JSON file)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RoomRule:
    key: str
    label: str
    weight: float
    heaviness: float
    movable: bool
    zones: dict[str, float]  # zone -> value in [0, 1]
    traditional: str
    physics: str
    remedy: str

    def value(self, zone: str) -> float:
        return self.zones[zone]

    def best_zones(self) -> list[str]:
        top = max(self.zones.values())
        return [z for z, v in self.zones.items() if v == top]


class RuleBase:
    """In-memory view of ``rules.json`` with level names resolved to numbers."""

    ZONES = ("NW", "N", "NE", "W", "C", "E", "SW", "S", "SE")

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.version: str = raw.get("version", "unknown")
        self.levels: dict[str, float] = {k: float(v) for k, v in raw["levels"].items()}
        default = self.levels[raw.get("default_level", "poor")]
        self.aliases: dict[str, str] = raw.get("aliases", {})
        self.rooms: dict[str, RoomRule] = {}
        for key, spec in raw["room_types"].items():
            zones = {z: self.levels[spec["zones"][z]] if z in spec["zones"] else default
                     for z in self.ZONES}  # fmt: skip
            if key == "other":
                zones = dict.fromkeys(self.ZONES, 0.0)
            self.rooms[key] = RoomRule(
                key=key,
                label=spec.get("label", key),
                weight=float(spec.get("weight", 1)),
                heaviness=float(spec.get("heaviness", 0.4)),
                movable=bool(spec.get("movable", True)),
                zones=zones,
                traditional=spec.get("traditional", ""),
                physics=spec.get("physics", ""),
                remedy=spec.get("remedy", ""),
            )
        ent = raw["entrance"]
        self.entrance_weight = float(ent["weight"])
        self.entrance_secondary_weight = float(ent.get("secondary_weight", 3))
        self.entrance_sectors: dict[str, float] = {
            s: self.levels[v] for s, v in ent["sectors"].items()
        }
        self.entrance_text = {k: ent.get(k, "") for k in ("traditional", "physics", "remedy")}
        self.site: dict[str, Any] = raw["site"]

    def canonical(self, room_type: str) -> str:
        """Resolve aliases and normalise spelling; unknown types become ``other``."""
        key = room_type.strip().lower().replace(" ", "_").replace("-", "_")
        key = self.aliases.get(key, key)
        return key if key in self.rooms else "other"

    def rule(self, room_type: str) -> RoomRule:
        return self.rooms[self.canonical(room_type)]


def load_rules(path: str | Path | None = None) -> RuleBase:
    """Load the bundled rule base, or a user-supplied JSON file."""
    if path is None:
        text = resources.files("vastu_analyzer").joinpath("data/rules.json").read_text("utf-8")
    else:
        text = Path(path).read_text(encoding="utf-8")
    return RuleBase(json.loads(text))
