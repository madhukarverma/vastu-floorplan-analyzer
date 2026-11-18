"""STEP 6b - the sun checker: which outside walls get too hot?

The numbers come from our physics model (see the paper in docs/paper): the hottest
temperature an outside wall's surface reaches on a summer day (21 June) in New Delhi.

Key idea for the class:
    East and west walls get the SAME amount of sunshine in a day,
    but the west wall gets it in the afternoon, when the air is already hot.
    So the west wall gets about 6.5 degrees C hotter. That is a science reason
    behind the Vastu idea "keep the west / south-west heavy and closed".
"""

from __future__ import annotations

# Peak summer wall temperature (degrees C) and what it means.
WALL_HEAT = {
    "N": (46.5, "cool, soft daylight all day"),
    "E": (58.6, "warm morning sun, cool afternoon"),
    "S": (46.1, "mild in summer, sunny in winter"),
    "W": (65.1, "hottest wall: strong afternoon sun"),
}

# Rooms where people spend a lot of time.
LIVING_ROOMS = {"master_bedroom", "bedroom", "living", "study", "pooja", "dining"}


def sun_tips(room_name: str, room_type: str, walls: list[str]) -> list[str]:
    """Simple sun-and-air advice for one room, from its outside walls."""
    tips = []
    if room_type in LIVING_ROOMS and "W" in walls:
        tips.append(
            f"'{room_name}' has a west wall that reaches about {WALL_HEAT['W'][0]} C "
            "in summer. Add shade outside (sunshade, plants) and use light paint."
        )
    if room_type == "kitchen" and "E" not in walls:
        tips.append(f"'{room_name}' gets no morning sun. An east window would help.")
    if room_type == "toilet" and not walls:
        tips.append(f"'{room_name}' has no outside wall. Fit an exhaust fan or air duct.")
    return tips
