"""STEP 8 and STEP 9 - try swapping rooms, then write the to-do list.

STEP 8, the swap game:
    1. Try swapping the use of every pair of rooms (e.g. kitchen <-> bedroom).
       Only rooms of similar size are swapped (the bigger one is at most twice the smaller),
       and fixed things like stairs and corridors never move.
    2. Keep the single swap that raises the score the most.
    3. Repeat until no swap helps by at least 1 point (or after 5 swaps).

STEP 9, the to-do list:
    Every room scoring under 7/10, a badly placed door, a blocked centre and the
    sun tips, biggest problems first, each with a "why".
"""

from __future__ import annotations

from .compass import ZONE_NAMES
from .house import House
from .rules import DOOR_RULE, RULES, room_type
from .scoring import Result, score_house
from .sun import sun_tips

FIXED = {"staircase", "circulation", "open_space", "other"}  # things you cannot swap


def best_swaps(house: House, max_swaps: int = 5) -> list[tuple[str, str, float]]:
    """Return the swaps to make, as (room A, room B, new score)."""
    types = [r.type for r in house.rooms]
    score = score_house(house, types).score
    swaps = []

    for _ in range(max_swaps):
        best = None
        for i, a in enumerate(house.rooms):
            for j, b in enumerate(house.rooms):
                if j <= i or room_type(types[i]) == room_type(types[j]):
                    continue  # each pair once, and swapping two bedrooms changes nothing
                if room_type(types[i]) in FIXED or room_type(types[j]) in FIXED:
                    continue  # stairs, corridors, balconies stay where they are
                if max(a.area, b.area) > 2 * min(a.area, b.area):
                    continue  # a kitchen will not fit in a cupboard
                trial = list(types)
                trial[i], trial[j] = trial[j], trial[i]
                new_score = score_house(house, trial).score
                if new_score >= score + 1 and (best is None or new_score > best[2]):
                    best = (i, j, new_score)
        if best is None:
            break
        i, j, score = best
        swaps.append((house.rooms[i].name, house.rooms[j].name, score))
        types[i], types[j] = types[j], types[i]
    return swaps


def todo_list(result: Result) -> list[str]:
    """Plain-language fixes, most important first."""
    rows: list[tuple[float, str]] = []  # (how many points are lost, advice)

    for r in result.rooms:
        if r.type in FIXED or r.points >= 7:  # no "move the corridor" advice
            continue
        rule = RULES[r.type]
        best = ", ".join(ZONE_NAMES[z] for z in rule["best"])
        lost = r.importance * (10 - r.points)
        rows.append((lost, f"Move '{r.name}' ({r.points}/10, now in the {ZONE_NAMES[r.zone]}) "
                           f"towards the {best}. Why: {rule['why']} Tip: {rule['tip']}"))  # fmt: skip

    if result.door_points is not None and result.door_zone and result.door_points < 7:
        best = ", ".join(ZONE_NAMES[z] for z in DOOR_RULE["best"])
        lost = DOOR_RULE["importance"] * (10 - result.door_points)
        rows.append((lost, f"Main door is in the {ZONE_NAMES[result.door_zone]} "
                           f"({result.door_points:.0f}/10). Best is {best}. "
                           f"Why: {DOOR_RULE['why']} Tip: {DOOR_RULE['tip']}"))  # fmt: skip

    if result.centre_blocked_by:
        rows.append((20, "Keep the centre of the house open: move "
                         f"{', '.join(result.centre_blocked_by)} away from the middle. "
                         "Why: the centre (Brahmasthan) should be free; it also lets "
                         "light and air reach every room."))  # fmt: skip

    rows.sort(key=lambda row: -row[0])
    advice = [text for _, text in rows]
    for r in result.rooms:
        advice.extend(sun_tips(r.name, r.type, r.walls))
    return advice


def analyse(house: House) -> Result:
    """Run the whole process: score, swap game, to-do list."""
    result = score_house(house)
    result.swaps = best_swaps(house)
    result.todo = todo_list(result)
    return result
