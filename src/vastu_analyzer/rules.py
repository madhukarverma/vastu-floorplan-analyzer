"""STEP 6a (part 1) - the Vastu rule book: every room's favourite spots.

Each room type lists the boxes it likes, from best to worst. Points per box:

    best  = 10 points
    good  =  7 points
    okay  =  5 points
    bad   =  0 points
    (any box not listed) = 3 points

"importance" says how much the room counts in the final score (1 to 3).
"why" is the reason from Vastu Shastra plus the common-sense / science reason.
"""

from __future__ import annotations

from typing import Any

POINTS = {"best": 10, "good": 7, "okay": 5, "bad": 0}
NOT_LISTED = 3

RULES: dict[str, dict[str, Any]] = {
    "kitchen": {
        "best": ["SE"],
        "good": ["NW"],
        "okay": ["E", "S"],
        "bad": ["NE", "N", "SW", "C"],
        "importance": 3,
        "why": "South-east belongs to Agni (fire). Science: an east-side kitchen gets morning light.",
        "tip": "Put the stove in the south-east corner so the cook faces east.",
    },
    "master_bedroom": {
        "best": ["SW"],
        "good": ["S", "W"],
        "okay": [],
        "bad": ["NE", "SE", "C"],
        "importance": 3,
        "why": "South-west is the most stable corner, for the head of the family. "
        "Science: thick walls here block the hot afternoon sun.",
        "tip": "Sleep with your head towards the south or west.",
    },
    "pooja": {
        "best": ["NE"],
        "good": ["E", "N"],
        "okay": ["W"],
        "bad": ["S", "SW", "SE"],
        "importance": 3,
        "why": "North-east (Ishanya) is the holiest corner. Science: it gets soft morning sun.",
        "tip": "Face east or north while praying.",
    },
    "toilet": {
        "best": ["NW"],
        "good": ["W"],
        "okay": ["S"],
        "bad": ["NE", "SW", "C"],
        "importance": 3,
        "why": "Waste goes to the north-west (Vayu, air). Never in the holy north-east or centre.",
        "tip": "Keep it dry, closed and fitted with an exhaust fan.",
    },
    "bedroom": {
        "best": ["W", "NW"],
        "good": ["S", "SW"],
        "okay": ["N", "E"],
        "bad": ["C"],
        "importance": 2,
        "why": "Children's and guest rooms belong to the west and north-west.",
        "tip": "Place the bed with the head towards the south or east.",
    },
    "living": {
        "best": ["N", "E", "NE"],
        "good": ["NW"],
        "okay": ["W", "C"],
        "bad": [],
        "importance": 2,
        "why": "Guests are welcomed in the bright, open north and east.",
        "tip": "Keep heavy furniture on the south and west walls.",
    },
    "dining": {
        "best": ["W"],
        "good": ["E"],
        "okay": ["N", "S", "C", "NW", "SE"],
        "bad": [],
        "importance": 1,
        "why": "Dining sits in the west, next to the kitchen.",
        "tip": "Keep the dining table close to the kitchen.",
    },
    "staircase": {
        "best": ["S", "W", "SW"],
        "good": [],
        "okay": ["SE", "NW"],
        "bad": ["NE", "C"],
        "importance": 2,
        "why": "Stairs are heavy, and heavy things belong in the south and west.",
        "tip": "Stairs should go up clockwise; never put a toilet under them.",
    },
    "study": {
        "best": ["NE", "E", "N"],
        "good": ["W"],
        "okay": ["NW"],
        "bad": [],
        "importance": 1,
        "why": "Study faces east or north. Science: soft north light causes no glare.",
        "tip": "Sit facing east or north.",
    },
    "store": {
        "best": ["SW"],
        "good": ["W", "S", "NW"],
        "okay": ["SE"],
        "bad": ["NE"],
        "importance": 1,
        "why": "Heavy storage makes the south-west strong.",
        "tip": "Keep the heaviest things on the south-west side.",
    },
    "open_space": {
        "best": ["NE", "N", "E"],
        "good": ["C"],
        "okay": ["NW", "SE"],
        "bad": ["SW"],
        "importance": 1,
        "why": "Open, light spaces belong in the north-east.",
        "tip": "Keep the north-east open and clean.",
    },
    "utility": {
        "best": ["NW"],
        "good": ["SE", "W"],
        "okay": ["S"],
        "bad": ["NE", "C"],
        "importance": 1,
        "why": "Washing (air and movement) belongs to the north-west.",
        "tip": "Drain water towards the north or east.",
    },
    "circulation": {
        "best": ["C"],
        "good": ["N", "E", "NE"],
        "okay": ["S", "W", "NW", "SE", "SW"],
        "bad": [],
        "importance": 1,
        "why": "Halls and passages keep the centre of the house open.",
        "tip": "Keep passages clear.",
    },
}

# Other names people use for the same room type.
ALIASES = {
    "bathroom": "toilet", "wc": "toilet", "washroom": "toilet",
    "puja": "pooja", "prayer": "pooja", "mandir": "pooja",
    "master": "master_bedroom", "master bedroom": "master_bedroom",
    "guest room": "bedroom", "kids room": "bedroom",
    "hall": "living", "drawing room": "living", "living room": "living",
    "stairs": "staircase", "storage": "store",
    "balcony": "open_space", "verandah": "open_space", "garden": "open_space",
    "courtyard": "open_space",
    "corridor": "circulation", "passage": "circulation", "foyer": "circulation",
    "lobby": "circulation", "laundry": "utility",
}  # fmt: skip

# The door (main entrance).
DOOR_RULE: dict[str, Any] = {
    "best": ["N", "NE", "E"], "good": [], "okay": ["NW", "W", "SE"], "bad": ["SW"],
    "importance": 3,
    "why": "North, north-east and east doors let in the morning energy. "
           "Science: they open to the cooler, shaded side in the afternoon.",
    "tip": "If you cannot move the door, keep it bright and clean.",
}  # fmt: skip

# Rooms that must NOT be in the centre (the Brahmasthan should stay open).
NOT_IN_CENTRE = {"toilet", "kitchen", "staircase", "store"}
CENTRE_IMPORTANCE = 2


def room_type(name: str) -> str:
    """Turn what the user typed ("Bathroom", "puja") into a rule-book type."""
    key = name.strip().lower().replace("-", " ")
    key = ALIASES.get(key, key).replace(" ", "_")
    return key if key in RULES else "other"


def points_for(rule: dict[str, Any], zone: str) -> int:
    """Points a room (or the door) earns for sitting in one zone."""
    for level in ("best", "good", "okay", "bad"):
        if zone in rule[level]:
            return POINTS[level]
    return NOT_LISTED
