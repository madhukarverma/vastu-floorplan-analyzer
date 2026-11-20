# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- The whole right-hand panel now scrolls (scrollbar plus mouse wheel anywhere over it), not
  just the report box. The wheel no longer changes drop-down lists or number boxes by accident.

## [2.2.0] - 2026-11-20

### Added

- SELECT mode (Tab switches between EDIT and SELECT): click a room to select it and drag it to
  move it. Dropping it on another room swaps the two rooms' places when both fit; otherwise it
  snaps back with an explanation.
- Keyboard shortcuts: Tab, Ctrl+Z (50-step undo), Ctrl+S, Ctrl+O, F5 / Ctrl+Enter, F11, Esc,
  and Delete, R (rotate) and arrow keys (nudge) for the selected room.
- "Add a room by size": type width and depth (optionally X and Y). The app finds a free spot
  automatically, and a persistent red message explains when there is no space or a collision.
- Collision detection on every draw, move, nudge, rotate and add (`collision`,
  `find_free_spot` and `move_room` in `house.py`, with tests).
- Coloured mode bar, status messages, "Update selected", "Delete selected" and "Shortcuts" buttons.

## [2.1.0] - 2026-11-18

### Added

- Full-screen mode (F11 or the *Full screen* button, Esc to leave). The drawing and its labels
  now grow with the window.
- Big score banner coloured by grade, a colour legend, and a colour-coded report card
  (steps, good / okay / bad points, swaps, sun tips).
- 7 sample houses from worst to best (Poor to Excellent; different sizes and north
  directions), selectable from a *Sample houses* list in the app.

### Changed

- Room swaps now need similar sizes (at most 1.5× instead of 2×), which avoids odd
  suggestions like turning a small toilet into a large living room.

## [2.0.0] - 2026-11-18

Simplified classroom version. The detailed research engine stays available at tag `v1.0.0`.

### Added

- Tkinter window app (`vastu app`): draw rooms with the mouse, place the door, set north,
  click Analyse to get coloured rooms and a report card.
- Plain-language flowchart (`docs/figures/simple_flowchart.svg`) and walkthrough.
- Presentation guide with slide plan, live demo script and likely questions.
- Step-by-step terminal report (`vastu analyze house.json`).

### Changed

- Rewritten as 9 short, commented modules that follow the flowchart steps one by one.
- Rooms are rectangles; north is up / right / down / left; points are 0-10 per room and
  the score is out of 100.
- Rule book is a plain Python dictionary in `rules.py`.
- 12 small tests, one per step.

### Removed

- Polygon geometry, solar-position physics, mass dipole, magnetic declination, the click
  digitiser and the paper build scripts (all still in `v1.0.0`; the paper PDF is kept in `docs/paper`).

## [1.0.0] - 2026-11-12

### Added

- Ranked evaluation of eight non-ML solution approaches (`docs/approaches.md`).
- Plan JSON schema v1, a loader that collects every validation error, unit conversion and
  type aliases.
- Exact computational geometry: shoelace area and centroid, Sutherland–Hodgman clipping and
  ray casting.
- 3 × 3 Vastu-Purusha mandala zoning and a 16-sector compass.
- Vastu rule base as editable JSON (16 room types, entrance sectors, site rules).
- Vastu Compliance Index with Brahmasthana, corner-cut, shape and mass-dipole terms.
- Solar physics: NOAA sun position, Kasten–Young air mass, Meinel DNI, wall irradiation,
  sol-air temperature and overhang sizing.
- Steepest-ascent optimiser over exchanges of room functions.
- Text, Markdown and JSON reports; annotated zone map; click-based digitiser.
- `vastu` CLI with `analyze`, `solar`, `rules` and `digitize` commands.
- 72 unit tests (97 % coverage), strict mypy, ruff, pre-commit and GitHub Actions CI.
- Physics-journal-style research paper with reproducible figure and PDF builds.
