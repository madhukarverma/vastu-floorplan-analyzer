# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
