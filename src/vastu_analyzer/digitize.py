"""Interactive, human-in-the-loop digitiser for raster floor plans (no AI/ML).

The user clicks points on the scanned plan; the program only records coordinates.
Steps: (1) scale bar, (2) north arrow, (3) outer footprint, (4) each room,
(5) the main entrance. Requires matplotlib with an interactive backend.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .geometry import compass_bearing


def _clicks(plt: Any, prompt: str, n: int = -1) -> list[tuple[float, float]]:
    plt.title(prompt, fontsize=9)
    plt.draw()
    pts = plt.ginput(n=n, timeout=0, show_clicks=True)
    return [(float(x), float(-y)) for x, y in pts]  # image rows grow downwards


def digitize(image_path: str | Path, out_path: str | Path) -> dict[str, Any]:  # pragma: no cover
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt

    img = mpimg.imread(str(image_path))
    plt.figure(figsize=(10, 8))
    plt.imshow(img)
    plt.axis("off")

    (a, b) = _clicks(plt, "Click both ends of a known dimension (scale bar)", 2)
    known = float(input("Real length of that dimension in metres: "))
    k = known / math.dist(a, b)

    (t, h) = _clicks(plt, "Click the tail, then the head, of the north arrow", 2)
    north = compass_bearing(h[0] - t[0], h[1] - t[1])
    ref = input("Is the arrow true or magnetic north? [true/magnetic]: ").strip() or "true"
    decl = float(input("Magnetic declination in degrees (east +, 0 if unknown): ") or 0)

    fp = _clicks(plt, "Click the outer wall corners; press Enter when done")
    rooms = []
    while True:
        name = input("Room name (blank to finish): ").strip()
        if not name:
            break
        rtype = input(f"Type of '{name}' (kitchen, toilet, master_bedroom, ...): ").strip()
        poly = _clicks(plt, f"Click the corners of '{name}'; press Enter when done")
        rooms.append({"name": name, "type": rtype, "polygon": [[x * k, y * k] for x, y in poly]})
    (door,) = _clicks(plt, "Click the main entrance door", 1)
    plt.close()

    plan = {
        "schema_version": "1.0",
        "name": Path(image_path).stem,
        "units": "m",
        "north": {"angle_deg": north, "reference": ref, "declination_deg": decl},
        "footprint": [[x * k, y * k] for x, y in fp],
        "rooms": rooms,
        "entrances": [{"name": "Main door", "position": [door[0] * k, door[1] * k], "main": True}],
    }
    Path(out_path).write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return plan
