"""The report card: print the result step by step, in plain words."""

from __future__ import annotations

from .compass import ZONE_NAMES
from .house import House
from .scoring import Result


def report(house: House, result: Result) -> str:
    """Build the text report shown in the terminal and in the window app."""
    lines = [
        f"VASTU REPORT CARD - {result.house_name}",
        "=" * 60,
        f"House size: {house.width} m x {house.depth} m, north points {house.north} on the drawing",
        "",
        "STEP 5 - Which box is each room in?",
    ]
    for r in result.rooms:
        where = ", ".join(f"{z} {share:.0%}" for z, share in r.shares.items())
        lines.append(f"  {r.name:<16} ({r.type}) -> mostly {ZONE_NAMES[r.zone]}  [{where}]")

    lines += ["", "STEP 6a - Points for each room (out of 10)"]
    for r in result.rooms:
        if r.type == "other":
            lines.append(f"  {r.name:<16} not scored (unknown room type)")
        else:
            bar = "#" * round(r.points) + "." * (10 - round(r.points))
            lines.append(f"  {r.name:<16} {bar} {r.points:>4}/10  (counts x{r.importance})")
    if result.door_zone is not None:
        lines.append(f"  {'Main door':<16} in the {ZONE_NAMES[result.door_zone]}: "
                     f"{result.door_points:.0f}/10")  # fmt: skip
    lines.append(f"  {'Open centre':<16} {result.centre_points:.0f}/10"
                 + (f"  (blocked by {', '.join(result.centre_blocked_by)})"
                    if result.centre_blocked_by else ""))  # fmt: skip

    lines += ["", "STEP 6b - Sun check (outside walls)"]
    for r in result.rooms:
        if r.walls:
            lines.append(f"  {r.name:<16} outside walls face: {', '.join(r.walls)}")

    lines += ["", f"STEP 7 - VASTU SCORE: {result.score} / 100  ({result.grade})"]

    lines += ["", "STEP 8 - Swap game (change what a room is used for)"]
    if result.swaps:
        for a, b, new_score in result.swaps:
            lines.append(f"  Swap '{a}' <-> '{b}'  -> score becomes {new_score}")
    else:
        lines.append("  No swap makes the house better. Nice!")

    lines += ["", "STEP 9 - To-do list (most important first)"]
    if result.todo:
        lines += [f"  {i}. {t}" for i, t in enumerate(result.todo, 1)]
    else:
        lines.append("  Nothing to fix. Every room is in a good spot!")
    return "\n".join(lines)
