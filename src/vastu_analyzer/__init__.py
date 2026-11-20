"""A simple Vastu checker for a house map.

The code follows the 9 steps of the flowchart (docs/figures/simple_flowchart.svg):

    house.py        STEP 1-2  describe the house, check the drawing
    compass.py      STEP 3-5  find north, 3 x 3 grid, which box each room is in
    rules.py        STEP 6a   every room's favourite spots
    sun.py          STEP 6b   which outside walls get too hot
    scoring.py      STEP 7    points per room and a score out of 100
    suggestions.py  STEP 8-9  swap game and to-do list
    report.py                 the printed report card
    app.py                    the window app
"""

from __future__ import annotations

__version__ = "2.2.0"

from .house import Door, House, Room, check_house, load_house, save_house
from .report import report
from .scoring import score_house
from .suggestions import analyse

__all__ = [
    "Door",
    "House",
    "Room",
    "__version__",
    "analyse",
    "check_house",
    "load_house",
    "report",
    "save_house",
    "score_house",
]
