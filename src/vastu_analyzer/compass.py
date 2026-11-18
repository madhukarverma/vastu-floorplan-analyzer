"""STEPS 3, 4 and 5 - find north, lay a 3 x 3 grid, see which box each room is in.

The 3 x 3 grid is the simplest form of the Vastu-Purusha mandala. When north
points UP on the drawing the nine boxes are:

        +------+------+------+
        |  NW  |  N   |  NE  |
        +------+------+------+
        |  W   |  C   |  E   |      C = centre (Brahmasthan)
        +------+------+------+
        |  SW  |  S   |  SE  |
        +------+------+------+

If north points another way we simply turn the compass labels round.
"""

from __future__ import annotations

from .house import House, Room, overlap_area

# The four sides of the drawing, going clockwise, and the four compass points.
SIDES = ["up", "right", "down", "left"]
COMPASS = ["N", "E", "S", "W"]

ZONES = ["NW", "N", "NE", "W", "C", "E", "SW", "S", "SE"]

ZONE_NAMES = {
    "N": "North",
    "NE": "North-east",
    "E": "East",
    "SE": "South-east",
    "S": "South",
    "SW": "South-west",
    "W": "West",
    "NW": "North-west",
    "C": "Centre",
}


# ----------------------------------------------------------------------------
# STEP 3 - find north
# ----------------------------------------------------------------------------


def side_to_compass(side: str, north: str) -> str:
    """Which compass direction a side of the drawing faces.

    Example: if north points "right", then the "up" side of the drawing faces West.
    We count how many quarter-turns north is away from "up" and turn back by that much.
    """
    turns = SIDES.index(north)
    return COMPASS[(SIDES.index(side) - turns) % 4]


# ----------------------------------------------------------------------------
# STEP 4 - the 3 x 3 grid
# ----------------------------------------------------------------------------


def zone_of_box(row: int, col: int, north: str) -> str:
    """Compass name of grid box (row, col); row 0 is the top, col 0 is the left."""
    parts = []
    if row == 0:
        parts.append(side_to_compass("up", north))
    if row == 2:
        parts.append(side_to_compass("down", north))
    if col == 0:
        parts.append(side_to_compass("left", north))
    if col == 2:
        parts.append(side_to_compass("right", north))
    if not parts:
        return "C"
    # Write north/south before east/west, so we get "NE" and not "EN".
    parts.sort(key=lambda p: 0 if p in ("N", "S") else 1)
    return "".join(parts)


def grid_boxes(house: House) -> dict[str, tuple[float, float, float, float]]:
    """The nine boxes as rectangles (x, y, w, h), keyed by compass name."""
    bw, bh = house.width / 3, house.depth / 3
    boxes = {}
    for row in range(3):
        for col in range(3):
            boxes[zone_of_box(row, col, house.north)] = (col * bw, row * bh, bw, bh)
    return boxes


# ----------------------------------------------------------------------------
# STEP 5 - which box is each room in?
# ----------------------------------------------------------------------------


def room_shares(room: Room, house: House) -> dict[str, float]:
    """How much of the room lies in each box, as fractions that add up to 1.

    Example: {"N": 0.5, "NE": 0.5} means half the room is in the north box
    and half in the north-east box.
    """
    shares = {}
    for zone, (x, y, w, h) in grid_boxes(house).items():
        part = overlap_area(room.x, room.y, room.w, room.h, x, y, w, h) / room.area
        if part > 0.001:
            shares[zone] = round(part, 3)
    return shares


def main_zone(shares: dict[str, float]) -> str:
    """The box that holds the biggest part of the room."""
    return max(shares, key=lambda z: shares[z])


def point_zone(x: float, y: float, house: House) -> str:
    """Which box a single point (like the door) is in."""
    col = min(2, int(x / (house.width / 3)))
    row = min(2, int(y / (house.depth / 3)))
    return zone_of_box(row, col, house.north)


def outside_walls(room: Room, house: House) -> list[str]:
    """Compass directions of the room's walls that touch the outside of the house."""
    walls = []
    if room.y == 0:
        walls.append(side_to_compass("up", house.north))
    if room.x + room.w == house.width:
        walls.append(side_to_compass("right", house.north))
    if room.y + room.h == house.depth:
        walls.append(side_to_compass("down", house.north))
    if room.x == 0:
        walls.append(side_to_compass("left", house.north))
    return walls
