# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
