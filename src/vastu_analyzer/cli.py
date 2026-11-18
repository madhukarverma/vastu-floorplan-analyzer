"""Command line:

vastu app                 open the window app (draw your house, click Analyse)
vastu analyze house.json  print the report card for a house file
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .house import check_house, load_house
from .report import report
from .suggestions import analyse


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vastu", description="Simple Vastu checker for a house map.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("app", help="open the window app")
    run = commands.add_parser("analyze", help="print the report card for a house JSON file")
    run.add_argument("file")
    args = parser.parse_args(argv)

    if args.command == "app":
        from .app import run_app  # imported here so the terminal mode never needs a screen

        run_app()
        return 0

    house = load_house(args.file)
    problems = check_house(house)  # STEP 2
    if problems:
        print("Please fix the drawing first:")
        for p in problems:
            print("  -", p)
        return 1
    print(report(house, analyse(house)))
    return 0
