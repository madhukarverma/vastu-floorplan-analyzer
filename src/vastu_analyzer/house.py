"""STEP 1 and STEP 2 - describe the house, then check the drawing.

We keep the house simple on purpose:

* The house is a rectangle, ``width`` metres wide and ``depth`` metres deep.
* Every room is a rectangle inside it.
* Positions are measured like on a screen: ``x`` from the LEFT edge,
  ``y`` from the TOP edge, both in metres.

            x ->
        +-----------------------+   y = 0 (top edge)
     y  |  Living   | Kitchen   |
     |  |-----------+-----------|
     v  |  Bedroom  |  Toilet   |
        +-----------------------+   y = depth (bottom edge)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Room:
    """One rectangular room."""

    name: str  # what the owner calls it, e.g. "Kitchen"
    type: str  # what it is used for, e.g. "kitchen" (see rules.py)
    x: float  # left edge, metres from the left of the house
    y: float  # top edge, metres from the top of the house
    w: float  # width in metres
    h: float  # height (depth) in metres

    @property
    def area(self) -> float:
        return self.w * self.h


@dataclass
class Door:
    """The main entrance, a point on the outer wall."""

    x: float
    y: float


@dataclass
class House:
    """The whole house: its size, which way north is, the rooms and the door."""

    name: str
    width: float
    depth: float
    north: str = "up"  # where north points on the drawing: up / right / down / left
    rooms: list[Room] = field(default_factory=list)
    door: Door | None = None


# ----------------------------------------------------------------------------
# STEP 1 - read / write the house as a JSON file
# ----------------------------------------------------------------------------


def load_house(path: str | Path) -> House:
    """Read a house from a JSON file (format: docs/input-format.md)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rooms = [Room(**r) for r in data["rooms"]]
    door = Door(**data["door"]) if data.get("door") else None
    return House(
        name=data.get("name", "My house"),
        width=data["width"],
        depth=data["depth"],
        north=data.get("north", "up"),
        rooms=rooms,
        door=door,
    )


def save_house(house: House, path: str | Path) -> None:
    """Write a house to a JSON file."""
    Path(path).write_text(json.dumps(asdict(house), indent=2), encoding="utf-8")


# ----------------------------------------------------------------------------
# STEP 2 - check the drawing for obvious mistakes
# ----------------------------------------------------------------------------


def check_house(house: House) -> list[str]:
    """Return a list of problems. An empty list means the drawing is fine."""
    problems: list[str] = []

    if house.north not in ("up", "right", "down", "left"):
        problems.append("North must be 'up', 'right', 'down' or 'left'.")
    if not house.rooms:
        problems.append("Draw at least one room.")

    for room in house.rooms:
        inside = (
            room.x >= 0 and room.y >= 0 and room.x + room.w <= house.width and room.y + room.h <= house.depth
        )
        if room.w <= 0 or room.h <= 0:
            problems.append(f"'{room.name}' has no size.")
        elif not inside:
            problems.append(f"'{room.name}' sticks out of the house.")

    # Two rooms must not sit on top of each other.
    for i, a in enumerate(house.rooms):
        for b in house.rooms[i + 1 :]:
            if overlap_area(a.x, a.y, a.w, a.h, b.x, b.y, b.w, b.h) > 0.01:
                problems.append(f"'{a.name}' and '{b.name}' overlap.")

    return problems


def overlap_area(
    ax: float, ay: float, aw: float, ah: float, bx: float, by: float, bw: float, bh: float
) -> float:
    """Area shared by two rectangles (0 if they do not touch).

    Overlap width  = (smaller right edge) - (bigger left edge)
    Overlap height = (smaller bottom edge) - (bigger top edge)
    """
    overlap_w = min(ax + aw, bx + bw) - max(ax, bx)
    overlap_h = min(ay + ah, by + bh) - max(ay, by)
    if overlap_w <= 0 or overlap_h <= 0:
        return 0.0
    return overlap_w * overlap_h


# ----------------------------------------------------------------------------
# Editing helpers used by the window app: collisions, free space, moving rooms
# ----------------------------------------------------------------------------


def collision(house: House, room: Room) -> str | None:
    """Why ``room`` cannot stay where it is, or ``None`` if it fits.

    A room fits when it is inside the house and does not overlap any OTHER room.
    """
    inside = room.x >= 0 and room.y >= 0 and room.x + room.w <= house.width and room.y + room.h <= house.depth
    if not inside:
        return f"'{room.name}' would stick out of the house."
    for other in house.rooms:
        if other is room:
            continue
        if overlap_area(room.x, room.y, room.w, room.h, other.x, other.y, other.w, other.h) > 0.01:
            return f"'{room.name}' would overlap '{other.name}'."
    return None


def find_free_spot(house: House, w: float, h: float, step: float = 0.5) -> tuple[float, float] | None:
    """Top-left corner of the first empty space big enough for a w x h room.

    We simply try every position, row by row from the top-left, in half-metre steps.
    Returns ``None`` when there is no space anywhere.
    """
    test = Room("new room", "other", 0, 0, w, h)
    y = 0.0
    while y + h <= house.depth:
        x = 0.0
        while x + w <= house.width:
            test.x, test.y = x, y
            if collision(house, test) is None:
                return x, y
            x += step
        y += step
    return None


def move_room(house: House, room: Room, x: float, y: float) -> tuple[bool, str]:
    """Move ``room`` so its top-left corner is at (x, y).

    * Dropped on empty space          -> the room just moves.
    * Dropped on top of ONE other room -> the two rooms swap places
                                          (if both still fit after swapping).
    * Anything else                   -> nothing changes and we explain why.

    Returns (it worked?, a message for the user).
    """
    old_x, old_y = room.x, room.y
    room.x, room.y = x, y
    if collision(house, room) is None:
        return True, f"Moved '{room.name}'."

    hits = [o for o in house.rooms if o is not room
            and overlap_area(room.x, room.y, room.w, room.h, o.x, o.y, o.w, o.h) > 0.01]  # fmt: skip
    if len(hits) == 1:
        other = hits[0]
        other_x, other_y = other.x, other.y
        room.x, room.y = other_x, other_y  # room takes the other room's place ...
        other.x, other.y = old_x, old_y  # ... and the other room takes the old place
        if collision(house, room) is None and collision(house, other) is None:
            return True, f"Swapped '{room.name}' and '{other.name}'."
        other.x, other.y = other_x, other_y  # did not fit: undo the swap

    room.x, room.y = old_x, old_y  # put it back where it was
    if not hits:
        reason = "it would stick out of the house."
    elif len(hits) == 1:
        reason = f"'{room.name}' and '{hits[0].name}' do not fit in each other's place."
    else:
        reason = f"it would overlap {len(hits)} rooms."
    return False, f"Cannot move '{room.name}' there: {reason}"
