"""STEP 6a (part 2) and STEP 7 - give every room points, then score the house out of 100.

Room points (0 to 10):
    A room can sit across several boxes, so we use a weighted average:
        points = sum over boxes of (share of the room in that box) x (points for that box)
    Example: a kitchen that is half in SE (10 points) and half in S (5 points)
    gets 0.5 x 10 + 0.5 x 5 = 7.5 points.

House score (0 to 100):
    Every item (each room, the door, the open centre) has an importance of 1 to 3.
        score = 100 x sum(importance x points) / sum(importance x 10)
    Important rooms (kitchen, master bedroom, pooja, toilet, door) count three times
    as much as a store room.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .compass import main_zone, outside_walls, point_zone, room_shares
from .house import House, Room
from .rules import CENTRE_IMPORTANCE, DOOR_RULE, NOT_IN_CENTRE, RULES, points_for, room_type


@dataclass
class RoomScore:
    name: str
    type: str  # rule-book type, e.g. "kitchen" ("other" if unknown)
    zone: str  # the box that holds most of the room
    shares: dict[str, float]  # e.g. {"N": 0.5, "NE": 0.5}
    walls: list[str]  # outside walls, e.g. ["N", "E"]
    points: float  # 0 to 10
    importance: int  # 0 to 3 (0 = not scored)


@dataclass
class Result:
    house_name: str
    score: float  # 0 to 100
    grade: str
    rooms: list[RoomScore]
    door_zone: str | None
    door_points: float | None
    centre_blocked_by: list[str]
    centre_points: float
    swaps: list[tuple[str, str, float]] = field(default_factory=list)  # filled in step 8
    todo: list[str] = field(default_factory=list)  # filled in step 9


def score_room(name: str, kind: str, house: House, x: float, y: float, w: float, h: float) -> RoomScore:
    """Points for one room of type ``kind`` placed at (x, y, w, h)."""
    room = Room(name, kind, x, y, w, h)
    shares = room_shares(room, house)
    rtype = room_type(kind)
    if rtype == "other":
        points, importance = 0.0, 0  # unknown rooms are shown but not scored
    else:
        rule = RULES[rtype]
        points = sum(share * points_for(rule, zone) for zone, share in shares.items())
        importance = rule["importance"]
    return RoomScore(name, rtype, main_zone(shares), shares, outside_walls(room, house),
                     round(points, 1), importance)  # fmt: skip


def grade(score: float) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Needs work"
    return "Poor"


def score_house(house: House, types: list[str] | None = None) -> Result:
    """Score the whole house. ``types`` lets step 8 try the house with rooms swapped."""
    types = types or [r.type for r in house.rooms]
    rooms = [
        score_room(r.name, t, house, r.x, r.y, r.w, r.h) for r, t in zip(house.rooms, types, strict=True)
    ]

    # Each item is (importance, points out of 10).
    items = [(r.importance, r.points) for r in rooms]

    # The main door.
    door_zone = door_points = None
    if house.door:
        door_zone = point_zone(house.door.x, house.door.y, house)
        door_points = float(points_for(DOOR_RULE, door_zone))
        items.append((DOOR_RULE["importance"], door_points))

    # The centre (Brahmasthan) should be open: lose points for heavy or wet rooms there.
    blocked = [r.name for r in rooms if r.type in NOT_IN_CENTRE and r.shares.get("C", 0) > 0.2]
    centre_points = 10.0 if not blocked else 0.0
    items.append((CENTRE_IMPORTANCE, centre_points))

    total_weight = sum(imp for imp, _ in items)
    score = 100 * sum(imp * pts for imp, pts in items) / (total_weight * 10)
    return Result(house.name, round(score, 1), grade(score), rooms, door_zone, door_points,
                  blocked, centre_points)  # fmt: skip
